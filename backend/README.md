# CoAgent Studio — Backend

FastAPI-based backend powering multi-agent orchestration, real-time WebSockets, and async LLM task processing.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (async Python 3.10+) |
| ORM | SQLModel (SQLAlchemy 2.0 async + Pydantic) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Task Queue | ARQ + Redis |
| File I/O | aiofiles (non-blocking) |
| Auth | JWT HttpOnly Cookies (OAuth2 + refresh) |
| LLM | OpenAI SDK + Google GenAI via `LLMFactory` |
| Testing | pytest + pytest-asyncio (97 tests) |

---

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py              # Auth + role dependencies (Depends)
│   │   └── api_v1/
│   │       └── endpoints/       # users, courses, rooms, agents, chat, login
│   ├── core/
│   │   ├── config.py            # Pydantic Settings
│   │   ├── db.py                # Async engine + get_session / get_session_context
│   │   ├── security.py          # JWT creation + Fernet encryption
│   │   ├── socket_manager.py    # WebSocket room broadcaster
│   │   ├── llm_service.py       # LLMFactory + unified async LLM client
│   │   └── a2a/                 # Agent-to-Agent protocol implementation
│   ├── models/                  # SQLModel table definitions
│   ├── repositories/
│   │   └── base_repo.py         # Generic CRUD base (no jsonable_encoder)
│   ├── services/                # Business logic layer
│   │   ├── user_service.py      # User CRUD + async avatar upload (aiofiles)
│   │   ├── agent_config_service.py  # Agent design, versions, keys
│   │   ├── course_service.py    # Course + enrollment management
│   │   ├── room_service.py      # Room + agent assignment
│   │   ├── permission_service.py    # Centralized RBAC checks
│   │   ├── chat_service.py      # Message persistence
│   │   └── thread_service.py    # Agent thread + LLM invocation
│   ├── initial_data.py          # DB seeding on startup (creates super admin)
│   ├── main.py                  # App entry point, lifespan, middleware
│   └── worker.py                # ARQ background worker (LLM inference jobs)
├── alembic/                     # Migration scripts
├── tests/                       # pytest suite
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── pytest.ini
└── pyproject.toml               # ruff + mypy config
```

---

## Local Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 16 + Redis (or run via Docker)

### Steps

**1. Start backing services**
```bash
docker compose up db redis -d   # from project root
```

**2. Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure environment**

Create `backend/.env` (or use root `.env`):
```env
SECRET_KEY=your_secret_key_min_32_chars
POSTGRES_SERVER=localhost
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=coagent_db
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
FERNET_SECRET_KEY=<base64-url-encoded-32-byte-key>
```

**4. Run migrations & seed**
```bash
alembic upgrade head
python -m app.initial_data       # Creates default super admin
```

**5. Start dev server**
```bash
uvicorn app.main:app --reload --port 8000
```
→ Swagger UI: http://localhost:8000/docs

**6. Start the ARQ worker (optional — needed for agent inference)**
```bash
python -m arq app.worker.WorkerSettings
```

---

## Key Concepts

### `get_session` vs `get_session_context`
- **`get_session`** — FastAPI `Depends()` generator. Use for regular HTTP endpoints.
- **`get_session_context`** — Async context manager. Use for WebSocket handlers and background tasks where a short-lived session per operation is needed (prevents connection pool exhaustion).

### Permission System
All resource access is routed through `permission_service.py`. Never hardcode role checks in endpoints — call `permission_service.check(user, action, resource, session)` instead.

### BaseRepository `update()`
Uses `obj_in.model_dump(exclude_unset=True)` — no `jsonable_encoder` — to avoid `MissingGreenlet` errors from lazy-loaded relationships in async SQLAlchemy.

---

## Database Migrations

After modifying any `app/models/*.py` file:
```bash
alembic revision --autogenerate -m "Description of change"
alembic upgrade head
```

---

## Testing

```bash
# Run all tests (97 total)
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/services/test_artifact_service.py
```

Tests use a real PostgreSQL test database with transaction rollback isolation — no test data pollutes production.

---

## Code Quality

```bash
ruff check app/           # Linting
ruff format app/          # Formatting
mypy app/                 # Type checking
```

## License
MIT
