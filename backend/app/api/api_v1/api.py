from fastapi import APIRouter

from app.api.api_v1.endpoints import (
    agent_config_crud,
    agents,
    agent_types,
    a2a_webhook,
    analytics,
    announcements,
    artifacts,
    chat,
    courses,
    login,
    rooms,
    users,
    user_keys,
    organizations,
    projects,
    threads,
    admin_db,
)

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
# New: User Keys
api_router.include_router(user_keys.router, prefix="/users/keys", tags=["user-keys"])

api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(threads.router, prefix="/threads", tags=["threads"])

api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(agent_config_crud.router, prefix="/agent-config", tags=["agent-config"])
api_router.include_router(agent_types.router, tags=["agent-types"])
api_router.include_router(a2a_webhook.router, tags=["a2a-webhook"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(admin_db.router, prefix="/admin/db", tags=["admin_db"])

# New: Artifact/Workspace endpoints
api_router.include_router(artifacts.router, prefix="/workspaces", tags=["workspaces"])



