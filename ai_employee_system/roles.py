"""Role catalog and safe task-proposal helpers."""
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class EmployeeRole:
    key: str
    title: str
    responsibility: str

ROLES = (
    EmployeeRole("ceo_chief_of_staff", "CEO / Chief of Staff", "Summarize priorities and prepare decisions; cannot approve its own proposals."),
    EmployeeRole("operations_manager", "Operations Manager", "Track delivery, SOPs, blockers, and service quality."),
    EmployeeRole("sales_researcher", "Sales Researcher", "Research prospects using permitted sources and prepare evidence-backed briefs."),
    EmployeeRole("sales_assistant", "Sales Assistant", "Draft outreach and follow-ups for founder review; never send them."),
    EmployeeRole("marketing_strategist", "Marketing Strategist", "Prepare campaign plans, positioning, and content briefs."),
    EmployeeRole("content_creator", "Content Creator", "Draft posts, captions, scripts, and creative briefs for review."),
    EmployeeRole("customer_support", "Customer Support Assistant", "Classify support requests and draft replies; do not send externally."),
    EmployeeRole("automation_engineer", "Automation Engineer", "Design and document Make/n8n workflows; do not deploy without approval."),
    EmployeeRole("analyst", "Reporting Analyst", "Summarize supplied metrics and flag data limitations."),
    EmployeeRole("finance_admin", "Finance & Admin Assistant", "Prepare budget summaries and invoice drafts; cannot spend money or move funds."),
)

ROLE_BY_KEY = {role.key: role for role in ROLES}

def create_agent_brief(role_key: str, objective: str, context: str = "") -> dict[str, Any]:
    """Create a bounded work brief; no execution or external side effects occur."""
    if role_key not in ROLE_BY_KEY:
        raise ValueError(f"Unknown role: {role_key}")
    if not objective.strip():
        raise ValueError("objective must not be empty")
    role = ROLE_BY_KEY[role_key]
    return {"role": role.key, "title": role.title, "responsibility": role.responsibility,
            "objective": objective.strip(), "context": context.strip(),
            "constraints": ["Propose only; do not execute external actions.",
                            "Request founder approval for consequential actions.",
                            "Never expose credentials or secrets."]}

def create_task_proposal(title: str, description: str, action_type: str = "internal") -> dict[str, str]:
    """Build a proposal payload for the approval queue, not an executable command."""
    if not title.strip() or not description.strip():
        raise ValueError("title and description must not be empty")
    return {"title": title.strip(), "description": description.strip(),
            "action_type": action_type.strip() or "internal", "status": "pending_approval"}
