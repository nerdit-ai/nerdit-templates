# scheduled-ai-job

A FastAPI app that runs an AI job on a timer. Every day Nerdit calls the app,
the app fetches a public feed, asks a model for a category and a one-line
summary of each new item, and stores the result. Endpoints: `GET /` (items and
runs), `POST /_agent/run/daily` (the scheduler only), `GET /health`.

It is a pipeline, not an agent loop: one model call per item, and the code
decides everything else. Start here for "watch X and enrich Y"; reach for a
loop only when the model has to choose its own next step.

Needs a Nerdit daemon with schedules (`features.schedules_v1`, 0.10.0 or later).

## The three bricks

| In `nerdit.toml` | What Nerdit does |
|---|---|
| `[schedules.daily]` | Calls `POST /_agent/run/daily` at 07:00 UTC with `X-Nerdit-Schedule-Token` |
| `[ai.default] provider = "gateway"` | Injects `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL`; the provider key stays on the machine |
| `[limits] ai_tokens_month` | Optional ceiling for this app; past it the gateway answers `429 budget_exceeded` |

## Deploy via the store

```bash
nerdit store deploy scheduled-ai-job --name my-digest
nerdit schedules list my-digest          # next run
nerdit schedules run my-digest daily     # run it now
nerdit schedules runs my-digest daily    # "accepted": the app took the run
```

An agent calls `deploy_template` (template_id `scheduled-ai-job`), then
`run_schedule` and `list_schedule_runs`. The run's real outcome (items stored,
tokens used) is on the app's page and in its `runs` table: Nerdit records only
that the app accepted the call.

## One thing a human does: the model

The app waits until the machine has a model alias named `fast`. Define it once
in the console's **AI** page (provider, model, API key), or:

```bash
nerdit secrets set --shared --prompt OPENROUTER_API_KEY   # hidden prompt
nerdit ai routes set fast \
  --base-url https://openrouter.ai/api/v1 \
  --model openai/gpt-4o-mini \
  --key-ref '${secrets.shared.OPENROUTER_API_KEY}'
```

Never paste a key into a chat or onto a command line. Set a spending limit at
your provider too: `[limits]` isolates this app from the others on the same
key, it is not a guarantee on your invoice.

## Make it yours

- `FEED_URL` (a plain variable) points the job at another RSS feed. Only fetch
  a source whose terms allow it.
- `enrich()` holds the prompt; `MAX_ITEMS` bounds what one run can spend.
- Change the time in `[schedules.daily]` (`cron`, optional `timezone`). The
  shortest interval is 5 minutes.
- Writing from several processes, or need SQL from elsewhere? Swap SQLite for a
  managed Postgres with `[db.default]`. The "one run at a time" lock lives in
  this process's memory: with several workers, claim the run in the database
  instead.

## Why the token check

Another container on the same machine can reach this app's port, so the
route trusts `X-Nerdit-Schedule-Token` (compared in constant time with
`NERDIT_SCHEDULE_TOKEN`), not the caller's address. Nerdit strips that header
from every request arriving from outside. A second delivery of the same run
id is ignored, and a run that starts while another is going is skipped.

## Run locally

```bash
pip install -r requirements.txt
NERDIT_SCHEDULE_TOKEN=dev uvicorn main:app --reload
curl -X POST localhost:8000/_agent/run/daily -H 'X-Nerdit-Schedule-Token: dev'
```

Without Nerdit the model defaults to a local Ollama at `localhost:11434`.
Tests: `pip install pytest httpx && pytest -q`.
