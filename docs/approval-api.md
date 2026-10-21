# Authenticated approval API bridge

This bridge exposes the existing SQLite proposal queue over HTTP. It only creates, reads, and reviews proposal records. It contains **no executor** and cannot send messages, publish content, deploy code, or spend money.

## Endpoints

- `GET /health` — public liveness check; returns `execution: disabled`.
- `POST /proposals` — create a pending proposal; requires `API_BEARER_TOKEN`.
- `GET /proposals?status=pending_approval` — list proposals; requires `API_BEARER_TOKEN`. Supported filters: `pending_approval`, `approved`, `rejected`, `all`.
- `GET /proposals/{id}` — read one proposal; requires `API_BEARER_TOKEN`.
- `POST /proposals/{id}/review` — record an approval or rejection; requires the separate `FOUNDER_BEARER_TOKEN`.

Use an Authorization header such as `Authorization: Bearer <token>`. Do not put tokens in URLs, workflow JSON, commits, or logs. Generate distinct high-entropy values for the two tokens and store them only in the hosting platform's secret environment settings. Use HTTPS; do not expose this API over plain HTTP.

## Request examples

Create a proposal:

```json
{
  "title": "Draft social post",
  "description": "Prepare a draft for founder review only.",
  "action_type": "content_draft",
  "payload": {"channel": "test"}
}
```

Review a proposal:

```json
{
  "decision": "approved",
  "note": "Reviewed draft"
}
```

The reviewer is recorded as `founder_api`, based on possession of the separate founder token; the request cannot choose a reviewer identity. Approval is only a database decision and does not authorize or trigger execution.

## Run locally

Install requirements, then configure secrets in the shell environment (never commit them):

```bash
export API_BEARER_TOKEN='replace-with-a-long-random-secret'
export FOUNDER_BEARER_TOKEN='use-a-different-long-random-secret'
export APPROVAL_DB_PATH='data/approvals.sqlite3'
uvicorn ai_employee_system.api:app --host 127.0.0.1 --port 8000
```

The app does not set up public hosting. Deploying it requires a hosting choice, persistent storage for SQLite, HTTPS, secret configuration, and review of the host's pricing and limits. None of those steps are performed by this repository change.

## Before n8n integration

1. Deploy only after reviewing hosting costs, persistent disk support, and network exposure.
2. Put the API token in an n8n credential/secret setting, not in a node's literal text or committed workflow JSON.
3. Start with `POST /proposals` and `GET /proposals`; do not connect send/publish/spend actions.
4. Keep the founder token out of ordinary workflow nodes. Do not add the review endpoint to an automation until the founder approval channel and token handling have been reviewed.
5. Add rate limiting, request-size limits at the proxy, audit monitoring, and key rotation before production use.

The API is a bridge for the proposal queue, not a production-ready public service by itself.
