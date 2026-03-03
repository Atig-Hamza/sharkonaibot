"""
Skill: System Commands
Execute CMD, PowerShell, and Python code on the host machine.
"""

import asyncio
import os

from config import CONFIG
from logger import log

# Import shared ToolResult from the parent tools module
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dataclasses import dataclass
from typing import Optional


@dataclass
class ToolResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    image_path: str = ""
    file_path: str = ""


# ── Definitions ─────────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
    {
        "name": "execute_cmd",
        "description": (
            "Execute any CMD / PowerShell / terminal command on the host machine. "
            "Use this to run system commands like ipconfig, systeminfo, dir, "
            "python scripts, start applications, manage files, install packages, etc. "
            "Returns stdout, stderr, and success status. "
            "For complex commands, prefer PowerShell syntax on Windows."
        ),
        "parameters": {
            "command": {
                "type": "string",
                "description": "The command to execute in the system shell.",
            }
        },
    },
    {
        "name": "execute_powershell",
        "description": (
            "Execute a PowerShell command or script directly. More powerful than CMD. "
            "Use this for advanced Windows operations: file management, registry, "
            "network configuration, system administration, WMI queries, etc."
        ),
        "parameters": {
            "script": {
                "type": "string",
                "description": "The PowerShell script/command to execute.",
            }
        },
    },
    {
        "name": "run_python",
        "description": (
            "Execute Python code in a subprocess and return the output. "
            "Use this for calculations, data processing, file manipulation, "
            "web scraping, or any task that benefits from Python. "
            "The code runs in a fresh Python process."
        ),
        "parameters": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            }
        },
    },
]


# ── Implementations ─────────────────────────────────────────────────────────

async def execute_cmd(command: str) -> ToolResult:
    """Execute a system command asynchronously and capture output."""
    log.info(f"Executing command: {command}")
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=CONFIG.CMD_TIMEOUT,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            log.warning(f"Command timed out after {CONFIG.CMD_TIMEOUT}s: {command}")
            return ToolResult(
                success=False, stdout="",
                stderr=f"Command timed out after {CONFIG.CMD_TIMEOUT} seconds.",
                return_code=-1,
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        success = process.returncode == 0

        max_len = 8000
        if len(stdout) > max_len:
            stdout = stdout[:max_len] + "\n... [output truncated]"
        if len(stderr) > max_len:
            stderr = stderr[:max_len] + "\n... [output truncated]"

        log.info(f"Command result: success={success}, rc={process.returncode}")
        return ToolResult(success=success, stdout=stdout, stderr=stderr, return_code=process.returncode)

    except Exception as e:
        log.error(f"Command execution error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=-1)


async def execute_powershell(script: str) -> ToolResult:
    """Execute a PowerShell script/command."""
    log.info(f"Executing PowerShell: {script[:100]}...")
    command = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "{script}"'
    return await execute_cmd(command)


async def run_python(code: str) -> ToolResult:
    """Execute Python code in a subprocess."""
    log.info(f"Running Python code: {code[:80]}...")
    try:
        temp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_temp_script.py")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(code)
        result = await execute_cmd(f'python "{temp_path}"')
        try:
            os.remove(temp_path)
        except OSError:
            pass
        return result
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=-1)


# ── Skill Map ───────────────────────────────────────────────────────────────

SKILL_MAP = {
    "execute_cmd": execute_cmd,
    "execute_powershell": execute_powershell,
    "run_python": run_python,
}
