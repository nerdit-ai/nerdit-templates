"""Nerdit template: a scheduled AI job.

Every day Nerdit calls ``POST /_agent/run/daily``. The app fetches a public
feed, asks the bound model for a category and a one-line summary of each new
item, and stores the result. One model call per item, no agent loop: the code
decides what happens, the model only fills two fields.

The three bricks, all declared in ``nerdit.toml``:

    [schedules.daily]   the timer (Nerdit calls the route)
    [ai.default]        the model, through the machine's AI gateway
    [limits]            an optional monthly token ceiling for this app
"""

from __future__ import annotations

import hmac
import html
import json
import logging
import os
import sqlite3
import threading
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import openai
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger("uvicorn.error")
app = FastAPI(title="Nerdit Scheduled AI Job")

# Nerdit mounts a persistent volume and names it in NERDIT_DATA_DIR.
# ponytail: SQLite, one process; a managed Postgres ([db.default]) once a
# second process writes.
DB_PATH = Path(os.environ.get("NERDIT_DATA_DIR", ".")) / "app.db"
# A feed its publisher offers for automated reading. Point FEED_URL at your
# own source, and only at one whose terms allow fetching it.
FEED_URL = os.environ.get("FEED_URL", "https://pypi.org/rss/packages.xml")
MODEL = os.environ.get("OPENAI_MODEL", "fast")
MAX_ITEMS = 10  # per run: bounds the tokens one run can spend
_FEED_MAX_BYTES = 1_000_000
_busy = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    guid TEXT PRIMARY KEY, title TEXT, link TEXT,
    category TEXT, summary TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY, started_at TEXT, finished_at TEXT,
    items INTEGER DEFAULT 0, tokens INTEGER DEFAULT 0, outcome TEXT);
"""


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def fetch_feed() -> list[dict[str, str]]:
    """Return the feed's items as ``{guid, title, link}``, newest first."""
    with urllib.request.urlopen(FEED_URL, timeout=20) as response:  # noqa: S310 - owner-set URL
        body = response.read(_FEED_MAX_BYTES)
    items = []
    for node in ET.fromstring(body).iter("item"):  # noqa: S314 - size-capped, owner-set source
        link = node.findtext("link") or ""
        items.append(
            {
                "guid": node.findtext("guid") or link,
                "title": (node.findtext("title") or "")[:300],
                "link": link,
            }
        )
    return [item for item in items if item["guid"]]


def enrich(title: str) -> tuple[str, str, int]:
    """Ask the model for ``(category, summary, tokens used)`` of one title.

    The title is untrusted text. That is safe here because the answer is only
    stored and shown escaped: the model holds no tool and takes no action.
    """
    client = openai.OpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", "nerdit-local"),
    )
    completion = client.chat.completions.create(
        model=MODEL,
        max_tokens=120,
        messages=[
            {
                "role": "system",
                "content": 'Answer with JSON only: {"category": "<one word>", '
                '"summary": "<one short sentence>"}.',
            },
            {"role": "user", "content": title},
        ],
    )
    text = completion.choices[0].message.content or ""
    tokens = completion.usage.total_tokens if completion.usage else 0
    try:
        data = json.loads(text[text.index("{") : text.rindex("}") + 1])
        return str(data["category"])[:40], str(data["summary"])[:300], tokens
    except (ValueError, KeyError, TypeError):
        return "unknown", text.strip()[:300], tokens


def work(run_id: str) -> None:
    """Enrich up to ``MAX_ITEMS`` new feed items and close the run row."""
    try:
        with sqlite3.connect(DB_PATH) as conn:  # the route created the schema
            done, tokens, outcome = _enrich_new(conn)
            conn.execute(
                "UPDATE runs SET finished_at = ?, items = ?, tokens = ?, outcome = ? "
                "WHERE run_id = ?",
                (_now(), done, tokens, outcome, run_id),
            )
    finally:
        _busy.release()


def _enrich_new(conn: sqlite3.Connection) -> tuple[int, int, str]:
    """Return ``(items stored, tokens used, outcome)``; never raises."""
    done = tokens = 0
    try:
        for item in fetch_feed():
            if done >= MAX_ITEMS:
                break
            if conn.execute("SELECT 1 FROM items WHERE guid = ?", (item["guid"],)).fetchone():
                continue
            category, summary, used = enrich(item["title"])
            tokens += used
            conn.execute(
                "INSERT INTO items VALUES (?, ?, ?, ?, ?, ?)",
                (item["guid"], item["title"], item["link"], category, summary, _now()),
            )
            conn.commit()  # keep what is paid for if a later item fails
            done += 1
    except openai.RateLimitError as exc:
        # The gateway's monthly limit for this app. Stop; the next run after
        # the limit is raised or the month turns picks up where this one ended.
        return done, tokens, "budget_exceeded" if exc.code == "budget_exceeded" else "rate_limited"
    except Exception as exc:  # noqa: BLE001 - one row must record any failure
        logger.exception("run failed")
        return done, tokens, f"failed: {type(exc).__name__}"
    return done, tokens, "ok"


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: never calls the model (Nerdit health-checks this path)."""
    return {"status": "ok"}


@app.post("/_agent/run/daily", status_code=202)
def run_daily(request: Request, background: BackgroundTasks) -> dict[str, str]:
    """Start one run. Only Nerdit's scheduler may call this."""
    # Nerdit injects NERDIT_SCHEDULE_TOKEN and sends it with every scheduled
    # call. Another container on the machine can reach this port, so the token,
    # not the caller's address, is the proof. An unset token refuses everyone.
    expected = os.environ.get("NERDIT_SCHEDULE_TOKEN", "")
    given = request.headers.get("x-nerdit-schedule-token", "")
    if not expected or not hmac.compare_digest(expected.encode(), given.encode()):
        raise HTTPException(status_code=403, detail="not a scheduled call")
    run_id = request.headers.get("x-nerdit-schedule-run") or uuid.uuid4().hex
    if not _busy.acquire(blocking=False):
        return {"skipped": "a run is already in progress"}
    conn = _db()
    try:
        conn.execute(
            "INSERT INTO runs (run_id, started_at, outcome) VALUES (?, ?, 'running')",
            (run_id, _now()),
        )
        conn.commit()
    except sqlite3.IntegrityError:  # the same run delivered twice
        _busy.release()
        return {"duplicate": run_id}
    finally:
        conn.close()
    # Answer now, work after: Nerdit records 202 as "accepted" and does not
    # wait. The run's real outcome is in the runs table (and on the page).
    background.add_task(work, run_id)
    return {"accepted": run_id}


def _href(link: str) -> str:
    """Escape a feed link for an href; a feed is untrusted, so only http(s) is clickable."""
    return html.escape(link, quote=True) if link.startswith(("https://", "http://")) else "#"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    conn = _db()
    items = conn.execute("SELECT * FROM items ORDER BY created_at DESC LIMIT 50").fetchall()
    runs = conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 10").fetchall()
    conn.close()
    esc = html.escape
    item_rows = "".join(
        f"<tr><td>{esc(r['category'] or '')}</td>"
        f"<td><a href='{_href(r['link'] or '')}' rel='noreferrer'>"
        f"{esc(r['title'] or '')}</a><br><small>{esc(r['summary'] or '')}</small></td></tr>"
        for r in items
    )
    run_rows = "".join(
        f"<tr><td>{esc(r['started_at'] or '')}</td><td>{esc(r['outcome'] or '')}</td>"
        f"<td>{r['items']}</td><td>{r['tokens']}</td></tr>"
        for r in runs
    )
    return (
        "<!doctype html><meta charset='utf-8'><title>Scheduled AI job</title>"
        "<style>body{font-family:system-ui;max-width:860px;margin:2rem auto;padding:0 1rem;"
        "color-scheme:light dark}table{border-collapse:collapse;width:100%}"
        "td,th{padding:.4rem;border-bottom:1px solid #8884;text-align:left;"
        "vertical-align:top}</style>"
        "<h1>Scheduled AI job</h1><h2>Runs</h2><table><tr><th>Started</th><th>Outcome</th>"
        f"<th>Items</th><th>Tokens</th></tr>{run_rows}</table>"
        f"<h2>Items</h2><table><tr><th>Category</th><th>Item</th></tr>{item_rows}</table>"
    )
