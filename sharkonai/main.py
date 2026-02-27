"""
SharkonAI — Main Entry Point
Autonomous AI Agent for Telegram, powered by NVIDIA Qwen model.

Starts all subsystems:
  • Memory (SQLite) — Enhanced with knowledge base and task tracking
  • Brain (NVIDIA AI) — Enhanced with chain-of-thought and multi-step planning
  • Telegram Bot (aiogram v3) — Enhanced with tool chaining
  • Cognition Loop — Enhanced with system health monitoring
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
║                      A I   v 2 . 0                        ║
║                                                           ║
║   🧠 Enhanced Brain • ⛓️ Multi-Step Chains • 🔧 47 Tools  ║
║   🎤 Voice Recognition • 📚 Memory • 🛡️ Self-Recovery  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""


async def main():
    """Initialize and run all SharkonAI subsystems."""
    print(BANNER)
    log.info("=" * 60)
    log.info("SharkonAI v2.0 starting up...")
    log.info("=" * 60)

    # ── 1. Memory System ──
    log.info("[1/5] Initializing Enhanced Memory System...")
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
    log.info("[2/5] Initializing Enhanced AI Brain...")
    brain = Brain(memory)
    log.info(f"  Model: {CONFIG.NVIDIA_MODEL}")
    log.info(f"  Max chain steps: {CONFIG.MAX_CHAIN_STEPS}")
    log.info(f"  Max tokens: {CONFIG.MAX_TOKENS}")

    # ── 3. Cognition Loop ──
    log.info("[3/5] Starting Cognition Loop...")
    cognition = CognitionLoop(memory)
    await cognition.start()

    # ── 4. Watchdog ──
    log.info("[4/5] Starting Watchdog...")
    watchdog = Watchdog(memory, cognition)
    await watchdog.start()

    # ── 5. Telegram Bot ──
    log.info("[5/5] Starting Telegram Bot...")
    init_handler(memory, brain)
    bot, dp = create_bot_and_dispatcher()

    # Store startup state
    await memory.set_state("status", "running")
    await memory.set_state("version", "2.0")
    await memory.set_state("startup_time", __import__("datetime").datetime.utcnow().isoformat())

    log.info("=" * 60)
    log.info("🚀 SharkonAI v2.0 is ONLINE and ready!")
    log.info(f"  Authorized user: {CONFIG.AUTHORIZED_USER_ID}")
    log.info(f"  AI Model: {CONFIG.NVIDIA_MODEL}")
    log.info(f"  Database: {CONFIG.DATABASE_PATH}")
    log.info(f"  Tools available: {len(TOOL_MAP)}")
    log.info(f"  Max chain depth: {CONFIG.MAX_CHAIN_STEPS}")
    log.info("=" * 60)

    # Graceful shutdown handler
    shutdown_event = asyncio.Event()

    async def shutdown():
        log.info("Shutting down SharkonAI...")
        await memory.set_state("status", "stopping")
        await watchdog.stop()
        await cognition.stop()
        await bot.session.close()
        await memory.set_state("status", "stopped")
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
    # Fix "Event loop is closed" error on Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSharkonAI stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
