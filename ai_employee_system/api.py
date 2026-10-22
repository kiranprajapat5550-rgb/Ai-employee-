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


MAX_REQUEST_BODY_BYTES = 32 * 1024


class RequestBodyLimitMiddleware:
    """Bound incoming write-request bodies before JSON parsing and validation."""

    def __init__(self, app, max_body_bytes: int = MAX_REQUEST_BODY_BYTES) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        content_lengths = [
            value for key, value in scope.get("headers", [])
            if key.lower() == b"content-length"
        ]
        if len(content_lengths) > 1:
            await self._bad_request(send)
            return

        declared_length = None
        if content_lengths:
            raw_length = content_lengths[0]
            # Content-Length must be a non-negative decimal integer; reject ambiguous values.
            if not raw_length or not raw_length.isdigit():
                await self._bad_request(send)
                return
            try:
                declared_length = int(raw_length)
            except ValueError:
                # Extremely long digit strings can exceed Python's safe int conversion limit.
                await self._bad_request(send)
                return
            if declared_length > self.max_body_bytes:
                await self._too_large(send)
                return

        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > self.max_body_bytes:
                await self._too_large(send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        if declared_length is not None and total != declared_length:
            await self._bad_request(send)
            return

        body = b"".join(chunks)
        delivered = False

        async def replay_body():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay_body, send)

    @staticmethod
    async def _bad_request(send) -> None:
        body = b'{"detail":"invalid request body length"}'
        await send({
            "type": "http.response.start",
            "status": 400,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        })
        await send({"type": "http.response.body", "body": body})

    @staticmethod
    async def _too_large(send) -> None:
        body = b'{"detail":"request body exceeds 32768 bytes"}'
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        })
        await send({"type": "http.response.body", "body": body})


class ProposalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    action_type: str = Field(
        default="internal",
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z][A-Za-z0-9_.:-]{0,79}$",
    )
    payload: dict[str, Any] = Field(default_factory=dict)


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(approved|rejected)$")
    note: str = Field(default="", max_length=2000)


def _require_token(expected_env: str, authorization: str | None) -> None:
    expected = os.getenv(expected_env, "")
    if len(expected.encode("utf-8")) < 32:
        # Keep configuration details out of responses and fail closed on weak tokens.
        raise HTTPException(status_code=503, detail="Service authentication is not configured correctly")
    scheme, _, supplied = (authorization or "").partition(" ")
    if (
        scheme.lower() != "bearer"
        or not supplied
        or not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


def create_app(queue: ApprovalQueue | None = None) -> FastAPI:
    """Create an app; injectable queue keeps tests isolated from the default database."""
    approval_queue = queue or ApprovalQueue(os.getenv("APPROVAL_DB_PATH", "data/approvals.sqlite3"))
    app = FastAPI(
        title="AI Employee Approval API",
        version="0.1.0",
        description="Authenticated proposal and founder-review API. No action executor is included.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(RequestBodyLimitMiddleware)

    def require_api_token(authorization: str | None = Header(default=None)) -> None:
        _require_token("API_BEARER_TOKEN", authorization)

    def require_founder_token(authorization: str | None = Header(default=None)) -> None:
        api_token = os.getenv("API_BEARER_TOKEN", "")
        founder_token = os.getenv("FOUNDER_BEARER_TOKEN", "")
        if len(api_token.encode("utf-8")) < 32 or len(founder_token.encode("utf-8")) < 32:
            raise HTTPException(
                status_code=503,
                detail="Service authentication is not configured correctly",
            )
        if hmac.compare_digest(api_token.encode("utf-8"), founder_token.encode("utf-8")):
            raise HTTPException(
                status_code=503,
                detail="Service authentication is not configured correctly",
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
