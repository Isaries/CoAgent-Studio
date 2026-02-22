# CoAgent Studio

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Stack](https://img.shields.io/badge/stack-Vue3%20%2B%20FastAPI-brightgreen)
![Database](https://img.shields.io/badge/db-PostgreSQL%2016-blue)

**CoAgent Studio** is a full-stack, multi-agent orchestration platform for education. It lets teachers and students interact with specialized AI agents (Teacher, Student, Designer, Analytics) in real-time collaborative rooms, while administrators can design, version, and monitor agent behavior through a built-in IDE.

---

## Architecture Overview

```
Browser (Vue 3 SPA)
      │  HTTP + WebSocket
      ▼
FastAPI Backend (Python async)
  ├── PostgreSQL  — persistent data (users, courses, rooms, agents, artifacts)
  ├── Redis       — async task queue (ARQ worker for LLM jobs)
  └── LLM APIs   — OpenAI / Google Gemini (via unified LLMService)
```

### Key Architectural Concepts

| Concept | Where | Description |
|---|---|---|
| **Agent-to-Agent (A2A) Protocol** | `backend/app/core/` | Typed message bus for autonomous agent coordination |
| **WebSocket Room Broadcasting** | `backend/app/core/socket_manager.py` | Atomic per-room message delivery |
| **ARQ Task Queue** | `backend/app/worker.py` | Offloads heavy LLM inference to background workers |
| **Optimistic UI** | `frontend/src/stores/workspace.ts` | Immediate local state updates with server-side rollback |
| **Role-Based Access Control** | Router guards + `permission_service.py` | Super Admin / Admin / Teacher / TA / Student / Guest |

---

## Tech Stack

### Frontend (`/frontend`)
- **Vue 3** (Composition API + `<script setup>`) + **TypeScript**
- **Vite** (bundler) · **Pinia** (state) · **Vue Router 4** (with auth guards)
- **Tailwind CSS** + **DaisyUI** · **Vue Flow** (process diagrams) · **Tiptap** (rich-text docs)
- Native **WebSockets** with auto-reconnect + exponential backoff

### Backend (`/backend`)
- **FastAPI** (async Python 3.10+) with full **OpenAPI** docs at `/docs`
- **SQLModel** (Pydantic + SQLAlchemy 2.0 async) · **Alembic** (migrations)
- **ARQ + Redis** (background task queue) · **aiofiles** (async file I/O)
- **JWT HttpOnly Cookies** (OAuth2 password flow + refresh token)
- **OpenAI SDK** + **Google GenAI** unified behind `LLMFactory`

### Infrastructure
- **Docker Compose** (single command to run all services)
- **PostgreSQL 16** · **Redis 7-alpine**

---

## Quick Start

### Option A — Docker (Recommended)

**1. Configure environment**

Copy and edit `.env` in the project root:
```env
SECRET_KEY=change_this_to_a_long_random_string
POSTGRES_SERVER=db
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=coagent_db
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
# Optional AI keys (agents won't respond without these)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
```

**2. Launch all services**
```bash
docker compose up --build -d
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Interactive API Docs (Swagger) | http://localhost:8000/docs |

---

### Option B — Manual Development

**Run backing services only (DB + Redis):**
```bash
docker compose up db redis -d
```

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
CoAgent-Studio/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # Route handlers (users, courses, agents, chat, …)
│   │   ├── core/      # Config, DB, security, WebSocket, LLM, A2A
│   │   ├── models/    # SQLModel table definitions
│   │   ├── repositories/ # Data access layer (BaseRepo + specializations)
│   │   ├── services/  # Business logic (CourseService, AgentConfigService, …)
│   │   └── worker.py  # ARQ background worker entry point
│   ├── alembic/       # Database migration scripts
│   └── tests/         # pytest suite (97 tests)
├── frontend/          # Vue 3 SPA
│   └── src/
│       ├── api.ts         # Axios instance + interceptors
│       ├── components/    # Reusable UI components
│       ├── composables/   # Logic hooks (useWebSocket, useRoomChat, …)
│       ├── router/        # Vue Router with auth/role guards
│       ├── services/      # API call wrappers
│       ├── stores/        # Pinia stores (auth, workspace, toast)
│       ├── types/         # TypeScript type definitions
│       └── views/         # Page-level components
├── docs/
│   └── A2A_PROTOCOL.md    # Agent-to-Agent protocol specification
├── docker-compose.yml
└── .env                   # Environment variables (not committed)
```

---

## Key Features

- **Real-Time Chat Rooms** — WebSocket broadcast with A2A trace visualization
- **Agent Design IDE** — Version-controlled system prompt editor with live sandbox
- **Kanban Board + Docs + Process Diagrams** — AI-generated workspace artifacts
- **Multi-Model Support** — OpenAI GPT & Google Gemini via unified API
- **Impersonation Mode** — Admins can "view as" any user for debugging
- **Async LLM Jobs** — Heavy inference runs in background via ARQ + Redis

---

## Contributing

1. Fork the repo and create a feature branch (`git checkout -b feat/my-feature`)
2. See `backend/README.md` and `frontend/README.md` for stack-specific guidelines
3. Run backend tests: `pytest` (97 tests must pass)
4. Run frontend type check: `vue-tsc --noEmit`
5. Open a Pull Request against `main`

## License
MIT
