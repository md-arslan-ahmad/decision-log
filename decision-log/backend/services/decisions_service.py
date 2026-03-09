"""
Service layer — business rules live here.

Responsibilities:
  - Validate input before touching the DB (manual validation, no Pydantic available)
  - Enforce domain rules (valid transitions, field constraints)
  - Log meaningful events for observability
  - Raise typed exceptions that routes translate to HTTP errors

Does NOT know about Flask request/response objects.
Does NOT access the database directly — always goes through the repository.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from models.decision import Decision, DecisionStatus, InvalidTransitionError
from repositories.decisions_repository import DecisionsRepository

logger = logging.getLogger(__name__)


# ── Typed exceptions ───────────────────────────────────────────────────────────

class NotFoundError(Exception):
    """Decision with the given ID does not exist."""
    pass


class ValidationError(ValueError):
    """Input failed domain validation. `errors` is a list of field-level messages."""
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(str(errors))


# ── Validation helpers ────────────────────────────────────────────────────────

@dataclass
class FieldError:
    field: str
    message: str

    def to_dict(self) -> dict:
        return {"field": self.field, "message": self.message}


def _validate_create(data: dict) -> list[FieldError]:
    errors: list[FieldError] = []

    title = str(data.get("title", "")).strip()
    if not title:
        errors.append(FieldError("title", "Required"))
    elif len(title) < 5:
        errors.append(FieldError("title", "Must be at least 5 characters"))
    elif len(title) > 200:
        errors.append(FieldError("title", "Must be at most 200 characters"))

    context = str(data.get("context", "")).strip()
    if not context:
        errors.append(FieldError("context", "Required"))
    elif len(context) < 10:
        errors.append(FieldError("context", "Must be at least 10 characters"))
    elif len(context) > 2000:
        errors.append(FieldError("context", "Must be at most 2000 characters"))

    decision = str(data.get("decision", "")).strip()
    if not decision:
        errors.append(FieldError("decision", "Required"))
    elif len(decision) < 10:
        errors.append(FieldError("decision", "Must be at least 10 characters"))
    elif len(decision) > 2000:
        errors.append(FieldError("decision", "Must be at most 2000 characters"))

    consequences = data.get("consequences")
    if consequences is not None:
        consequences = str(consequences).strip()
        if len(consequences) > 2000:
            errors.append(FieldError("consequences", "Must be at most 2000 characters"))

    return errors


def _validate_update(data: dict) -> list[FieldError]:
    errors: list[FieldError] = []

    if "title" in data:
        title = str(data["title"]).strip()
        if len(title) < 5:
            errors.append(FieldError("title", "Must be at least 5 characters"))
        elif len(title) > 200:
            errors.append(FieldError("title", "Must be at most 200 characters"))

    if "context" in data:
        context = str(data["context"]).strip()
        if len(context) < 10:
            errors.append(FieldError("context", "Must be at least 10 characters"))
        elif len(context) > 2000:
            errors.append(FieldError("context", "Must be at most 2000 characters"))

    if "decision" in data:
        decision = str(data["decision"]).strip()
        if len(decision) < 10:
            errors.append(FieldError("decision", "Must be at least 10 characters"))
        elif len(decision) > 2000:
            errors.append(FieldError("decision", "Must be at most 2000 characters"))

    if "consequences" in data and data["consequences"] is not None:
        consequences = str(data["consequences"]).strip()
        if len(consequences) > 2000:
            errors.append(FieldError("consequences", "Must be at most 2000 characters"))

    return errors


# ── Service ────────────────────────────────────────────────────────────────────

class DecisionsService:
    def __init__(self, repo: DecisionsRepository) -> None:
        self._repo = repo

    def list_decisions(self) -> list[Decision]:
        decisions = self._repo.get_all()
        logger.info("Listed %d decisions", len(decisions))
        return decisions

    def get_decision(self, decision_id: int) -> Decision:
        decision = self._repo.get_by_id(decision_id)
        if decision is None:
            raise NotFoundError(f"Decision {decision_id} not found")
        return decision

    def create_decision(self, data: dict) -> Decision:
        errors = _validate_create(data)
        if errors:
            raise ValidationError([e.to_dict() for e in errors])

        decision = Decision(
            title=str(data["title"]).strip(),
            context=str(data["context"]).strip(),
            decision_text=str(data["decision"]).strip(),
            consequences=str(data["consequences"]).strip() if data.get("consequences") else None,
            status=DecisionStatus.PROPOSED,
        )
        saved = self._repo.create(decision)
        logger.info("Created decision id=%d title=%r", saved.id, saved.title)
        return saved

    def update_decision(self, decision_id: int, data: dict) -> Decision:
        decision = self.get_decision(decision_id)  # raises NotFoundError if missing

        errors = _validate_update(data)
        if errors:
            raise ValidationError([e.to_dict() for e in errors])

        if "title" in data:
            decision.title = str(data["title"]).strip()
        if "context" in data:
            decision.context = str(data["context"]).strip()
        if "decision" in data:
            decision.decision_text = str(data["decision"]).strip()
        if "consequences" in data:
            decision.consequences = (
                str(data["consequences"]).strip() if data["consequences"] else None
            )

        updated = self._repo.update(decision)
        logger.info("Updated decision id=%d", decision_id)
        return updated

    def transition_decision(self, decision_id: int, new_status_str: str) -> Decision:
        decision = self.get_decision(decision_id)

        # Validate the status string is a known value
        try:
            new_status = DecisionStatus(new_status_str)
        except ValueError:
            valid = [s.value for s in DecisionStatus]
            raise ValidationError([{
                "field": "status",
                "message": f"'{new_status_str}' is not a valid status. Choose from: {valid}",
            }])

        # InvalidTransitionError raised by Decision.transition() if move is illegal
        decision.transition(new_status)

        updated = self._repo.update(decision)
        logger.info(
            "Transitioned decision id=%d to status=%r",
            decision_id,
            new_status_str,
        )
        return updated

    def delete_decision(self, decision_id: int) -> None:
        decision = self.get_decision(decision_id)  # ensures it exists first
        self._repo.delete(decision.id)
        logger.info("Deleted decision id=%d", decision_id)
