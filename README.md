# CoAgent Studio

CoAgent Studio is a comprehensive platform designed for the creation, management, and real-time interaction with specialized AI agents. It features a robust multi-user collaboration environment where users interacts with agents in designated "Rooms".

## System Architecture

The project follows a modern client-server architecture with real-time capabilities.

### Backend (Python/FastAPI)
The backend is built with FastAPI, prioritizing performance and asynchronous capabilities.
*   **API Layer**: RESTful endpoints exposed via `app/api/v1` handling authentication, user management, and resource CRUD operations.
*   **Real-time Layer**: A dedicated WebSocket manager (`ConnectionManager`) handles persistent connections. It maintains a mapping of `room_id` to active socket connections, enabling atomic broadcasting of messages to all participants in a room.
*   **Data Access**: Uses SQLModel (combining Pydantic and SQLAlchemy) for type-safe database interactions with PostgreSQL.
*   **Database Migrations**: Alembic is used for version control of the database schema.

### Frontend (Vue 3/TypeScript)
The frontend is a Single Page Application (SPA) built with Vite and Vue 3.
*   **State Management**: Pinia is used for centralized store management (Auth, Rooms).
*   **Networking**: An Axios wrapper manages HTTP requests with automatic token refresh logic (Interceptors). Native WebSocket API is used for real-time features.
*   **UI Framework**: TailwindCSS allows for utility-first styling.

## Codebase Structure

### Backend (`/backend`)
*   `app/main.py`: Application entry point and CORS configuration.
*   `app/api/v1/`: API route definitions grouped by domain (users, login, rooms, etc.).
*   `app/core/`: Core infrastructure code.
    *   `config.py`: Environment configuration and validation.
    *   `security.py`: JWT token generation and password hashing utilities.
    *   `socket_manager.py`: WebSocket connection handling and broadcasting logic.
*   `app/models/`: SQLModel classes defining database schema and Pydantic validation.
*   `app/services/`: Business logic layer separating complex operations from API routes.
*   `alembic/`: Database migration scripts.

### Frontend (`/frontend`)
*   `src/api.ts`: Centralized Axios instance with interceptors for auth handling.
*   `src/stores/`: Pinia stores for global state.
    *   `auth.ts`: Authentication state (user profile, token logic).
*   `src/services/`: API service layer mapping backend endpoints to typed functions.
*   `src/views/`: Main page components (e.g., Login, Dashboard, Room).
*   `src/components/`: Reusable UI components.


## Security Overview

The application implements defense-in-depth strategies to secure user data and session integrity.

### Authentication & Session Management
*   **Token Storage**: JSON Web Tokens (JWT) are strictly stored in HttpOnly, Secure, SameSite=Lax cookies. This effectively mitigates Cross-Site Scripting (XSS) attacks as JavaScript cannot access the tokens.
*   **Token Lifecycle**: Access tokens are short-lived (default 8 hours). Refresh tokens are long-lived (7 days) and are used to silently acquire new access tokens without user intervention.
*   **Password Storage**: User passwords are never stored in plain text. They are hashed using `bcrypt` before persistence.

### Infrastructure Security
*   **Secret Management**: The application enforces the presence of a strong `SECRET_KEY` environment variable. It will refuse to start if this key is missing or is left as a default value.
*   **CORS Policy**: The backend implements a strict Cross-Origin Resource Sharing policy. It rejects all requests from origins not explicitly allowlisted in the `BACKEND_CORS_ORIGINS` configuration.

## Deployment Guide

### Prerequisites
*   Docker Desktop (or Docker Engine + Compose)
*   Git

### Local Development (Docker Compose)
This is the recommended method for running the application locally as it orchestrates the Database, Backend, and Frontend containers.

1.  **Configuration**:
    Create a `.env` file in the project root. You must populate `SECRET_KEY` with a strong random string.
    ```env
    SECRET_KEY=replace_with_a_secure_random_string
    BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]
    POSTGRES_USER=user
    POSTGRES_PASSWORD=password
    POSTGRES_DB=coagent_db
    ```

2.  **Execution**:
    Run the following command to build and start the services:
    ```bash
    docker compose up --build
    ```

3.  **Access**:
    *   Frontend: `http://localhost:5173`
    *   API Documentation (Swagger UI): `http://localhost:8000/docs`

### Production Server Deployment

1.  **Environment Setup**:
    On your production server, clone the repository and navigate to the project directory.

2.  **Production Configuration**:
    Create a production-grade `.env` file.
    *   Set `SECRET_KEY` to a high-entropy string (e.g., generated via `openssl rand -hex 32`).
    *   Set `BACKEND_CORS_ORIGINS` to your actual domain (e.g., `["https://studio.example.com"]`).
    *   Ensure database credentials are strong.

3.  **Run Services**:
    Start the application in detached mode:
    ```bash
    docker compose -f docker-compose.yml up -d --build
    ```

4.  **Reverse Proxy Configuration**:
    It is standard practice to place a reverse proxy (like Nginx or Traefik) in front of the application.
    *   Proxy requests to `localhost:5173` for the frontend.
    *   Proxy requests to `localhost:8000` for the backend.
    *   **Important**: Ensure WebSocket headers (`Upgrade` and `Connection`) are properly forwarded by the proxy.

## Troubleshooting

### 403 Forbidden Errors
If you encounter 403 Forbidden errors immediately after deployment or config changes, it is likely due to Token Invalidation.
*   **Cause**: Changing the `SECRET_KEY` invalidates all existing JWTs signed with the old key.
*   **Solution**: Clear your browser cookies for the site or Logout and Login again.

### Container Connection Issues
If the backend cannot connect to the database:
*   Ensure the `db` service in `docker-compose.yml` is healthy.
*   Check that the `POSTGRES_SERVER` env var in the backend matches the service name `db`.
