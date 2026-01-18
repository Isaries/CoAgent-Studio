from fastapi import APIRouter

from app.api.api_v1.endpoints import (
    agent_config_crud,
    agents,
    analytics,
    announcements,
    chat,
    courses,
    login,
    rooms,
    users,
    admin_db,
)

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(agent_config_crud.router, prefix="/agent-config", tags=["agent-config"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(admin_db.router, prefix="/admin/db", tags=["admin_db"])
# will add users, courses, etc.
