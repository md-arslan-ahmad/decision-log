"""
Repository layer — all database access lives here.

No business logic. No validation. Just persistence.
Translates between sqlite3.Row dicts and Decision dataclass instances.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import database
from models.decision import Decision, DecisionStatus

logger = logging.getLogger(__name__)


def _row_to_decision(row: dict) -> Decision:
    """Map a sqlite3 Row to a Decision dataclass."""
    return Decision(
        id=row["id"],
        title=row["title"],
        context=row["context"],
        decision_text=row["decision_text"],
        consequences=row["consequences"],
        status=DecisionStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


class DecisionsRepository:
    def get_all(self) -> list[Decision]:
        with database.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, context, decision_text, consequences, "
                "status, created_at, updated_at "
                "FROM decisions ORDER BY created_at DESC"
            ).fetchall()
        return [_row_to_decision(row) for row in rows]

    def get_by_id(self, decision_id: int) -> Optional[Decision]:
        with database.get_connection() as conn:
            row = conn.execute(
                "SELECT id, title, context, decision_text, consequences, "
                "status, created_at, updated_at "
                "FROM decisions WHERE id = ?",
                (decision_id,),
            ).fetchone()
        return _row_to_decision(row) if row else None

    def create(self, decision: Decision) -> Decision:
        now = datetime.now(timezone.utc).isoformat()
        with database.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO decisions "
                "(title, context, decision_text, consequences, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    decision.title,
                    decision.context,
                    decision.decision_text,
                    decision.consequences,
                    decision.status.value,
                    now,
                    now,
                ),
            )
            conn.commit()
            new_id = cursor.lastrowid

        saved = self.get_by_id(new_id)
        if saved is None:
            raise RuntimeError(f"Failed to retrieve decision after insert (id={new_id})")
        return saved

    def update(self, decision: Decision) -> Decision:
        now = datetime.now(timezone.utc).isoformat()
        with database.get_connection() as conn:
            conn.execute(
                "UPDATE decisions SET "
                "title=?, context=?, decision_text=?, consequences=?, status=?, updated_at=? "
                "WHERE id=?",
                (
                    decision.title,
                    decision.context,
                    decision.decision_text,
                    decision.consequences,
                    decision.status.value,
                    now,
                    decision.id,
                ),
            )
            conn.commit()

        updated = self.get_by_id(decision.id)
        if updated is None:
            raise RuntimeError(f"Failed to retrieve decision after update (id={decision.id})")
        return updated

    def delete(self, decision_id: int) -> None:
        with database.get_connection() as conn:
            conn.execute("DELETE FROM decisions WHERE id=?", (decision_id,))
            conn.commit()
