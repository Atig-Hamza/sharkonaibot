"""
SharkonAI — Main Entry Point
Autonomous AI Agent for Telegram, powered by NVIDIA Qwen model.

Starts all subsystems:
  • Memory (SQLite) — Enhanced with knowledge base, task tracking, and goal system
  • Brain (NVIDIA AI) — Enhanced with chain-of-thought and multi-step planning
  • Telegram Bot (aiogram v3) — Non-blocking with concurrent user interaction
  • Cognition Loop — System health monitoring and skill evolution
  • Autonomous Engine — Self-directed goal generation, planning, and execution
  • Watchdog — Self-recovery system
"""

import asyncio
import signal
import sys
import os

# Ensure the sharkonai package directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from logger import log
from memory import Memory
from brain import Brain
from cognition_loop import CognitionLoop
from autonomous_engine import AutonomousEngine
from watchdog import Watchdog
from telegram_handler import init_handler, create_bot_and_dispatcher
from tools import TOOL_MAP


# ── Banner ──────────────────────────────────────────────────────────────────

BANNER = r"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███████╗██╗  ██╗ █████╗ ██████╗ ██╗  ██╗ ██████╗ ███╗  ║
║   ██╔════╝██║  ██║██╔══██╗██╔══██╗██║ ██╔╝██╔═══██╗████║ ║
║   ███████╗███████║███████║██████╔╝█████╔╝ ██║   ██║██╔██║ ║
║   ╚════██║██╔══██║██╔══██║██╔══██╗██╔═██╗ ██║   ██║████║  ║
║   ███████║██║  ██║██║  ██║██║  ██║██║  ██╗╚██████╔╝╚███║  ║
║   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚══╝  ║
║                      A I   v 4 . 0                        ║
║                                                           ║
║   🧠 Autonomous Brain • ⛓️ 25-Step Chains • 🔧 56+ Tools ║
║   🌐 Web Browsing • 🧬 Self-Evolving • 📚 Memory         ║
║   🤖 Self-Directing • 🎯 Goal Engine • 💬 Non-Blocking   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""


async def main():
    """Initialize and run all SharkonAI subsystems."""
    print(BANNER)
    log.info("=" * 60)
    log.info("SharkonAI v4.0 starting up...")
    log.info("=" * 60)

    # ── 1. Memory System ──
    log.info("[1/6] Initializing Enhanced Memory System...")
    memory = Memory()
    msg_count = await memory.get_message_count()
    action_count = await memory.get_action_count()
    log.info(f"  Memory loaded: {msg_count} messages, {action_count} actions in history.")

    # Store system knowledge on first boot
    knowledge = await memory.get_knowledge(category="system_config")
    if not knowledge:
        import platform
        await memory.store_knowledge("system_config", "os", f"{platform.system()} {platform.release()}")
        await memory.store_knowledge("system_config", "python_version", platform.python_version())
        await memory.store_knowledge("system_config", "machine", platform.machine())
        await memory.store_knowledge("system_config", "hostname", platform.node())
        log.info("  Stored initial system knowledge.")

    # ── 2. Brain ──
    log.info("[2/6] Initializing Enhanced AI Brain...")
    brain = Brain(memory)
    log.info(f"  Model: {CONFIG.NVIDIA_MODEL}")
    log.info(f"  Max chain steps: {CONFIG.MAX_CHAIN_STEPS}")
    log.info(f"  Max tokens: {CONFIG.MAX_TOKENS}")

    # ── 3. Cognition Loop ──
    log.info("[3/6] Starting Cognition Loop...")
    cognition = CognitionLoop(memory)
    cognition.set_brain(brain)  # Enable autonomous skill evolution
    await cognition.start()

    # ── 4. Autonomous Engine ──
    autonomous = None
    if CONFIG.AUTONOMOUS_ENABLED:
        log.info("[4/6] Starting Autonomous Engine...")
        autonomous = AutonomousEngine(memory)
        autonomous.set_brain(brain)
        await autonomous.start()
        log.info(f"  Cycle interval: {CONFIG.AUTONOMOUS_CYCLE_SECONDS}s")
        log.info(f"  User pause: {CONFIG.AUTONOMOUS_PAUSE_AFTER_USER}s")
    else:
        log.info("[4/6] Autonomous Engine: DISABLED")

    # ── 5. Watchdog ──
    log.info("[5/6] Starting Watchdog...")
    watchdog = Watchdog(memory, cognition)
    await watchdog.start()

    # ── 6. Telegram Bot ──
    log.info("[6/6] Starting Telegram Bot...")
    init_handler(memory, brain, autonomous)
    bot, dp = create_bot_and_dispatcher()

    # Store startup state
    await memory.set_state("status", "running")
    await memory.set_state("version", "4.0")
    await memory.set_state("startup_time", __import__("datetime").datetime.utcnow().isoformat())

    log.info("=" * 60)
    log.info("🚀 SharkonAI v4.0 is ONLINE and ready!")
    log.info(f"  Authorized user: {CONFIG.AUTHORIZED_USER_ID}")
    log.info(f"  AI Model: {CONFIG.NVIDIA_MODEL}")
    log.info(f"  Database: {CONFIG.DATABASE_PATH}")
    log.info(f"  Tools available: {len(TOOL_MAP)}")
    log.info(f"  Max chain depth: {CONFIG.MAX_CHAIN_STEPS}")
    log.info(f"  Skill evolution: {'enabled' if CONFIG.SKILL_EVOLUTION_ENABLED else 'disabled'}")
    log.info(f"  Autonomous engine: {'enabled' if CONFIG.AUTONOMOUS_ENABLED else 'disabled'}")
    log.info("=" * 60)

    # Log startup activity
    await memory.log_activity("system_start", "SharkonAI v4.0 started successfully")

    # Graceful shutdown handler
    shutdown_event = asyncio.Event()

    async def shutdown():
        log.info("Shutting down SharkonAI...")
        await memory.set_state("status", "stopping")
        if autonomous:
            await autonomous.stop()
        await watchdog.stop()
        await cognition.stop()
        await bot.session.close()
        await memory.set_state("status", "stopped")
        await memory.log_activity("system_stop", "SharkonAI shut down gracefully")
        log.info("SharkonAI has shut down gracefully.")
        shutdown_event.set()

    # Handle OS signals for graceful shutdown
    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    try:
        # Start polling (this blocks until stopped)
        await dp.start_polling(bot, close_bot_session=False)
    except (KeyboardInterrupt, SystemExit):
        log.info("Received shutdown signal...")
    except Exception as e:
        log.critical(f"Fatal error in polling: {e}", exc_info=True)
    finally:
        await shutdown()


if __name__ == "__main__":
    # Suppress harmless "Event loop is closed" errors on Windows shutdown.
    # We CANNOT use WindowsSelectorEventLoopPolicy because asyncio subprocess
    # (used by execute_cmd, execute_powershell, etc.) requires ProactorEventLoop.
    if sys.platform == "win32":
        # Patch the ProactorEventLoop to silence the shutdown RuntimeError
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _original_del = _ProactorBasePipeTransport.__del__

        def _silenced_del(self, _warn=None):
            try:
                _original_del(self, _warn=_warn)
            except RuntimeError:
                pass

        _ProactorBasePipeTransport.__del__ = _silenced_del

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSharkonAI stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
