# Render authentication setup (manual, secret-safe)

This guide prepares the test service for authenticated use. It does not create, store, or reveal secrets. Do not put token values in source files, GitHub Actions logs, issue comments, screenshots, or chat.

## Current behavior

Until both tokens are configured correctly, protected endpoints deliberately return HTTP 503. This is fail-closed behavior, not an application crash. `GET /health` remains public and reports that external execution is disabled.

## Create two separate tokens

Generate each token privately on a trusted device using Python's standard library:

```python
import secrets
print(secrets.token_urlsafe(48))
```

Run it twice and keep the two outputs separate. Each value must be at least 32 UTF-8 bytes; the generated values above exceed that. Do not reuse the same token for both roles. Do not paste either value into a repository file or CI variable.

If you cannot run Python, use a trusted password manager's random-secret generator with at least 48 random bytes, then keep the API and founder tokens different.

## Add them in Render

1. Open the Render dashboard for `ai-employee-approval-api-test`.
2. Open the service's **Environment** settings.
3. Add `API_BEARER_TOKEN` with the first generated value.
4. Add `FOUNDER_BEARER_TOKEN` with the second generated value.
5. Save changes. Render may restart/redeploy the service; perform this only when ready for that restart.
6. Never include the values in a Git commit, deployment log, PR, or chat.

These variables authorize API access and founder review. Keep them private; anyone holding a token can act with that token's permissions.

## Verify after configuration

- Confirm `GET /health` returns HTTP 200 and `execution: disabled`.
- Without an Authorization header, `GET /proposals` should return HTTP 401 (not 200).
- With a valid API token, `GET /proposals` should return HTTP 200.
- An API token must not authorize `POST /proposals/{id}/review`; only the separate founder token should authorize review.
- Confirm the two token values are different before saving. The app fails closed on identical tokens for founder review.
- Use only synthetic test proposals. The API has no action executor, and approvals only record a decision.

## Important limitation

Do not treat this service as production-ready after token setup alone. SQLite on Render Free is temporary, and there is currently no persistent database connected to this service. Resolve storage, backups, monitoring, and operational controls before relying on approval/audit history.
