"""Authenticated HTTP API for task proposals and founder review.

This API only records proposals and review decisions. It never executes external actions.
Set API_BEARER_TOKEN for proposal read/write endpoints and FOUNDER_BEARER_TOKEN
for review decisions. Use HTTPS at the hosting layer.
"""
import hmac
import json
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from .approvals import ApprovalQueue


class ProposalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    action_type: str = Field(default="internal", min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(approved|rejected)$")
    note: str = Field(default="", max_length=2000)


def _require_token(expected_env: str, authorization: str | None) -> None:
    expected = os.getenv(expected_env, "")
    if not expected:
        raise HTTPException(status_code=503, detail=f"{expected_env} is not configured")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


def create_app(queue: ApprovalQueue | None = None) -> FastAPI:
    """Create an app; injectable queue keeps tests isolated from the default database."""
    approval_queue = queue or ApprovalQueue(os.getenv("APPROVAL_DB_PATH", "data/approvals.sqlite3"))
    app = FastAPI(
        title="AI Employee Approval API",
        version="0.1.0",
        description="Authenticated proposal and founder-review API. No action executor is included.",
    )

    def require_api_token(authorization: str | None = Header(default=None)) -> None:
        _require_token("API_BEARER_TOKEN", authorization)

    def require_founder_token(authorization: str | None = Header(default=None)) -> None:
        api_token = os.getenv("API_BEARER_TOKEN", "")
        founder_token = os.getenv("FOUNDER_BEARER_TOKEN", "")
        if not api_token or not founder_token:
            raise HTTPException(
                status_code=503,
                detail="API_BEARER_TOKEN and FOUNDER_BEARER_TOKEN must both be configured",
            )
        if hmac.compare_digest(api_token, founder_token):
            raise HTTPException(
                status_code=503,
                detail="Founder and API bearer tokens must be different",
            )
        _require_token("FOUNDER_BEARER_TOKEN", authorization)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "execution": "disabled"}

    @app.post("/proposals", status_code=201, dependencies=[Depends(require_api_token)])
    def create_proposal(body: ProposalCreate) -> dict[str, Any]:
        try:
            payload_text = json.dumps(body.payload, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="payload must be JSON serializable") from exc
        if len(payload_text.encode("utf-8")) > 10000:
            raise HTTPException(status_code=413, detail="payload exceeds 10000 bytes")
        try:
            return approval_queue.submit(
                body.title, body.description, body.action_type, body.payload
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/proposals", dependencies=[Depends(require_api_token)])
    def list_proposals(status: str = Query(default="pending_approval")) -> list[dict[str, Any]]:
        if status not in {"pending_approval", "approved", "rejected", "all"}:
            raise HTTPException(status_code=422, detail="unsupported status filter")
        return approval_queue.list(None if status == "all" else status)

    @app.get("/proposals/{proposal_id}", dependencies=[Depends(require_api_token)])
    def get_proposal(proposal_id: int) -> dict[str, Any]:
        try:
            return approval_queue.get(proposal_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="proposal not found") from exc

    @app.post("/proposals/{proposal_id}/review", dependencies=[Depends(require_founder_token)])
    def review_proposal(proposal_id: int, body: ReviewDecision) -> dict[str, Any]:
        try:
            # Reviewer identity comes from the dedicated founder credential, not request input.
            return approval_queue.review(proposal_id, body.decision, "founder_api", body.note)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="proposal not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return app


app = create_app()
