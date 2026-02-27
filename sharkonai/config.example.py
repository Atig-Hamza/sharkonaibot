"""
SharkonAI Configuration — EXAMPLE
Copy this file to config.py and fill in your credentials.

    cp config.example.py config.py
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Central configuration for SharkonAI."""

    # ── Telegram Bot ────────────────────────────────────────────────────────
    # Get your bot token from @BotFather on Telegram: https://t.me/BotFather
    TELEGRAM_BOT_TOKEN: str = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

    # Your personal Telegram user ID (the bot will ONLY respond to this ID)
    # To find your ID, message @userinfobot on Telegram
    AUTHORIZED_USER_ID: int = 0

    # ── NVIDIA AI Endpoint ──────────────────────────────────────────────────
    # Get your API key from: https://build.nvidia.com/
    NVIDIA_API_KEY: str = "nvapi-YOUR_NVIDIA_API_KEY_HERE"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "moonshotai/kimi-k2-instruct-0905"

    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_PATH: str = os.path.join(os.path.dirname(__file__), "database.db")

    # ── Cognition Loop ──────────────────────────────────────────────────────
    COGNITION_INTERVAL_SECONDS: int = 60  # How often the cognition loop ticks
    MAX_CONTEXT_MESSAGES: int = 50        # Messages included in AI context window

    # ── Watchdog ────────────────────────────────────────────────────────────
    WATCHDOG_CHECK_INTERVAL: int = 30  # seconds between health checks
    MAX_RESTART_ATTEMPTS: int = 5      # max auto-restarts before giving up

    # ── Logging ─────────────────────────────────────────────────────────────
    LOG_FILE: str = os.path.join(os.path.dirname(__file__), "sharkonai.log")
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # ── Tool Execution ──────────────────────────────────────────────────────
    CMD_TIMEOUT: int = 180  # seconds timeout for command execution

    # ── Brain — Reasoning Parameters ────────────────────────────────────────
    MAX_CHAIN_STEPS: int = 10         # Max auto-continuation steps for multi-step tasks
    MAX_RETRIES: int = 3              # Retry attempts for JSON parsing failures
    CREATIVE_TEMPERATURE: float = 0.7 # For creative / conversational tasks
    PRECISE_TEMPERATURE: float = 0.2  # For tool execution / precise tasks
    MAX_TOKENS: int = 4096            # Max response token length

    # ── Memory ──────────────────────────────────────────────────────────────
    MAX_TASK_HISTORY: int = 50   # Max tasks to keep in history
    SUMMARY_INTERVAL: int = 20  # Summarize conversation every N messages

    # ── Media / File Storage ────────────────────────────────────────────────
    # All generated files go here, not in the project root
    MEDIA_DIR: str = os.path.join(os.path.dirname(__file__), "media")
    DOWNLOADS_DIR: str = os.path.join(os.path.dirname(__file__), "media", "downloads")


CONFIG = Config()

# Ensure media directories exist at import time
os.makedirs(CONFIG.MEDIA_DIR, exist_ok=True)
os.makedirs(CONFIG.DOWNLOADS_DIR, exist_ok=True)
