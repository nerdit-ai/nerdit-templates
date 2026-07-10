"""Nerdit template: a minimal FastAPI backend starter (no AI).

A clean starting point for a JSON API deployed on Nerdit. Swagger UI is served
at /docs by FastAPI out of the box.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Nerdit FastAPI API Starter")


class EchoRequest(BaseModel):
    message: str


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe (Nerdit health-checks this path)."""
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "fastapi-api-starter", "docs": "/docs"}


@app.post("/api/echo")
def echo(req: EchoRequest) -> dict[str, str]:
    return {"echo": req.message}
