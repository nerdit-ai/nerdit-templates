# fastapi-api-starter

A minimal FastAPI backend starter (no AI). Endpoints: `GET /health`, `GET /`,
`POST /api/echo`, plus FastAPI's interactive docs at `/docs`.

## Deploy via the store

```bash
nerdit store deploy fastapi-api-starter --name my-api
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
