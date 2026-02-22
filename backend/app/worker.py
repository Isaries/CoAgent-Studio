from typing import Any, ClassVar

import structlog
from arq.connections import RedisSettings
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.db import engine
from app.services.execution.agent_execution_service import run_agent_cycle_task, run_agent_time_task
from app.services.graphrag_service import (
    build_communities_task,
    extract_entities_task,
    full_graph_rebuild_task,
)

logger = structlog.get_logger()


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("worker_startup")
    ctx["session_factory"] = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # GraphRAG: Initialize Neo4j + Qdrant clients
    from app.core.neo4j_client import neo4j_client
    from app.core.qdrant_client import vector_store

    try:
        await neo4j_client.connect()
        await vector_store.connect()
        logger.info("worker_graphrag_ready")
    except Exception as e:
        logger.warning("worker_graphrag_init_failed", error=str(e))

    # Start the Redis Stream consumer for incremental ingestion
    from app.services.graphrag_consumer import graphrag_consumer
    try:
        await graphrag_consumer.start(ctx)
    except Exception as e:
        logger.warning("worker_graphrag_consumer_failed", error=str(e))

    # Provide an embedding API key to tasks via context
    import os
    ctx["embedding_api_key"] = os.getenv("OPENAI_API_KEY", "")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker_shutdown")

    from app.core.neo4j_client import neo4j_client
    from app.core.qdrant_client import vector_store
    from app.services.graphrag_consumer import graphrag_consumer

    await graphrag_consumer.stop()
    await neo4j_client.close()
    await vector_store.close()
    await engine.dispose()


class WorkerSettings:
    functions: ClassVar[list] = [
        run_agent_cycle_task,
        run_agent_time_task,
        # GraphRAG tasks
        extract_entities_task,
        build_communities_task,
        full_graph_rebuild_task,
    ]
    redis_settings = RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    on_startup = startup
    on_shutdown = shutdown
    handle_signals = False
  # Let Docker/Supervisor handle this
