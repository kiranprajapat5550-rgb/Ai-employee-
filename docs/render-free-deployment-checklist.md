# Render Free test deployment checklist

This checklist describes the current test-only deployment. It does not provision services,
change Render settings, configure secrets, or connect n8n.

## Current verified state

- Render service: `ai-employee-approval-api-test`
- Runtime: Python / Uvicorn
- Plan: Free, Singapore
- Health endpoint: `GET /health`
- Current health response reports `status: ok` and `execution: disabled`.
- API docs endpoints are disabled.
- Proposal and review endpoints fail closed while their bearer-token environment variables are not configured.
- The application has no external-action executor. Approving a proposal records a decision; it does not send, publish, deploy, or spend.
- GitHub Actions runs 40 unit tests plus a GET-only live smoke check.

## Important Free-tier limitation

The application defaults to SQLite at `data/approvals.sqlite3`. The Render Free service does not have a persistent disk configured, so SQLite data on its local filesystem must be treated as temporary and may be lost on restart or redeploy. Do not use this deployment as the sole store for important approvals or audit records. No database is currently connected to this service. A separate database in the same Render workspace is associated with another project; it is not assumed to be suitable or authorized for this application and has not been changed.

Before relying on persistent records, select and configure a persistent database/storage option, verify backup and restore, and test restart/redeploy behavior. Do not assume that committing the SQLite file to Git is a safe persistence solution.

## Before any non-test use

- [ ] Configure `API_BEARER_TOKEN` and `FOUNDER_BEARER_TOKEN` as separate, random values of at least 32 UTF-8 bytes, using the host's secret settings. Never commit them.
- [ ] Verify unauthenticated requests are denied and founder review requires the separate founder credential.
- [ ] Choose persistent storage and verify backup/restore and retention.
- [ ] Review rate limiting, monitoring, access restrictions, and incident recovery.
- [ ] Keep sending, publishing, deployment, payment, and other external actions disabled until a separate execution gate is designed and explicitly reviewed.
- [ ] Test with synthetic records only.

## Deployment caution

Render auto-deploy is enabled for `feature/secure-approval-api-bridge`. Merging a pull request into that branch can trigger a deployment. Review CI and the exact diff before merging. No merge is implied by this checklist.
