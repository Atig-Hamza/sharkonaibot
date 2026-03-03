"""
SharkonAI Configuration
All settings and credentials for the autonomous AI agent.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Central configuration for SharkonAI."""

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = "TELEGRAM_BOT_TOKEN_HERE"
    AUTHORIZED_USER_ID: int = 0

    # NVIDIA AI Endpoint
    NVIDIA_API_KEY: str = "nvapi-API_KEY_HERE"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "moonshotai/kimi-k2-instruct-0905"

    # Database
    DATABASE_PATH: str = os.path.join(os.path.dirname(__file__), "database.db")

    # Cognition Loop
    COGNITION_INTERVAL_SECONDS: int = 60  # How often the cognition loop ticks
    MAX_CONTEXT_MESSAGES: int = 50  # Increased for richer context

    # Watchdog
    WATCHDOG_CHECK_INTERVAL: int = 30  # seconds
    MAX_RESTART_ATTEMPTS: int = 5

    # Logging
    LOG_FILE: str = os.path.join(os.path.dirname(__file__), "sharkonai.log")
    LOG_LEVEL: str = "INFO"

    # Tool Execution
    CMD_TIMEOUT: int = 180  # seconds timeout for command execution (increased)
    TOOL_TIMEOUT: int = 120

    # Brain - Enhanced Reasoning
    MAX_CHAIN_STEPS: int = 25        # Max auto-continuation steps for multi-step tasks
    MAX_RETRIES: int = 3             # Retry attempts for JSON parsing failures
    CREATIVE_TEMPERATURE: float = 0.7  # For creative/conversational tasks
    PRECISE_TEMPERATURE: float = 0.2   # For tool execution / precise tasks
    MAX_TOKENS: int = 4096             # Increased for more detailed reasoning

    # Skill Evolution
    SKILL_EVOLUTION_INTERVAL: int = 30   # Every N cognition ticks, review skills
    SKILL_EVOLUTION_ENABLED: bool = True # Allow autonomous skill creation

    # Memory
    MAX_TASK_HISTORY: int = 50    # Max tasks to keep in history
    SUMMARY_INTERVAL: int = 20   # Summarize conversation every N messages

    # Voice Recognition
    # Languages to try for speech-to-text, in priority order.
    # The system tries each language until one succeeds.
    # Common codes: 'fr-FR', 'en-US', 'ar-SA', 'es-ES', 'de-DE', 'zh-CN'
    VOICE_LANGUAGES: list = None  # Will be set in __post_init__

    def __post_init__(self):
        if self.VOICE_LANGUAGES is None:
            self.VOICE_LANGUAGES = ["fr-FR", "en-US", "ar-SA"]

    # Media / File Storage — all generated files go here, not in the project root
    MEDIA_DIR: str = os.path.join(os.path.dirname(__file__), "media")
    DOWNLOADS_DIR: str = os.path.join(os.path.dirname(__file__), "media", "downloads")


CONFIG = Config()

# Ensure media directories exist at import time
os.makedirs(CONFIG.MEDIA_DIR, exist_ok=True)
os.makedirs(CONFIG.DOWNLOADS_DIR, exist_ok=True)
