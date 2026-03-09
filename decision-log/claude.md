# Claude / AI Agent Guidance for Decision Log

This file constrains how AI tools should interact with this codebase.
Read this before generating, modifying, or reviewing any code.

---

## Project Purpose

A small REST API + React frontend for recording Architecture Decision Records (ADRs).
Keep it **small and correct**. Resist the urge to add features.

---

## Hard Rules (Never Violate)

1. **Never bypass validation** — all inputs must pass Pydantic schema validation before touching the DB.
2. **Never write raw SQL** — use SQLAlchemy ORM exclusively. No `db.execute()` with string interpolation.
3. **Never swallow exceptions silently** — every except block must log the error before re-raising or returning an error response.
4. **Never expose internal stack traces** to the client — use structured error responses (`{"error": "...", "code": "..."}`) only.
5. **Never add a feature without a test** — every new endpoint or domain rule needs at least one test in `backend/tests/`.
6. **Never mutate** a `Decision` object's `status` directly — always use the `Decision.transition(new_status)` method to enforce valid state transitions.
7. **Never use `SELECT *`** — always name columns explicitly in queries.

---

## Architecture Boundaries

```
Frontend (React)
    │  HTTP/JSON only
    ▼
Flask API (routes/)
    │  calls only
    ▼
Service layer (services/)
    │  calls only
    ▼
Repository layer (repositories/)
    │  calls only
    ▼
SQLAlchemy ORM (models/)
    │
    ▼
SQLite (decisions.db)
```

- **Routes** — validate HTTP concerns (auth headers, content-type), call services, return JSON.
- **Services** — enforce business rules (valid transitions, required fields logic), call repositories.
- **Repositories** — DB access only. No business logic.
- **Do not skip layers.** Routes must not call repositories directly.

---

## Domain Rules (Encode in Service Layer)

### Decision Statuses
Valid statuses (in order): `proposed` → `accepted` | `rejected` | `superseded`

Allowed transitions:
- `proposed` → `accepted`
- `proposed` → `rejected`
- `accepted` → `superseded`
- All others are **invalid** and must raise `InvalidTransitionError`

### Required Fields
- `title`: 5–200 characters, non-empty after strip
- `context`: 10–2000 characters
- `decision`: 10–2000 characters
- `status`: must be one of the four valid statuses
- `consequences` (optional): max 2000 characters

---

## Coding Standards

### Python / Flask
- Type-annotate all function signatures.
- Use dataclasses or Pydantic models for all data transfer objects.
- Use `flask.current_app.logger` — never bare `print()`.
- Return consistent JSON envelopes:
  - Success: `{"data": ..., "meta": {...}}`
  - Error: `{"error": "human message", "code": "MACHINE_CODE"}`
- All dates stored and returned as ISO-8601 UTC strings.

### React / Frontend
- No inline styles — use CSS modules or the existing stylesheet.
- No direct `fetch()` calls in components — use the `api.js` service module.
- Props must be validated with PropTypes.
- State must never be mutated directly.

### Tests
- Use `pytest` with the `testing` config (in-memory SQLite).
- Test files mirror source files: `backend/tests/test_decisions_service.py` tests `backend/services/decisions_service.py`.
- Each test function should test exactly one behavior.
- Forbidden in tests: `time.sleep()`, network calls, file I/O outside fixtures.

---

## What AI Should NOT Do

- Do not add authentication/authorization (out of scope, noted in README).
- Do not add a caching layer.
- Do not add WebSocket or real-time features.
- Do not change the database from SQLite without a migration strategy discussion.
- Do not refactor working code speculatively.
- Do not add dependencies without updating `requirements.txt` and noting the reason in a comment.

---

## When in Doubt

Prefer **explicit over implicit**, **simple over clever**, and **boring over novel**.
If a change touches more than 3 files, stop and ask whether it respects the layer boundaries above.
