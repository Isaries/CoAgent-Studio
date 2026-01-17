import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.api_v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.socket_manager import manager

# Setup Logging
setup_logging(json_logs=False)  # Set True in Prod via env var ideally, keeping simple for now
logger = structlog.get_logger()

# Lifespan Events
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("startup_event")

    try:
        # 1. Connect SocketManager to Redis (for Pub/Sub)
        await manager.connect_redis(settings.redis_url)

        # 2. Init ARQ Pool (for enqueueing jobs)
        app.state.arq_pool = await create_pool(
            RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        )

        # 3. Init Cache
        from app.core.cache import cache

        await cache.connect()

        # 4. Start Room Monitor
        from app.core.room_monitor import room_monitor

        await room_monitor.start(arq_pool=app.state.arq_pool)
    except Exception as e:
        logger.critical(f"Startup Failed: Could not initialize Redis/ARQ dependencies. {e}")
        raise RuntimeError(
            "Critical Dependency Failure: Redis or ARQ Pool could not be initialized."
        ) from e

    yield

    # Shutdown
    logger.info("shutdown_event")
    await room_monitor.stop()
    await app.state.arq_pool.close()
    await cache.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

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
