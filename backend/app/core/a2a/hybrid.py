"""
A2A Hybrid Dispatcher.

Provides a unified interface that can operate in either:
- LOCAL mode: In-memory routing (original A2ADispatcher)
- DISTRIBUTED mode: Redis Streams routing (DistributedDispatcher)

This allows seamless switching between modes without changing application code.
"""

import structlog
from enum import Enum
from typing import Optional

from .dispatcher import A2ADispatcher
from .distributed import DistributedDispatcher, DistributedDispatcherConfig
from .models import A2AMessage

logger = structlog.get_logger()


class DispatchMode(str, Enum):
    """Dispatch mode for hybrid dispatcher."""
    LOCAL = "local"
    DISTRIBUTED = "distributed"
    AUTO = "auto"  # Distributed if Redis available, else local


class HybridDispatcher:
    """
    Unified dispatcher interface supporting both local and distributed modes.
    
    This is the recommended entry point for A2A messaging, as it provides:
    - Transparent fallback from distributed to local
    - Consistent API regardless of deployment mode
    - Easy migration path from local to distributed
    
    Example:
        # Development (local mode)
        dispatcher = HybridDispatcher(mode=DispatchMode.LOCAL)
        
        # Production (distributed mode)
        dispatcher = HybridDispatcher(
            mode=DispatchMode.DISTRIBUTED,
            redis_url="redis://localhost:6379",
        )
        await dispatcher.connect()
        
        # Auto mode (tries distributed, falls back to local)
        dispatcher = HybridDispatcher(
            mode=DispatchMode.AUTO,
            redis_url="redis://localhost:6379",
        )
        await dispatcher.connect()
        
        # Usage is the same regardless of mode
        dispatcher.register("teacher", teacher_handler)
        await dispatcher.dispatch(message)
    """
    
    def __init__(
        self,
        mode: DispatchMode = DispatchMode.AUTO,
        redis_url: str = "redis://localhost:6379",
        config: Optional[DistributedDispatcherConfig] = None,
    ):
        self._mode = mode
        self._redis_url = redis_url
        self._config = config or DistributedDispatcherConfig()
        
        self._local: Optional[A2ADispatcher] = None
        self._distributed: Optional[DistributedDispatcher] = None
        self._active_mode: Optional[DispatchMode] = None
    
    @property
    def mode(self) -> Optional[DispatchMode]:
        """Get the active dispatch mode after connection."""
        return self._active_mode
    
    @property
    def is_distributed(self) -> bool:
        """Check if currently running in distributed mode."""
        return self._active_mode == DispatchMode.DISTRIBUTED
    
    async def connect(self) -> None:
        """
        Connect and initialize the appropriate dispatcher.
        
        For LOCAL mode: Initializes in-memory dispatcher
        For DISTRIBUTED mode: Connects to Redis
        For AUTO mode: Tries Redis, falls back to local
        """
        if self._mode == DispatchMode.LOCAL:
            self._local = A2ADispatcher()
            self._active_mode = DispatchMode.LOCAL
            logger.info("hybrid_dispatcher_connected", mode="local")
            
        elif self._mode == DispatchMode.DISTRIBUTED:
            self._distributed = DistributedDispatcher(
                redis_url=self._redis_url,
                config=self._config,
            )
            await self._distributed.connect()
            self._active_mode = DispatchMode.DISTRIBUTED
            logger.info("hybrid_dispatcher_connected", mode="distributed")
            
        else:  # AUTO
            try:
                self._distributed = DistributedDispatcher(
                    redis_url=self._redis_url,
                    config=self._config,
                )
                await self._distributed.connect()
                self._active_mode = DispatchMode.DISTRIBUTED
                logger.info("hybrid_dispatcher_connected", mode="distributed_auto")
            except Exception as e:
                logger.warning(
                    "distributed_connection_failed_falling_back",
                    error=str(e),
                )
                self._distributed = None
                self._local = A2ADispatcher()
                self._active_mode = DispatchMode.LOCAL
                logger.info("hybrid_dispatcher_connected", mode="local_fallback")
    
    async def disconnect(self) -> None:
        """Disconnect from Redis if in distributed mode."""
        if self._distributed:
            await self._distributed.disconnect()
            self._distributed = None
        self._local = None
        self._active_mode = None
        logger.info("hybrid_dispatcher_disconnected")
    
    def register(self, agent_id: str, handler) -> None:
        """Register an agent handler."""
        if self._local:
            self._local.register(agent_id, handler)
        if self._distributed:
            self._distributed.register(agent_id, handler)
    
    def unregister(self, agent_id: str) -> None:
        """Unregister an agent handler."""
        if self._local:
            self._local.unregister(agent_id)
        if self._distributed:
            self._distributed.unregister(agent_id)
    
    async def dispatch(
        self,
        msg: A2AMessage,
        wait_response: bool = False,
    ) -> Optional[A2AMessage]:
        """
        Dispatch a message using the active mode.
        
        Args:
            msg: The A2AMessage to dispatch
            wait_response: If True and in distributed mode, wait for response
            
        Returns:
            Response message from handler (local) or response stream (distributed)
        """
        if self._active_mode == DispatchMode.LOCAL and self._local:
            return await self._local.dispatch(msg)
        
        elif self._active_mode == DispatchMode.DISTRIBUTED and self._distributed:
            return await self._distributed.dispatch(msg, wait_response=wait_response)
        
        else:
            raise RuntimeError("Dispatcher not connected")
    
    async def start_consuming(self, agent_id: str) -> None:
        """
        Start consuming messages for an agent (distributed mode only).
        
        In local mode, this is a no-op since messages are processed synchronously.
        """
        if self._active_mode == DispatchMode.DISTRIBUTED and self._distributed:
            await self._distributed.start_consuming(agent_id)
        else:
            logger.info(
                "start_consuming_skipped",
                reason="local mode - messages handled synchronously",
                agent_id=agent_id,
            )
    
    def stop(self) -> None:
        """Stop consuming (distributed mode only)."""
        if self._distributed:
            self._distributed.stop()
    
    # === Delegation methods for advanced use ===
    
    @property
    def local_dispatcher(self) -> Optional[A2ADispatcher]:
        """Access underlying local dispatcher if available."""
        return self._local
    
    @property
    def distributed_dispatcher(self) -> Optional[DistributedDispatcher]:
        """Access underlying distributed dispatcher if available."""
        return self._distributed
    
    def add_middleware(self, fn) -> None:
        """Add middleware (local mode only)."""
        if self._local:
            self._local.add_middleware(fn)
        else:
            logger.warning("middleware_not_supported_in_distributed_mode")
    
    def set_broadcast_handler(self, handler) -> None:
        """Set broadcast handler (local mode only)."""
        if self._local:
            self._local.set_broadcast_handler(handler)


# === Factory Functions ===

async def create_hybrid_dispatcher(
    mode: DispatchMode = DispatchMode.AUTO,
    redis_url: str = "redis://localhost:6379",
    **config_kwargs,
) -> HybridDispatcher:
    """
    Create and connect a hybrid dispatcher.
    
    Usage:
        # Auto mode (recommended for most cases)
        dispatcher = await create_hybrid_dispatcher()
        
        # Force local mode
        dispatcher = await create_hybrid_dispatcher(mode=DispatchMode.LOCAL)
        
        # Force distributed mode
        dispatcher = await create_hybrid_dispatcher(
            mode=DispatchMode.DISTRIBUTED,
            redis_url="redis://production-redis:6379",
        )
    """
    config = DistributedDispatcherConfig(**config_kwargs) if config_kwargs else None
    dispatcher = HybridDispatcher(
        mode=mode,
        redis_url=redis_url,
        config=config,
    )
    await dispatcher.connect()
    return dispatcher
