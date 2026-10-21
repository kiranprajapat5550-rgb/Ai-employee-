# AI Automation Services — AI Employee System

A free-first starter system for ten AI employee roles, MCP tools for agent briefs and task proposals, and a SQLite founder-approval queue.

## Included
- Ten role definitions: Chief of Staff, Operations, Sales Research, Sales Assistant, Marketing Strategist, Content Creator, Customer Support, Automation Engineer, Reporting Analyst, and Finance/Admin.
- MCP tools to list roles, prepare a bounded agent brief, submit a task proposal, and list proposals.
- SQLite proposal queue with pending/approved/rejected states and review audit fields.
- Unit tests and GitHub Actions.
- Make.com/n8n integration guidance.

## Safety boundary
**Approval is not execution.** This project deliberately contains no executor for sending messages, publishing content, deploying changes, or spending money. An approved proposal is an audit record only. Any future executor must be separate, authenticated, least-privileged, and require an explicit founder action on the exact action and payload.

## Setup
Requires Python 3.10+ (CI uses 3.12).

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The default SQLite database is `data/approvals.sqlite3`. Set `APPROVAL_DB_PATH` to change it. Keep the database and credentials out of source control.

## Run the MCP server

```bash
python -m ai_employee_system.mcp_server
```

Configure your MCP client to launch this command in the repository's Python environment. Exact configuration differs by client. The server exposes `list_employee_roles`, `create_agent_brief_tool`, `propose_task`, and `list_proposals`.

## Review workflow

The MCP interface creates and lists proposals. The `feature/secure-approval-api-bridge` branch adds an authenticated HTTP API in `ai_employee_system/api.py`, including a founder-token-protected review endpoint. Configure distinct `API_BEARER_TOKEN` and `FOUNDER_BEARER_TOKEN` values. Review decisions update the audit record only; no MCP tool or HTTP route executes approved work. Before using this beyond local testing, configure HTTPS, persistent storage, secret management, backups, rate limiting, and monitoring.

## Make.com / n8n
See [integration guidance](docs/make-n8n-integration.md). Start with internal drafts and test data; do not connect live send/publish/spend actions until a separate explicit execution gate and audit logging are implemented.
