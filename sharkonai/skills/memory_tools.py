"""
Skill: Memory Tools
Store and retrieve knowledge from permanent memory.
"""

from logger import log
from skills.system_commands import ToolResult


_memory_ref = None


def SKILL_SETUP(memory):
    """Receive the memory reference from the skill manager."""
    global _memory_ref
    _memory_ref = memory


SKILL_DEFINITIONS = [
    {
        "name": "remember",
        "description": (
            "Store a fact, preference, or piece of knowledge in permanent memory. "
            "Use this to remember important information the user tells you, "
            "system configurations, or anything useful for future reference."
        ),
        "parameters": {
            "category": {"type": "string", "description": "Category (e.g., 'user_preference', 'system_config')."},
            "key": {"type": "string", "description": "Short identifier (e.g., 'favorite_editor')."},
            "value": {"type": "string", "description": "The information to remember."},
        },
    },
    {
        "name": "recall",
        "description": (
            "Search permanent memory for previously stored knowledge or facts."
        ),
        "parameters": {
            "query": {"type": "string", "description": "What to search for in memory."},
        },
    },
]


async def remember(category: str, key: str, value: str) -> ToolResult:
    if _memory_ref is None:
        return ToolResult(success=False, stdout="", stderr="Memory not initialized.", return_code=1)
    try:
        await _memory_ref.store_knowledge(category, key, value)
        return ToolResult(success=True, stdout=f"Remembered: [{category}] {key} = {value}", stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def recall(query: str) -> ToolResult:
    if _memory_ref is None:
        return ToolResult(success=False, stdout="", stderr="Memory not initialized.", return_code=1)
    try:
        results = await _memory_ref.search_knowledge(query)
        if results:
            lines = [f"[{r['category']}] {r['key']}: {r['value']} (confidence: {r['confidence']})" for r in results]
            return ToolResult(success=True, stdout="\n".join(lines), stderr="", return_code=0)
        return ToolResult(success=True, stdout="No matching knowledge found.", stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


SKILL_MAP = {
    "remember": remember,
    "recall": recall,
}
