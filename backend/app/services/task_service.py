import structlog
from typing import Any, Optional

logger = structlog.get_logger()

class TaskService:
    """
    Abstractions for Task Queue (ARQ) operations.
    Decouples endpoints from ARQ specifics.
    """

    def __init__(self, arq_pool: Any):
        self.arq_pool = arq_pool

    async def enqueue_agent_cycle(self, room_id: str, message_id: str) -> bool:
        """
        Trigger the agent cycle background task.
        """
        if not self.arq_pool:
            logger.error("task_enqueue_failed", reason="pool_not_initialized")
            return False
            
        try:
            await self.arq_pool.enqueue_job("run_agent_cycle_task", room_id, message_id)
            return True
        except Exception as e:
            logger.error("task_enqueue_failed", error=str(e))
            return False
