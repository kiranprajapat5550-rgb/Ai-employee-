"""Approval queue backed by PostgreSQL when DATABASE_URL is set, otherwise SQLite.

Approval records consent only; this module never executes external actions.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class ApprovalQueue:
    def __init__(self, db_path: str | Path = "data/approvals.sqlite3") -> None:
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.is_postgres = bool(self.database_url)
        self._uri = False
        self._anchor_connection = None

        if self.is_postgres:
            if not self.database_url.startswith(("postgres://", "postgresql://")):
                raise ValueError("DATABASE_URL must be a PostgreSQL connection URL")
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError("PostgreSQL configured but psycopg is not installed") from exc
            self._psycopg = psycopg
            self._dict_row = dict_row
            self.db_path = "<postgresql>"
        else:
            requested_path = str(db_path)
            self._uri = requested_path == ":memory:"
            if self._uri:
                self.db_path = f"file:approvalqueue_{uuid4().hex}?mode=memory&cache=shared"
                self._anchor_connection = sqlite3.connect(self.db_path, uri=True)
            else:
                self.db_path = requested_path
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with self._transaction() as conn:
            if self.is_postgres:
                conn.execute("""CREATE TABLE IF NOT EXISTS proposals (
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending_approval','approved','rejected')),
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    reviewer TEXT,
                    review_note TEXT
                )""")
            else:
                conn.execute("""CREATE TABLE IF NOT EXISTS proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending_approval','approved','rejected')),
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    reviewer TEXT,
                    review_note TEXT
                )""")

    def _connect(self):
        if self.is_postgres:
            return self._psycopg.connect(self.database_url, row_factory=self._dict_row)
        conn = sqlite3.connect(self.db_path, uri=self._uri)
        conn.row_factory = sqlite3.Row
        return conn

    def _sql(self, statement: str) -> str:
        return statement.replace("?", "%s") if self.is_postgres else statement

    @contextmanager
    def _transaction(self) -> Iterator[Any]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self) -> None:
        if self._anchor_connection is not None:
            self._anchor_connection.close()
            self._anchor_connection = None

    def submit(self, title: str, description: str, action_type: str = "internal", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not title.strip() or not description.strip():
            raise ValueError("title and description must not be empty")
        created = datetime.now(timezone.utc).isoformat()
        with self._transaction() as conn:
            sql = """INSERT INTO proposals(title,description,action_type,payload_json,status,created_at)
                     VALUES(?,?,?,?,?,?)"""
            if self.is_postgres:
                cur = conn.execute(self._sql(sql) + " RETURNING id",
                    (title.strip(), description.strip(), action_type.strip() or "internal", json.dumps(payload or {}, sort_keys=True), "pending_approval", created))
                proposal_id = cur.fetchone()["id"]
            else:
                cur = conn.execute(sql,
                    (title.strip(), description.strip(), action_type.strip() or "internal", json.dumps(payload or {}, sort_keys=True), "pending_approval", created))
                proposal_id = cur.lastrowid
        return self.get(proposal_id)

    def get(self, proposal_id: int) -> dict[str, Any]:
        with self._transaction() as conn:
            row = conn.execute(self._sql("SELECT * FROM proposals WHERE id=?"), (proposal_id,)).fetchone()
        if row is None:
            raise KeyError(f"Proposal {proposal_id} not found")
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._transaction() as conn:
            if status:
                rows = conn.execute(self._sql("SELECT id FROM proposals WHERE status=? ORDER BY id"), (status,)).fetchall()
            else:
                rows = conn.execute("SELECT id FROM proposals ORDER BY id").fetchall()
        return [self.get(row["id"]) for row in rows]

    def review(self, proposal_id: int, decision: str, reviewer: str, note: str = "") -> dict[str, Any]:
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be 'approved' or 'rejected'")
        if not reviewer.strip():
            raise ValueError("reviewer is required")
        reviewed = datetime.now(timezone.utc).isoformat()
        with self._transaction() as conn:
            cur = conn.execute(self._sql("""UPDATE proposals SET status=?, reviewed_at=?, reviewer=?, review_note=?
                WHERE id=? AND status='pending_approval'"""), (decision, reviewed, reviewer.strip(), note.strip(), proposal_id))
            if cur.rowcount != 1:
                exists = conn.execute(self._sql("SELECT id FROM proposals WHERE id=?"), (proposal_id,)).fetchone()
                if exists is None:
                    raise KeyError(f"Proposal {proposal_id} not found")
                raise ValueError("proposal has already been reviewed")
        return self.get(proposal_id)
