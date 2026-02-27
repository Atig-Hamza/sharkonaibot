"""
SharkonAI Watchdog
Monitors system health and automatically recovers from failures.
"""

import asyncio
import signal
import sys
from datetime import datetime, timedelta

from config import CONFIG
from logger import log
from memory import Memory
from cognition_loop import CognitionLoop


class Watchdog:
    """
    Monitors SharkonAI components and restarts them if they fail.
    Ensures 24/7 continuous operation.
    """

    def __init__(self, memory: Memory, cognition: CognitionLoop):
        self.memory = memory
        self.cognition = cognition
        self._running = False
        self._task: asyncio.Task = None
        self._restart_count = 0

    async def start(self):
        """Start the watchdog monitor."""
        self._running = True
        self._task = asyncio.create_task(self._monitor())
        log.info("Watchdog started — monitoring system health.")

    async def stop(self):
        """Stop the watchdog."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Watchdog stopped.")

    async def _monitor(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Watchdog monitoring error: {e}", exc_info=True)

            await asyncio.sleep(CONFIG.WATCHDOG_CHECK_INTERVAL)

    async def _check_health(self):
        """Check health of all components."""

        # Check cognition loop
        if not self.cognition.is_running:
            log.warning("Cognition loop is not running! Attempting restart...")
            if self._restart_count < CONFIG.MAX_RESTART_ATTEMPTS:
                try:
                    await self.cognition.start()
                    self._restart_count += 1
                    log.info(f"Cognition loop restarted (attempt {self._restart_count})")
                    await self.memory.store_action(
                        action_type="watchdog_restart",
                        parameters={"component": "cognition_loop"},
                        result="Restarted successfully",
                        success=True,
                    )
                except Exception as e:
                    log.error(f"Failed to restart cognition loop: {e}")
            else:
                log.critical(
                    f"Cognition loop restart limit reached ({CONFIG.MAX_RESTART_ATTEMPTS}). "
                    "Manual intervention required."
                )

        # Check heartbeat freshness
        last_hb = await self.memory.get_state("last_heartbeat")
        if last_hb:
            try:
                hb_time = datetime.fromisoformat(last_hb)
                age = datetime.utcnow() - hb_time
                max_age = timedelta(seconds=CONFIG.COGNITION_INTERVAL_SECONDS * 3)
                if age > max_age:
                    log.warning(
                        f"Heartbeat is stale ({age.total_seconds():.0f}s old). "
                        "System may be unresponsive."
                    )
            except ValueError:
                pass

        # Update watchdog state
        await self.memory.set_state("watchdog_last_check", datetime.utcnow().isoformat())
        await self.memory.set_state("watchdog_restart_count", str(self._restart_count))

    @property
    def is_running(self) -> bool:
        return self._running
