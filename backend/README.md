# CoAgent Studio Backend

This directory contains the server-side application for CoAgent Studio, built with **FastAPI**. It powers the multi-agent orchestration platform with RESTful APIs, real-time WebSockets, and asynchronous background processing.

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Database**: PostgreSQL 16
- **ORM**: [SQLModel](https://sqlmodel.tiangolo.com/) (Pydantic + SQLAlchemy)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Real-time**: Native WebSockets with Atomic Broadcasting
- **Async Tasks**: [ARQ](https://arq-docs.helpmanual.io/) + Redis
- **Security**: OAuth2 with Password Flow (JWT HttpOnly Cookies)
- **AI Integration**: OpenAI SDK, Google GenAI

## Project Structure

```bash
backend/
├── alembic/                # Database migration scripts
├── app/
│   ├── api/v1/             # API Router (Users, Login, Rooms, Agents)
│   ├── core/               # Config, Security, WebSocket Manager
│   ├── models/             # SQLModel Database Tables
│   ├── services/           # Business Logic (AgentRunner, ChatService)
│   └── main.py             # App Entrypoint
├── tests/                  # Pytest Suite
├── Dockerfile              # Production Docker Image
├── requirements.txt        # Python Dependencies
└── alembic.ini             # Migration Config
```

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL
- Redis

### Local Setup (Manual)

1. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Create a `.env` file in this directory (or root) with the following:
   ```env
   SECRET_KEY=dev_secret_key_change_me
   POSTGRES_SERVER=localhost
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=password
   POSTGRES_DB=coagent_db
   BACKEND_CORS_ORIGINS=["http://localhost:5173"]
   ```

4. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Start Dev Server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   Access API Docs at: http://localhost:8000/docs

### Docker Setup (Recommended)

Run from the project root:
```bash
docker compose up --build
```

## Key Components

### 🔄 Real-Time WebSocket Manager
Located in `app/core/socket_manager.py`. It handles:
- Connection lifecycle (Connect/Disconnect).
- Room-based broadcasting.
- Atomic message delivery to ensuring strict ordering.

### 🧠 Agent Runner Service
Located in `app/services/agent_service.py`. It handles:
- **Prompt Construction**: Merging system prompts with conversation history.
- **Model Invocation**: Calling OpenAI/Gemini APIs.
- **Tool Execution**: Parsing model output to execute defined tools (if any).

### 🔒 Security
- **Authentication**: `app/api/v1/endpoints/login.py` issues HttpOnly JWTs.
- **Dependency Injection**: `app/api/deps.py` provides `get_current_user` dependencies for route protection.

## Database Migrations (Alembic)

To create a new migration after modifying models in `app/models`:
```bash
alembic revision --autogenerate -m "Description of change"
```

To apply migrations:
```bash
alembic upgrade head
```

## Testing

Run the test suite with pytest:
```bash
pytest
```
Configuration is in `pytest.ini`.

## License
MIT
