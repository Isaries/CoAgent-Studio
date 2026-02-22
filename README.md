# CoAgent Studio

![Stack](https://img.shields.io/badge/stack-Vue3%20%2B%20FastAPI-brightgreen)
![Database](https://img.shields.io/badge/db-PostgreSQL%2016%20%7C%20Neo4j%205%20%7C%20Qdrant-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow)

**CoAgent Studio** is a full-stack, multi-agent orchestration platform for education. It lets teachers and students interact with specialized AI agents (Teacher, Student, Designer, Analytics) in real-time collaborative rooms, while administrators can design, version, and monitor agent behavior through a built-in IDE.

A **GraphRAG (Graph Retrieval-Augmented Generation)** engine powers the Analytics Agent, building persistent knowledge graphs from conversations and enabling deep cross-session reasoning.

---

## Architecture Overview

```
Browser (Vue 3 SPA)
      │  HTTP + WebSocket
      ▼
FastAPI Backend (Python async)
  ├── PostgreSQL  — persistent data (users, courses, rooms, agents, artifacts, messages)
  ├── Redis       — task queue (ARQ worker) + Redis Streams (GraphRAG event bus)
  ├── Neo4j 5     — knowledge graph (entities, relationships, community clusters)
  ├── Qdrant      — vector store (entity embeddings, chunk search, community summaries)
  └── LLM APIs   — OpenAI / Google Gemini (via unified LLMService)
```

### Key Architectural Concepts

| Concept | Where | Description |
|---|---|---|
| **GraphRAG Engine** | `backend/app/services/graphrag_service.py` | Extracts entity graphs from conversations, runs Leiden clustering, embeds summaries for Analytics Agent |
| **Incremental Ingestion** | `backend/app/services/graphrag_consumer.py` | Redis Stream consumer with per-room debounce triggers extraction on new messages |
| **Agent-to-Agent (A2A) Protocol** | `backend/app/core/` | Typed message bus for autonomous agent coordination |
| **WebSocket Room Broadcasting** | `backend/app/core/socket_manager.py` | Atomic per-room real-time message delivery |
| **ARQ Task Queue** | `backend/app/worker.py` | Offloads LLM inference and graph builds to background workers |
| **Optimistic UI** | `frontend/src/stores/workspace.ts` | Immediate local state updates with server-side rollback |
| **Role-Based Access Control** | Router guards + `permission_service.py` | Super Admin / Admin / Teacher / TA / Student / Guest |

---

## Tech Stack

### Frontend (`/frontend`)
- **Vue 3** (Composition API + `<script setup>`) + **TypeScript**
- **Vite** (bundler) · **Pinia** (state) · **Vue Router 4** (with auth guards)
- **Tailwind CSS** + **DaisyUI** · **Vue Flow** (process diagrams) · **Tiptap** (rich-text docs)
- **Canvas-based** force-directed knowledge graph visualization
- Native **WebSockets** with auto-reconnect + exponential backoff

### Backend (`/backend`)
- **FastAPI** (async Python 3.10+) with full **OpenAPI** docs at `/docs`
- **SQLModel** (Pydantic + SQLAlchemy 2.0 async) · **Alembic** (migrations)
- **ARQ + Redis** (background task queue) · **Redis Streams** (event bus)
- **JWT HttpOnly Cookies** (OAuth2 password flow + refresh token)
- **OpenAI SDK** + **Google GenAI** unified behind `LLMFactory`
- **`instructor`** (structured LLM output) · **`tiktoken`** (token-aware chunking)

### Infrastructure
- **Docker Compose** (single command to run all services)
- **PostgreSQL 16** · **Redis 7-alpine** · **Neo4j 5 Community** (APOC + GDS) · **Qdrant**

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

# AI keys (required for agents and GraphRAG)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# GraphRAG services (auto-configured in Docker)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=coagent_neo4j
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

**2. Launch all services**
```bash
docker compose up --build -d
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

### Option B — Manual Development

**Run backing services:**
```bash
docker compose up db redis neo4j qdrant -d
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

**ARQ Worker (required for agents + GraphRAG):**
```bash
python -m arq app.worker.WorkerSettings
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
│   │   ├── api/       # Route handlers (users, courses, agents, chat, graph, …)
│   │   ├── core/
│   │   │   ├── neo4j_client.py    # Async Neo4j: entity MERGE, Leiden clustering, APOC traversal
│   │   │   ├── qdrant_client.py   # Vector store: entity/chunk/community embeddings
│   │   │   ├── embedding_service.py  # OpenAI text-embedding-3-small wrapper
│   │   │   ├── llm_service.py     # LLMFactory + unified async LLM client
│   │   │   └── a2a/               # Agent-to-Agent protocol
│   │   ├── models/    # SQLModel table definitions + GraphRAG Pydantic schemas
│   │   ├── repositories/ # Data access layer
│   │   ├── services/
│   │   │   ├── graphrag_service.py   # GraphRAG ARQ tasks (extract, cluster, summarize)
│   │   │   ├── graphrag_consumer.py  # Redis Stream consumer (incremental ingestion)
│   │   │   ├── graph_search_service.py # Intent routing → Global/Local search
│   │   │   ├── chat_service.py    # Message persistence + GraphRAG event publishing
│   │   │   └── artifact_service.py   # Artifact CRUD + GraphRAG event publishing
│   │   └── worker.py  # ARQ worker + GraphRAG consumer lifecycle
│   ├── alembic/       # Database migration scripts
│   └── tests/         # pytest suite
├── frontend/          # Vue 3 SPA
│   └── src/
│       ├── components/
│       │   └── room/
│       │       ├── RoomGraphView.vue    # Canvas force-directed knowledge graph
│       │       ├── GraphQueryPanel.vue  # Analytics Agent Q&A + community browser
│       │       └── …
│       ├── services/graphService.ts     # GraphRAG API wrapper
│       ├── types/graph.ts               # GraphRAG type definitions
│       └── views/RoomView.vue           # Room tabs: Chat | Board | Docs | Process | 🧠 Knowledge Graph
├── docs/
│   └── A2A_PROTOCOL.md    # Agent-to-Agent protocol specification
├── docker-compose.yml
└── .env
```

---

## Key Features

### Collaborative Learning
- **Real-Time Chat Rooms** — WebSocket broadcast with A2A trace visualization
- **Agent Design IDE** — Version-controlled system prompt editor with live sandbox
- **Kanban Board + Docs + Process Diagrams** — AI-generated workspace artifacts
- **Multi-Model Support** — OpenAI GPT & Google Gemini via unified API

### 🧠 Analytics Agent (GraphRAG)
- **Knowledge Graph** — Entities (people, concepts, technologies, artifacts) extracted from conversations
- **Leiden Community Detection** — Thematic clusters via Neo4j GDS
- **Dual Search Strategy** — Global search (community summaries) for macro questions, Local search (APOC multi-hop traversal + Qdrant chunks) for specific entities
- **Incremental Ingestion** — Redis Stream consumer automatically updates the graph within ~10 seconds of new messages
- **Interactive Visualization** — Canvas force-directed graph with type filtering, search, and relationship inspection

### Security & Operations
- **Impersonation Mode** — Admins can "view as" any user for debugging
- **RBAC** — Per-room and per-resource permission checks on every graph API
- **Async LLM Jobs** — Heavy inference runs in background via ARQ + Redis

---

## License

> ⚠️ **License not yet specified.** Please consult the project owner before use, redistribution, or contribution.
