# fastapi-ai-chat

A FastAPI chat app wired to a local model through Nerdit's `[ai.default]`
binding. The app reads `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL`
(injected by Nerdit at launch) and calls the OpenAI-compatible chat endpoint —
so the same code runs against a local Ollama model or an external API.

## Deploy via the store

```bash
nerdit serve llama3.1:8b        # the app declares it needs a model
nerdit store deploy fastapi-ai-chat --name my-chat
```

Open the printed URL and chat. `[ai.default]` gates the deploy on a served
model, so serve one first.

## Run locally (outside Nerdit)

```bash
pip install -r requirements.txt
OPENAI_BASE_URL=http://localhost:11434/v1 OPENAI_MODEL=llama3.1:8b \
  uvicorn main:app --reload
```
