"""SQLite proposal queue. Approval records consent only; it never executes actions."""
import json
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class ApprovalQueue:
    def __init__(self, db_path: str | Path = "data/approvals.sqlite3") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._transaction() as conn:
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

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit or roll back one transaction and always close its connection."""
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def submit(self, title: str, description: str, action_type: str = "internal", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not title.strip() or not description.strip():
            raise ValueError("title and description must not be empty")
        created = datetime.now(timezone.utc).isoformat()
        with self._transaction() as conn:
            cur = conn.execute("INSERT INTO proposals(title,description,action_type,payload_json,status,created_at) VALUES(?,?,?,?,?,?)",
                (title.strip(), description.strip(), action_type.strip() or "internal", json.dumps(payload or {}, sort_keys=True), "pending_approval", created))
            proposal_id = cur.lastrowid
        return self.get(proposal_id)

    def get(self, proposal_id: int) -> dict[str, Any]:
        with self._transaction() as conn:
            row = conn.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
        if row is None:
            raise KeyError(f"Proposal {proposal_id} not found")
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._transaction() as conn:
            if status:
                rows = conn.execute("SELECT id FROM proposals WHERE status=? ORDER BY id", (status,)).fetchall()
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
            cur = conn.execute("""UPDATE proposals SET status=?, reviewed_at=?, reviewer=?, review_note=?
                WHERE id=? AND status='pending_approval'""", (decision, reviewed, reviewer.strip(), note.strip(), proposal_id))
            if cur.rowcount != 1:
                exists = conn.execute("SELECT id FROM proposals WHERE id=?", (proposal_id,)).fetchone()
                if exists is None:
                    raise KeyError(f"Proposal {proposal_id} not found")
                raise ValueError("proposal has already been reviewed")
        # Intentionally no executor: approval is an audit record, not permission to auto-run.
        return self.get(proposal_id)
