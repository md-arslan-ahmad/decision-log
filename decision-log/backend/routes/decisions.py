"""
HTTP route handlers for /api/decisions.

Responsibilities:
  - Parse HTTP-level concerns (content-type, JSON body presence)
  - Delegate all logic to DecisionsService
  - Translate typed exceptions into structured JSON error responses
  - Return consistent response envelopes: {"data": ...} or {"error": ..., "code": ...}

Does NOT contain business logic or database access.
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request, current_app

from models.decision import InvalidTransitionError
from repositories.decisions_repository import DecisionsRepository
from services.decisions_service import DecisionsService, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

decisions_bp = Blueprint("decisions", __name__, url_prefix="/api/decisions")


def _get_service() -> DecisionsService:
    """Build the service with its dependency (simple manual dependency injection)."""
    return DecisionsService(repo=DecisionsRepository())


def _require_json():
    """Return an error response tuple if the request is not JSON, else None."""
    if not request.is_json:
        return (
            jsonify({"error": "Content-Type must be application/json", "code": "BAD_CONTENT_TYPE"}),
            415,
        )
    return None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@decisions_bp.get("/")
def list_decisions():
    service = _get_service()
    decisions = service.list_decisions()
    return jsonify({
        "data": [d.to_dict() for d in decisions],
        "meta": {"count": len(decisions)},
    })


@decisions_bp.post("/")
def create_decision():
    err = _require_json()
    if err:
        return err

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be valid JSON", "code": "BAD_JSON"}), 400

    service = _get_service()
    try:
        decision = service.create_decision(body)
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "code": "VALIDATION_ERROR", "details": exc.errors}), 422
    except Exception:
        current_app.logger.exception("Unexpected error creating decision")
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500

    return jsonify({"data": decision.to_dict()}), 201


@decisions_bp.get("/<int:decision_id>")
def get_decision(decision_id: int):
    service = _get_service()
    try:
        decision = service.get_decision(decision_id)
    except NotFoundError as exc:
        return jsonify({"error": str(exc), "code": "NOT_FOUND"}), 404

    return jsonify({"data": decision.to_dict()})


@decisions_bp.patch("/<int:decision_id>")
def update_decision(decision_id: int):
    err = _require_json()
    if err:
        return err

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be valid JSON", "code": "BAD_JSON"}), 400

    service = _get_service()
    try:
        decision = service.update_decision(decision_id, body)
    except NotFoundError as exc:
        return jsonify({"error": str(exc), "code": "NOT_FOUND"}), 404
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "code": "VALIDATION_ERROR", "details": exc.errors}), 422
    except Exception:
        current_app.logger.exception("Unexpected error updating decision id=%d", decision_id)
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500

    return jsonify({"data": decision.to_dict()})


@decisions_bp.post("/<int:decision_id>/transition")
def transition_decision(decision_id: int):
    err = _require_json()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    new_status = body.get("status")
    if not new_status:
        return jsonify({"error": "'status' field is required", "code": "MISSING_FIELD"}), 400

    service = _get_service()
    try:
        decision = service.transition_decision(decision_id, new_status)
    except NotFoundError as exc:
        return jsonify({"error": str(exc), "code": "NOT_FOUND"}), 404
    except (InvalidTransitionError, ValidationError) as exc:
        msg = str(exc) if isinstance(exc, InvalidTransitionError) else "Validation failed"
        return jsonify({"error": msg, "code": "INVALID_TRANSITION"}), 422
    except Exception:
        current_app.logger.exception("Unexpected error transitioning decision id=%d", decision_id)
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500

    return jsonify({"data": decision.to_dict()})


@decisions_bp.delete("/<int:decision_id>")
def delete_decision(decision_id: int):
    service = _get_service()
    try:
        service.delete_decision(decision_id)
    except NotFoundError as exc:
        return jsonify({"error": str(exc), "code": "NOT_FOUND"}), 404

    return "", 204
