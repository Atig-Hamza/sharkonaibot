"""
SharkonAI Tools - Skills-Based Architecture
Thin orchestration layer that delegates to the modular skills/ system.

The skills/ folder contains all tool implementations organized by category.
The AI can create new skills at runtime via the skill_developer meta-skill.

See skills/__init__.py for the skill loader and skills/skill_developer.py
for the self-evolution engine.
"""

import asyncio
import os
import sys

# Ensure the sharkonai package is on the path for skills to import from each other
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataclasses import dataclass
from typing import Optional

from logger import log


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    stdout: str
    stderr: str = ""
    return_code: int = 0
    image_path: str = ""  # If set, the telegram handler will send this as a photo
    file_path: str = ""   # If set, the telegram handler will send this as a document


# -- Skills System Integration ------------------------------------------------
# Import everything from the skills module - this auto-loads all skill files

from skills import (
    TOOL_DEFINITIONS,
    TOOL_MAP,
    get_tools_prompt,
    set_memory_ref,
    load_all_skills,
    load_single_skill,
    get_loaded_skills,
)

# Re-export transcribe_audio for the telegram handler (voice message support)
from skills.audio_transcription import transcribe_audio


def _coerce_tool_result(raw) -> ToolResult:
    """Ensure the return value is a proper ToolResult (AI skills sometimes return dicts)."""
    if isinstance(raw, ToolResult):
        return raw
    if isinstance(raw, dict):
        return ToolResult(
            success=raw.get("success", False),
            stdout=str(raw.get("stdout", "")),
            stderr=str(raw.get("stderr", "")),
            return_code=int(raw.get("return_code", 1 if not raw.get("success") else 0)),
            image_path=str(raw.get("image_path", "")),
            file_path=str(raw.get("file_path", "")),
        )
    # Fallback — treat any other return as stdout text
    return ToolResult(success=True, stdout=str(raw))


async def dispatch_tool(action: str, parameters: dict) -> ToolResult:
    """Dispatch a tool call by name with the given parameters."""
    if action not in TOOL_MAP:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Unknown tool: {action}. Available: {list(TOOL_MAP.keys())}",
            return_code=1,
        )

    func = TOOL_MAP[action]
    try:
        # Filter out None-valued params (AI sometimes sends null for optional args)
        clean_params = {k: v for k, v in parameters.items() if v is not None}
        # Execute with timeout to prevent runaway tools from freezing the bot
        from config import CONFIG
        result = await asyncio.wait_for(
            func(**clean_params),
            timeout=CONFIG.TOOL_TIMEOUT,
        )
        return _coerce_tool_result(result)
    except asyncio.TimeoutError:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Tool '{action}' timed out after {CONFIG.TOOL_TIMEOUT} seconds. "
                   "The operation took too long. Try a simpler/smaller request.",
            return_code=1,
        )
    except TypeError as e:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Invalid parameters for {action}: {e}",
            return_code=1,
        )
    except Exception as e:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Tool execution error: {e}",
            return_code=1,
        )
