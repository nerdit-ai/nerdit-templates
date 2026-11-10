"""One check for the template: token gate, dedupe, the happy run, the budget stop.

Run: pip install -r requirements.txt pytest httpx && pytest -q
"""

from __future__ import annotations

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

import main

FEED = [{"guid": f"g{i}", "title": f"t{i}", "link": f"https://example.org/{i}"} for i in range(3)]
AUTH = {"x-nerdit-schedule-token": "tok"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setenv("NERDIT_SCHEDULE_TOKEN", "tok")
    monkeypatch.setattr(main, "fetch_feed", lambda: FEED)
    monkeypatch.setattr(main, "enrich", lambda title: ("cat", f"about {title}", 7))
    return TestClient(main.app)


def _runs():
    conn = main._db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY started_at")]
    conn.close()
    return rows


def test_refuses_without_the_token(client, monkeypatch):
    assert client.post("/_agent/run/daily").status_code == 403
    assert (
        client.post("/_agent/run/daily", headers={"x-nerdit-schedule-token": "no"}).status_code
        == 403
    )
    monkeypatch.delenv("NERDIT_SCHEDULE_TOKEN")
    assert (
        client.post("/_agent/run/daily", headers={"x-nerdit-schedule-token": ""}).status_code == 403
    )


def test_run_enriches_new_items_once(client):
    first = client.post("/_agent/run/daily", headers={**AUTH, "x-nerdit-schedule-run": "r1"})
    assert first.status_code == 202 and first.json() == {"accepted": "r1"}
    assert client.post(
        "/_agent/run/daily", headers={**AUTH, "x-nerdit-schedule-run": "r1"}
    ).json() == {"duplicate": "r1"}
    client.post("/_agent/run/daily", headers={**AUTH, "x-nerdit-schedule-run": "r2"})
    runs = _runs()
    assert [(r["run_id"], r["outcome"], r["items"], r["tokens"]) for r in runs] == [
        ("r1", "ok", 3, 21),
        ("r2", "ok", 0, 0),  # nothing new: no model call
    ]
    assert "about t0" in client.get("/").text


def test_a_run_that_cannot_start_does_not_block_the_next_one(client, monkeypatch):
    db = main._db
    monkeypatch.setattr(main, "_db", lambda: (_ for _ in ()).throw(main.sqlite3.OperationalError()))
    with pytest.raises(main.sqlite3.OperationalError):
        client.post("/_agent/run/daily", headers=AUTH)
    monkeypatch.setattr(main, "_db", db)
    again = client.post("/_agent/run/daily", headers={**AUTH, "x-nerdit-schedule-run": "r1"})
    assert again.json() == {"accepted": "r1"}


def test_a_feed_link_that_is_not_http_is_never_an_href(client, monkeypatch):
    hostile = [{"guid": "x", "title": "t", "link": "javascript:alert(1)"}]
    monkeypatch.setattr(main, "fetch_feed", lambda: hostile)
    client.post("/_agent/run/daily", headers=AUTH)
    page = client.get("/").text
    assert "javascript:" not in page and "href='#'" in page


def test_budget_exceeded_stops_the_run(client, monkeypatch):
    def over_budget(title):
        response = httpx.Response(429, request=httpx.Request("POST", "http://gateway/v1"))
        raise openai.RateLimitError("limit", response=response, body={"code": "budget_exceeded"})

    monkeypatch.setattr(main, "enrich", over_budget)
    client.post("/_agent/run/daily", headers={**AUTH, "x-nerdit-schedule-run": "r1"})
    assert _runs()[0]["outcome"] == "budget_exceeded"
    # The lock was released: the next run is accepted.
    assert client.post("/_agent/run/daily", headers=AUTH).status_code == 202
