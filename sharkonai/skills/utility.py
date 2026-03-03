"""
Skill: Utility
Wait/sleep and general-purpose helpers.
"""

import asyncio

from logger import log
from skills.system_commands import ToolResult


SKILL_DEFINITIONS = [
    {
        "name": "wait",
        "description": "Wait/sleep for a specified number of seconds before continuing.",
        "parameters": {
            "seconds": {"type": "number", "description": "How many seconds to wait."},
        },
    },
]


async def wait(seconds: float) -> ToolResult:
    log.info(f"Waiting {seconds}s...")
    seconds = min(seconds, 60)
    await asyncio.sleep(seconds)
    return ToolResult(success=True, stdout=f"Waited {seconds} seconds.", stderr="", return_code=0)


SKILL_MAP = {
    "wait": wait,
}
