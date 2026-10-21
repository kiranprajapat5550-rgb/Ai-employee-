"""MCP server exposing safe brief/proposal tools; it does not execute approved actions."""
import json
import os
from mcp.server.fastmcp import FastMCP
from .approvals import ApprovalQueue
from .roles import ROLES, create_agent_brief, create_task_proposal

mcp = FastMCP("ai-automation-services")
queue = ApprovalQueue(os.getenv("APPROVAL_DB_PATH", "data/approvals.sqlite3"))

@mcp.tool()
def list_employee_roles() -> str:
    """List the ten configured AI employee roles and their responsibilities."""
    return json.dumps([r.__dict__ for r in ROLES], ensure_ascii=False)

@mcp.tool()
def create_agent_brief_tool(role_key: str, objective: str, context: str = "") -> str:
    """Prepare a bounded agent brief. This tool performs no external action."""
    return json.dumps(create_agent_brief(role_key, objective, context), ensure_ascii=False)

@mcp.tool()
def propose_task(title: str, description: str, action_type: str = "internal", payload_json: str = "{}") -> str:
    """Submit a task proposal for founder review; approval never triggers execution."""
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError("payload_json must be valid JSON") from exc
    proposal = create_task_proposal(title, description, action_type)
    return json.dumps(queue.submit(proposal["title"], proposal["description"], proposal["action_type"], payload), ensure_ascii=False)

@mcp.tool()
def list_proposals(status: str = "pending_approval") -> str:
    """List proposals. Use status='all' to list every proposal."""
    return json.dumps(queue.list(None if status == "all" else status), ensure_ascii=False)

if __name__ == "__main__":
    mcp.run()
