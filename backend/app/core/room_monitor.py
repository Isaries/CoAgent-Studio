import asyncio

import structlog
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import engine
from app.core.socket_manager import manager
from app.services.execution.agent_execution_service import check_and_process_time_triggers

logger = structlog.get_logger()


class RoomMonitor:
    def __init__(self):
        self.is_running = False
        self.task = None
        self.arq_pool = None

    async def start(self, arq_pool=None) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.arq_pool = arq_pool
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("room_monitor_started")

    async def stop(self) -> None:
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("room_monitor_stopped")

    async def _monitor_loop(self) -> None:
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        while self.is_running:
            try:
                # Get copy of keys to avoid modification during iteration
                # (though asyncio is single threaded, better safe if structure changes)
                active_room_ids = list(manager.active_connections.keys())

                if active_room_ids:
                    for room_id in active_room_ids:
                        try:
                            async with async_session() as session:
                                await check_and_process_time_triggers(
                                    room_id, session, self.arq_pool
                                )
                        except Exception as e:
                            logger.error("room_monitor_check_failed", room_id=room_id, error=str(e))

            except Exception as e:
                logger.error("room_monitor_loop_error", error=str(e))

            await asyncio.sleep(30)  # Check every 30 seconds (reduces DB load)


room_monitor = RoomMonitor()
