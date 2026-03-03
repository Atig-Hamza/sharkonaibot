"""
Skill: Clipboard
Read/write system clipboard.
"""

from logger import log
from skills.system_commands import ToolResult


SKILL_DEFINITIONS = [
    {
        "name": "get_clipboard",
        "description": "Read the current contents of the system clipboard.",
        "parameters": {},
    },
    {
        "name": "set_clipboard",
        "description": "Set the system clipboard to the given text.",
        "parameters": {
            "text": {"type": "string", "description": "The text to copy to the clipboard."},
        },
    },
]


async def get_clipboard() -> ToolResult:
    try:
        import pyperclip
        content = pyperclip.paste()
        return ToolResult(success=True, stdout=content or "(clipboard is empty)", stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def set_clipboard(text: str) -> ToolResult:
    try:
        import pyperclip
        pyperclip.copy(text)
        return ToolResult(success=True, stdout=f"Copied {len(text)} characters to clipboard.", stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


SKILL_MAP = {
    "get_clipboard": get_clipboard,
    "set_clipboard": set_clipboard,
}
