"""Nerdit template: receive Stripe webhooks.

Nerdit checks the Stripe-Signature on the machine before this app sees the
request, so the handler stays small: dedupe, log, answer 200.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request

logger = logging.getLogger("uvicorn.error")
app = FastAPI(title="Nerdit Stripe Webhook")

# ponytail: in-memory, one process, forgotten on restart; a UNIQUE event-id
# column in your database when a duplicate would cost money.
_seen: dict[str, None] = {}
_SEEN_MAX = 1000


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe (Nerdit health-checks this path)."""
    return {"status": "ok"}


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict[str, bool]:
    # The machine verified the Stripe-Signature before forwarding, then set
    # X-Nerdit-Hook to the hook's name. Nerdit strips that header from every
    # other request, so it is proof only for requests that came through a Nerdit
    # route: do not publish this app's port any other way.
    if request.headers.get("x-nerdit-hook") != "stripe":
        raise HTTPException(status_code=403, detail="not a verified Stripe delivery")
    try:
        event = await request.json()
        event_id, event_type = str(event["id"]), str(event["type"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="not a Stripe event") from None
    # Delivery is at least once: Stripe and Nerdit both retry.
    if event_id in _seen:
        return {"duplicate": True}
    logger.info("stripe event %s %s", event_type, event_id)
    # Handle event_type here (checkout.session.completed, invoice.paid, ...).
    # Raise on failure: the id is recorded only after success, so the retry
    # from Stripe or Nerdit runs the handler again instead of being skipped.
    _seen[event_id] = None
    if len(_seen) > _SEEN_MAX:
        del _seen[next(iter(_seen))]  # oldest first: dicts keep insertion order
    return {"received": True}
