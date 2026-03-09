"""
Decision domain model — a pure Python dataclass with no framework dependency.

The state machine (transition rules) lives here, close to the data it guards.
Keeping this free of framework imports means it's trivially unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class DecisionStatus(str, Enum):
    PROPOSED   = "proposed"
    ACCEPTED   = "accepted"
    REJECTED   = "rejected"
    SUPERSEDED = "superseded"


# Explicit allow-list. Anything not in this map is forbidden.
VALID_TRANSITIONS: dict[DecisionStatus, frozenset[DecisionStatus]] = {
    DecisionStatus.PROPOSED:   frozenset({DecisionStatus.ACCEPTED, DecisionStatus.REJECTED}),
    DecisionStatus.ACCEPTED:   frozenset({DecisionStatus.SUPERSEDED}),
    DecisionStatus.REJECTED:   frozenset(),
    DecisionStatus.SUPERSEDED: frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a status transition violates domain rules."""
    pass


@dataclass
class Decision:
    title:         str
    context:       str
    decision_text: str
    status:        DecisionStatus = DecisionStatus.PROPOSED
    consequences:  Optional[str]  = None
    id:            Optional[int]  = None
    created_at:    datetime       = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:    datetime       = field(default_factory=lambda: datetime.now(timezone.utc))

    def transition(self, new_status: DecisionStatus) -> None:
        """
        Advance status according to the finite state machine.
        This is the ONLY correct way to change status — never assign directly.
        Raises InvalidTransitionError for disallowed moves.
        """
        allowed = VALID_TRANSITIONS.get(self.status, frozenset())
        if new_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition '{self.status.value}' -> '{new_status.value}'. "
                f"Allowed from '{self.status.value}': "
                f"{[s.value for s in allowed] or 'none'}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Serialise to a JSON-safe plain dict. Column aliases are stable API surface."""
        return {
            "id":           self.id,
            "title":        self.title,
            "context":      self.context,
            "decision":     self.decision_text,
            "consequences": self.consequences,
            "status":       self.status.value,
            "created_at":   self.created_at.isoformat(),
            "updated_at":   self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Decision id={self.id} status={self.status.value!r} title={self.title!r}>"
