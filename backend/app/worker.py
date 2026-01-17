from typing import Any, ClassVar

import structlog
from arq.connections import RedisSettings
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.db import engine
from app.services.execution.agent_execution_service import run_agent_cycle_task, run_agent_time_task

logger = structlog.get_logger()


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("worker_startup")
    # Initialize DB Engine (shared) if needed, or just let SQLAlchemy handle pool
    # We might want to construct a sessionmaker here and put it in ctx
    ctx["session_factory"] = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker_shutdown")
    await engine.dispose()


class WorkerSettings:
    functions: ClassVar[list] = [run_agent_cycle_task, run_agent_time_task]
    redis_settings = RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    on_startup = startup
    on_shutdown = shutdown
    handle_signals = False  # Let Docker/Supervisor handle this
