# stripe-webhook

A minimal FastAPI app that receives Stripe events through a Nerdit webhook.
Endpoints: `POST /webhooks/stripe`, `GET /health`.

The machine checks the `Stripe-Signature` with your signing secret before the
app sees the request, then adds `X-Nerdit-Hook: stripe`. The app trusts that
header, skips an event id it has already seen, logs the event type and answers
`200`. A request without the header gets `403`.

## Deploy via the store

```bash
nerdit store deploy stripe-webhook --name my-stripe
nerdit share my-stripe        # a webhook only answers on a shared app
nerdit hooks list my-stripe   # prints the Webhook URL
```

An agent calls `deploy_template` (template_id `stripe-webhook`), then
`share_service`, then `list_hooks` for the URL. In the console, deploy the
template, then open the app's **… → Webhooks** and copy the **Webhook URL**.

The URL needs a linked machine (a box always is). The app also receives it as
`NERDIT_HOOK_STRIPE_URL` from its next launch.

## Connect Stripe

1. In Stripe, open **Developers → Webhooks → Add endpoint**, paste the Webhook
   URL and pick the events.
2. Copy the signing secret Stripe shows, then run
   `nerdit secrets set my-stripe --prompt NERDIT_HOOK_STRIPE_SECRET` (hidden
   prompt). The console's Webhooks panel can also replace it.
3. Until the secret is set, deliveries wait at the edge: Nerdit answers Stripe
   `202` and retries for up to 24 h.

Do not pass the secret with `nerdit store deploy --secret`: other processes can
read the command line.

## Test with the Stripe CLI

```bash
stripe trigger checkout.session.completed
nerdit logs my-stripe   # shows "stripe event checkout.session.completed evt_..."
```

Use test mode. A test-mode endpoint has its own signing secret.
Do not use `stripe listen --forward-to`: it bypasses Nerdit, so the request
lacks `X-Nerdit-Hook` and gets `403`.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
curl -X POST localhost:8000/webhooks/stripe -H 'X-Nerdit-Hook: stripe' \
  -H 'Content-Type: application/json' -d '{"id":"evt_test","type":"ping"}'
```

Locally nothing checks the signature, so the header is a stand-in.

## Production notes

- Deduplication lives in memory. Use a UNIQUE event-id column for anything that
  moves money.
- `NERDIT_HOOK_STRIPE_SECRET` is in the app's environment if you want to verify
  again with the Stripe SDK.
- Never publish the app's port another way: the header proves verification only
  on requests that came through a Nerdit route.
