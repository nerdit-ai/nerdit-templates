"""Nerdit template: a FastAPI chat app wired to a local model.

The app never hardcodes a model endpoint. Nerdit resolves the ``[ai.default]``
binding in ``nerdit.toml`` at launch and injects three env vars:

    OPENAI_BASE_URL   OpenAI-compatible endpoint (local Ollama or an external API)
    OPENAI_API_KEY    key for that endpoint (a local placeholder for Ollama)
    OPENAI_MODEL      the model name to call

So the same code runs against a local `llama3.1:8b` or a hosted API — swap the
binding, not the app.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from openai import OpenAI
from pydantic import BaseModel

app = FastAPI(title="Nerdit FastAPI AI Chat")

# Fall back to a local Ollama default so the app is runnable outside Nerdit too;
# under Nerdit these are overridden by the injected binding env.
MODEL = os.environ.get("OPENAI_MODEL", "llama3.1:8b")


def _client() -> OpenAI:
    return OpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", "nerdit-local"),
    )


class ChatRequest(BaseModel):
    message: str


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — never calls the model (Nerdit health-checks this path)."""
    return {"status": "ok", "model": MODEL}


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict[str, str]:
    """Send one user message to the bound model and return its reply."""
    completion = _client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": req.message}],
    )
    return {"reply": completion.choices[0].message.content or ""}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _INDEX_HTML


_INDEX_HTML = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Nerdit AI Chat</title>
  <style>
    :root { color-scheme: light dark; }
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; display: flex;
           justify-content: center; background: Canvas; color: CanvasText; }
    main { width: min(720px, 100%); padding: 24px; display: flex;
           flex-direction: column; gap: 16px; height: 100vh; }
    h1 { font-size: 1.25rem; margin: 0; }
    #log { flex: 1; overflow-y: auto; display: flex; flex-direction: column;
           gap: 10px; padding-right: 4px; }
    .msg { padding: 10px 14px; border-radius: 12px; max-width: 80%;
           white-space: pre-wrap; line-height: 1.4; }
    .user { align-self: flex-end; background: #2563eb; color: #fff; }
    .bot { align-self: flex-start; background: rgba(127,127,127,.18); }
    form { display: flex; gap: 8px; }
    input { flex: 1; padding: 12px; border-radius: 10px;
            border: 1px solid rgba(127,127,127,.4); background: Field;
            color: FieldText; font-size: 1rem; }
    button { padding: 12px 18px; border: 0; border-radius: 10px;
             background: #2563eb; color: #fff; font-size: 1rem; cursor: pointer; }
    button:disabled { opacity: .5; cursor: default; }
  </style>
</head>
<body>
  <main>
    <h1>Nerdit AI Chat</h1>
    <div id="log"></div>
    <form id="form">
      <input id="input" autocomplete="off" placeholder="Ask the model anything…" />
      <button id="send" type="submit">Send</button>
    </form>
  </main>
  <script>
    const log = document.getElementById("log");
    const form = document.getElementById("form");
    const input = document.getElementById("input");
    const send = document.getElementById("send");
    function bubble(text, who) {
      const el = document.createElement("div");
      el.className = "msg " + who;
      el.textContent = text;
      log.appendChild(el);
      log.scrollTop = log.scrollHeight;
      return el;
    }
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const message = input.value.trim();
      if (!message) return;
      bubble(message, "user");
      input.value = "";
      send.disabled = true;
      const pending = bubble("…", "bot");
      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message }),
        });
        const data = await res.json();
        pending.textContent = res.ok ? data.reply : (data.message || "Error");
      } catch (err) {
        pending.textContent = "Request failed: " + err;
      } finally {
        send.disabled = false;
        input.focus();
      }
    });
  </script>
</body>
</html>
"""
