# Make.com and n8n integration

This repository provides the agent brief/proposal layer. It does not currently connect to Make.com or n8n APIs and does not execute approved proposals.

## Safe starter pattern
1. Trigger: manual test, schedule, or webhook with authenticated access.
2. Validate input and reject unknown action types.
3. Ask the AI employee to prepare a brief or draft only.
4. Call the MCP `propose_task` tool (or create a proposal through a small internal adapter).
5. Notify the founder with proposal ID, exact content, target, cost (if any), and consequences.
6. Founder reviews the proposal in the approval queue.
7. Keep the execution workflow separate. An approval record alone must never trigger that workflow. Require a second explicit, authenticated action for sending, publishing, deploying, or spending.
8. Log the actor, decision, timestamp, external response, and idempotency key.

## n8n
Run the MCP server in a trusted environment with persistent storage. Use an MCP-compatible client if available in your n8n version, or build a small authenticated internal adapter. Do not expose the MCP server publicly without authentication and network restrictions.

## Connect n8n to the authenticated HTTP API (proposal-only)

This section is a setup guide, not an imported or activated workflow. It does not modify any existing n8n workflow.

### Prerequisites
- The API is deployed on a host you have reviewed for HTTPS, persistent storage, pricing, and access controls.
- The API base URL is known and begins with `https://`.
- `API_BEARER_TOKEN` is configured on the API host and stored in an n8n Header Auth credential. Do not use the founder token in routine automation.
- Test with synthetic content only.

### Create a proposal from n8n
1. Create a **new test workflow**; leave existing workflows untouched and keep this one inactive until manually tested.
2. Add **Manual Trigger**.
3. Add **Edit Fields (Set)** and create only safe test fields, for example:
   - `title`: `n8n test draft — no publishing`
   - `description`: `Test proposal created by n8n. Do not send or publish.`
   - `action_type`: `internal_test`
   - `payload`: an object such as `{"channel":"test","action_executed":false}`
4. Add an **HTTP Request** node:
   - Method: `POST`
   - URL: `https://YOUR-API-HOST/proposals` (replace with the real HTTPS base URL)
   - Authentication: **Generic Credential Type → Header Auth**; select a credential holding `Authorization: Bearer <API_BEARER_TOKEN>`. Store the value in n8n credentials, never in node expressions or exported workflow JSON.
   - Send Body: on; Body Content Type: JSON; specify `title`, `description`, `action_type`, and `payload` from the Edit Fields node.
   - Do not add any email, social publishing, deployment, payment, or other external-action nodes.
5. Execute manually once with test data. Expect HTTP `201` and a response with `status: pending_approval`. If the API is not deployed or configured, stop and fix that prerequisite rather than substituting a public or insecure endpoint.
6. Optionally add a second **HTTP Request** node using `GET https://YOUR-API-HOST/proposals?status=pending_approval` and the same API credential to verify the record exists.
7. Keep the workflow inactive after testing until you have reviewed access, retention, and logging.

### Founder review boundary
- Never place `FOUNDER_BEARER_TOKEN` in the routine proposal workflow.
- Do not call `POST /proposals/{id}/review` from an unattended workflow.
- An `approved` database status is an audit record only; it does not authorize or trigger execution.
- This guide does not configure or execute anything in your n8n account.

## Make.com
Use a webhook or HTTP module to submit proposals to an authenticated adapter. Store secrets in Make connections/secret settings, never in repository files. The proposal endpoint should only create or read proposals; it must not execute actions.

## Required guardrails
- Start with test data and no external side effects.
- Use least-privilege credentials and rotate exposed keys.
- Require human review of exact outbound text and recipient/target.
- Put send/publish/spend/deploy actions behind a separate approval-and-execution gate.
- Add rate limits, deduplication, retries with backoff, and audit logging before production use.
