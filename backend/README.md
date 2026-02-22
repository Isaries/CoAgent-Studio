# CoAgent Studio — Backend

FastAPI-based backend powering multi-agent orchestration, real-time WebSockets, async LLM processing, and a GraphRAG knowledge graph engine.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (async Python 3.10+) |
| ORM | SQLModel (SQLAlchemy 2.0 async + Pydantic) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Task Queue | ARQ + Redis |
| Event Bus | Redis Streams (`graphrag:events`) |
| Graph DB | Neo4j 5 Community (APOC + GDS plugins) |
| Vector DB | Qdrant |
| Embeddings | OpenAI `text-embedding-3-small` via `EmbeddingService` |
| LLM I/O | OpenAI SDK + Google GenAI via `LLMFactory`; `instructor` for structured output |
| Chunking | `tiktoken` for token-aware message splitting |
| Auth | JWT HttpOnly Cookies (OAuth2 + refresh) |
| Testing | pytest + pytest-asyncio |

---

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py                   # Auth + role dependencies (Depends)
│   │   └── api_v1/
│   │       └── endpoints/
│   │           ├── chat.py           # Chat history + WebSocket handler
│   │           ├── graph.py          # GraphRAG API (build, query, visualize, communities, status)
│   │           ├── agents.py         # Agent config + sandbox
│   │           ├── courses.py / rooms.py / users.py / …
│   ├── core/
│   │   ├── config.py                 # Pydantic Settings (incl. Neo4j, Qdrant, GraphRAG params)
│   │   ├── db.py                     # Async engine + get_session / get_session_context
│   │   ├── security.py               # JWT creation + Fernet encryption
│   │   ├── socket_manager.py         # WebSocket room broadcaster
│   │   ├── llm_service.py            # LLMFactory + unified async LLM client
│   │   ├── neo4j_client.py           # Async Neo4j: entity MERGE (case-normalized), Leiden GDS, APOC multi-hop
│   │   ├── qdrant_client.py          # Qdrant vector store: 3 collections, semantic search, room deletion
│   │   ├── embedding_service.py      # OpenAI text-embedding-3-small batch wrapper
│   │   └── a2a/                      # Agent-to-Agent protocol implementation
│   ├── models/
│   │   ├── graph_schemas.py          # GraphRAG Pydantic models (EntityNode, CommunityReport, QueryIntent, …)
│   │   └── …                        # SQLModel table definitions
│   ├── repositories/
│   │   └── base_repo.py              # Generic CRUD base (no jsonable_encoder, async-safe)
│   ├── services/
│   │   ├── graphrag_service.py       # ARQ tasks: extract_entities, build_communities, full_graph_rebuild
│   │   ├── graphrag_consumer.py      # Redis Stream consumer — incremental ingestion with per-room debounce
│   │   ├── graph_search_service.py   # Intent router → Global search (community summaries) | Local search (Neo4j + Qdrant)
│   │   ├── chat_service.py           # Message persistence + GraphRAG event publisher
│   │   ├── artifact_service.py       # Artifact CRUD + GraphRAG event publisher
│   │   ├── permission_service.py     # Centralized RBAC checks
│   │   └── …
│   ├── initial_data.py               # DB seeding on startup (creates super admin)
│   ├── main.py                       # App entry point, lifespan, Neo4j/Qdrant lifecycle
│   └── worker.py                     # ARQ worker + GraphRAG consumer startup/shutdown
├── alembic/                          # Migration scripts
├── tests/                            # pytest suite
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── pyproject.toml                    # ruff + mypy config
```

---

## Local Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 16 + Redis + Neo4j 5 + Qdrant (or run via Docker)

### Steps

**1. Start backing services**
```bash
docker compose up db redis neo4j qdrant -d   # from project root
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

# AI
OPENAI_API_KEY=sk-...

# GraphRAG
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=coagent_neo4j
QDRANT_HOST=localhost
QDRANT_PORT=6333
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

**6. Start the ARQ worker (required for agents + GraphRAG)**
```bash
python -m arq app.worker.WorkerSettings
```

The worker starts the **GraphRAG Redis Stream consumer** automatically on startup. It listens on `graphrag:events` and triggers incremental entity extraction within ~10 seconds of new chat messages or artifact changes.

---

## Key Concepts

### GraphRAG Engine

The Analytics Agent is powered by a Graph RAG pipeline:

```
New message/artifact
    │
    ▼  (Redis Stream publish)
graphrag:events
    │
    ▼  (GraphRAGConsumer — 10s debounce per room)
extract_entities_task
    ├── LLM (gpt-4o-mini + instructor) → EntityNode, EntityRelationship
    ├── Neo4j MERGE (case-normalized names, display_name preserved)
    └── Qdrant upsert (entity descriptions + message chunks)
    │
    ▼  (full rebuild only)
build_communities_task
    ├── Neo4j GDS Leiden clustering → community_id per entity
    ├── LLM → CommunityReport (title, summary, key findings)
    └── Qdrant upsert (community summaries)
    │
    ▼  (query time)
graph_search_service.query_graph()
    ├── intent = "global" → Qdrant community search → LLM answer
    └── intent = "local"  → Neo4j APOC multi-hop → Qdrant chunk evidence → LLM answer
```

**Entity name normalization**: All Neo4j entity names are stored as `toLower(name)` for consistent merging; the original casing is preserved in `display_name` for display purposes.

**Idempotent rebuilds**: `full_graph_rebuild_task` wipes the room's Neo4j nodes + all 3 Qdrant collections before re-extracting, preventing data accumulation.

### `get_session` vs `get_session_context`
- **`get_session`** — FastAPI `Depends()` generator. Use for regular HTTP endpoints.
- **`get_session_context`** — Async context manager. For WebSocket handlers and background tasks (prevents pool exhaustion).

### Permission System
All resource access goes through `permission_service.check(user, action, resource, session)`. Graph API endpoints additionally call `_verify_room_access()` to confirm the requesting user belongs to the room.

### BaseRepository `update()`
Uses `obj_in.model_dump(exclude_unset=True)` — no `jsonable_encoder` — to avoid `MissingGreenlet` errors in async SQLAlchemy.

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
# Run all tests
pytest

# Verbose output
pytest -v

# Specific file
pytest tests/services/test_artifact_service.py
```

Tests use a real PostgreSQL test database with transaction rollback isolation.

---

## Code Quality

```bash
ruff check app/           # Linting
ruff format app/          # Formatting
mypy app/                 # Type checking
```

---

## License

> ⚠️ **License not yet specified.** Please consult the project owner before use, redistribution, or contribution.
