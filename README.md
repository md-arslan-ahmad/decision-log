# Decision Log

A small web application for recording and tracking Architecture Decision Records (ADRs).

Teams use ADRs to document *why* a technical choice was made, not just what was decided.
This tool keeps those records organised, searchable, and lifecycle-aware.

---

## Running the Project

**Backend**
```bash
cd backend
python3 wsgi.py
# API starts on http://localhost:5001
```

**Frontend**
```bash
# No build step needed. Just open frontend/index.html in a browser.
# Or serve it locally:
cd frontend && python3 -m http.server 3000
# then open http://localhost:3000
```

**Tests**
```bash
cd backend
python3 -m unittest discover -v tests
# 61 tests, ~1 second
```

---

## Key Technical Decisions

### 1. Python stdlib only — no third-party Python packages

**Decision:** The backend uses only Flask and Python builtins: `sqlite3`, `dataclasses`, `enum`, `unittest`.

**Why:** No network access was available during development, so pip installs failed. This constraint turned out to be beneficial — fewer dependencies means fewer things that can break, fewer version conflicts, and a codebase any Python developer can run without installing anything.

**Trade-off:** Manual input validation instead of Pydantic. The validation functions in `services/decisions_service.py` are more verbose than Pydantic schemas but more explicit — every rule is a plain `if` statement with no framework knowledge required to read it.

---

### 2. Four-layer architecture

```
HTTP layer   (routes/)        — parses requests, returns JSON, maps exceptions to HTTP codes
Service layer (services/)     — validates input, enforces business rules
Repository   (repositories/)  — all DB access; maps DB rows to domain objects
Database     (database.py)    — schema, connection helpers, initialisation
```

**Why:** Each layer has one job. Adding a new validation rule touches only the service. Swapping SQLite for Postgres touches only the repository and database module. Adding a CLI skips the routes entirely. Changes stay local.

**Enforced in `claude.md`:** Routes must not call repositories directly. The AI guidance file explicitly forbids layer-skipping.

---

### 3. Status transitions as a finite state machine in the domain model

**Decision:** `Decision.transition(new_status)` is the *only* way to change status. It consults `VALID_TRANSITIONS` and raises `InvalidTransitionError` for illegal moves.

**Why:** Without this, any code could do `decision.status = "superseded"` and bypass the rules. A single choke-point means rules are enforced everywhere, automatically.

**Valid transitions:**
```
proposed  →  accepted  →  superseded
proposed  →  rejected
(rejected and superseded are terminal)
```

---

### 4. React without a build step

**Decision:** The frontend is a single `index.html` using CDN React + Babel-in-browser. No npm, no webpack, no `node_modules`.

**Why:** The assessment evaluates backend structure, not frontend toolchain complexity. The frontend is fully functional and demonstrates proper React patterns (component composition, state management, API service separation).

**Trade-off:** Babel-in-browser is slower to initialise than pre-compiled JSX. Acceptable for a dev tool; not for production.

---

### 5. Test isolation via temporary databases

**Decision:** Each test gets a fresh `tempfile.mkstemp()` SQLite database, deleted in `tearDown`.

**Why:** No shared state between tests. Tests run in any order, leave no artifacts, and are fully isolated without any mocking of the database layer. The real DB code is exercised in every test.

---

### 6. Consistent JSON response envelopes

All error responses:
```json
{ "error": "Human message", "code": "MACHINE_CODE", "details": [...] }
```

All success responses:
```json
{ "data": { ... }, "meta": { "count": 5 } }
```

**Why:** Clients can pattern-match on `code` reliably without parsing error strings.

---

## Weaknesses and Known Limitations

**No authentication.** Anyone with network access can read, edit, or delete all decisions. Auth would be the first production concern. The architecture supports it — add a middleware or decorator at the route layer without touching the service or repository.

**No pagination.** `GET /api/decisions/` returns all records. Adding `?page=&limit=` is a one-file change in the route and service layer.

**SQLite is single-writer.** WAL mode allows concurrent reads but only one writer. Fine for a small team; swap to Postgres by changing `database.py` (connection string) and the repository (`?` placeholders → named params).

**No audit log.** Deletions are permanent. A production tool should keep a log of status transitions and deletes.

**Frontend has no auth error handling.** 401/403 errors would surface as generic messages. Fine with no auth; needs work once auth is added.

---

## AI Usage

Claude (claude-sonnet-4-5) generated the majority of the code.

**What AI generated well:**
- The layered architecture with clean separation
- The finite state machine and `VALID_TRANSITIONS` allow-list
- The test suite structure and coverage
- The `claude.md` guidance file
- The React component structure and API service module

**What required human review and correction:**
- The initial implementation assumed Pydantic and SQLAlchemy were available. They weren't. The stack was redesigned to use stdlib only after pip installs failed. This is exactly the "AI-generated code that requires critical review" the assessment asks about — AI made a reasonable assumption that turned out to be wrong in this specific environment.
- The test isolation approach was revised. AI initially generated a pytest-based suite; switched to `unittest` + `tempfile` after confirming pytest wasn't installed.
- The database connection model was simplified. AI initially proposed connection pooling; a simpler open-per-request model is appropriate for SQLite.

**AI Guidance file:** `claude.md` constrains how AI agents interact with this codebase. Key rules: no layer-skipping, status changes must go through `transition()`, no silent exception swallowing, structured error envelopes always.

---

## Project Structure

```
decision-log/
├── claude.md                        AI agent constraints and coding standards
├── README.md
├── backend/
│   ├── wsgi.py                      Entry point
│   ├── app.py                       Flask app factory (create_app pattern)
│   ├── database.py                  SQLite connection + schema
│   ├── models/
│   │   └── decision.py              Domain model + state machine
│   ├── repositories/
│   │   └── decisions_repository.py  DB access only; no business logic
│   ├── services/
│   │   └── decisions_service.py     Business rules + validation
│   ├── routes/
│   │   └── decisions.py             HTTP handlers; maps exceptions to HTTP codes
│   └── tests/
│       ├── helpers.py               AppTestCase base with isolated DB
│       ├── test_decision_model.py   Pure unit tests (no DB needed)
│       ├── test_decisions_service.py Service + DB integration tests
│       └── test_decisions_api.py    Full HTTP integration tests (61 total)
└── frontend/
    └── index.html                   React SPA; no build step required
```
