from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.api_v1.api import api_router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(api_router, prefix=settings.API_V1_STR)

import os

from fastapi.staticfiles import StaticFiles  # noqa: E402

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to CoAgent Studio API"}


from app.core.room_monitor import room_monitor  # noqa: E402


@app.on_event("startup")
async def startup_event() -> None:
    await room_monitor.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await room_monitor.stop()
