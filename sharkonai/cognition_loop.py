"""
SharkonAI Cognition Loop — Enhanced v2
Background autonomous cognition with system monitoring,
proactive health checks, and periodic memory maintenance.
"""

import asyncio
import platform
import shutil
from datetime import datetime

from config import CONFIG
from logger import log
from memory import Memory


class CognitionLoop:
    """
    Runs a background loop that maintains SharkonAI's internal state.
    Now includes system health monitoring, memory stats, and proactive intelligence.
    """

    def __init__(self, memory: Memory):
        self.memory = memory
        self._running = False
        self._task: asyncio.Task = None
        self._tick_count = 0

    async def start(self):
        """Start the cognition loop as a background task."""
        if self._running:
            log.warning("Cognition loop is already running.")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        log.info("Cognition loop started.")

    async def stop(self):
        """Stop the cognition loop gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Cognition loop stopped.")

    async def _loop(self):
        """Main cognition loop."""
        log.info("Cognition loop entering main cycle...")

        while self._running:
            try:
                await self._tick()
                self._tick_count += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Cognition loop error: {e}", exc_info=True)

            await asyncio.sleep(CONFIG.COGNITION_INTERVAL_SECONDS)

    async def _tick(self):
        """Single cognition tick — comprehensive system and memory health check."""
        now = datetime.utcnow().isoformat()

        # ── Core heartbeat ──
        await self.memory.set_state("last_heartbeat", now)
        await self.memory.set_state("tick_count", str(self._tick_count))

        # ── Gather stats ──
        msg_count = await self.memory.get_message_count()
        action_count = await self.memory.get_action_count()

        await self.memory.set_state("total_messages", str(msg_count))
        await self.memory.set_state("total_actions", str(action_count))

        # ── System health (every 5 ticks) ──
        if self._tick_count % 5 == 0:
            await self._check_system_health()

        # ── Log periodic status (every 10 ticks) ──
        if self._tick_count % 10 == 0:
            log.info(
                f"Cognition tick #{self._tick_count} | "
                f"Messages: {msg_count} | Actions: {action_count} | "
                f"Time: {now}"
            )

    async def _check_system_health(self):
        """Check system resources and store metrics."""
        try:
            # Disk space
            total, used, free = shutil.disk_usage("/")
            disk_pct = (used / total) * 100
            await self.memory.set_state("disk_used_pct", f"{disk_pct:.1f}")
            await self.memory.set_state("disk_free_gb", f"{free / (1024 ** 3):.1f}")

            if disk_pct > 90:
                log.warning(f"Disk usage is high: {disk_pct:.1f}% used!")

        except Exception as e:
            log.debug(f"System health check error: {e}")

        try:
            # Database file size
            import os
            db_size = os.path.getsize(CONFIG.DATABASE_PATH) if os.path.exists(CONFIG.DATABASE_PATH) else 0
            await self.memory.set_state("db_size_mb", f"{db_size / (1024 * 1024):.2f}")
        except Exception:
            pass

    @property
    def is_running(self) -> bool:
        return self._running
