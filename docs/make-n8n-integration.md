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

## Make.com
Use a webhook or HTTP module to submit proposals to an authenticated adapter. Store secrets in Make connections/secret settings, never in repository files. The proposal endpoint should only create or read proposals; it must not execute actions.

## Required guardrails
- Start with test data and no external side effects.
- Use least-privilege credentials and rotate exposed keys.
- Require human review of exact outbound text and recipient/target.
- Put send/publish/spend/deploy actions behind a separate approval-and-execution gate.
- Add rate limits, deduplication, retries with backoff, and audit logging before production use.
