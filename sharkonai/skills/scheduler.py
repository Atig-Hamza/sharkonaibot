"""
Skill: Scheduler
Create, list, cancel, and trigger scheduled / recurring tasks.
Tasks are executed autonomously in the background and results delivered via Telegram.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.system_commands import ToolResult
from logger import log


# ── Lazy engine access ────────────────────────────────────────────────────────

def _engine():
    from scheduler_engine import get_scheduler_engine
    e = get_scheduler_engine()
    if e is None:
        raise RuntimeError("Scheduler engine not initialized.")
    return e


# ── Tool implementations ──────────────────────────────────────────────────────

async def schedule_task(description: str, schedule: str, label: str = "") -> ToolResult:
    """
    Schedule a task to run automatically.

    Schedule formats:
      • "2025-06-01 14:30"        — one-shot at exact date/time
      • "every 30 minutes"        — repeating every 30 minutes
      • "every 2 hours"           — repeating every 2 hours
      • "every 1 day"             — repeating every day
      • "every day at 09:00"      — daily at 9 AM
      • "every monday at 09:00"   — weekly on Mondays at 9 AM
      • "cron: 0 9 * * 1-5"       — cron expression (Mon-Fri at 9 AM)
    """
    if not label:
        label = description[:40].strip()

    try:
        task = await _engine().add_task(label, description, schedule)
        msg = (
            f"Task scheduled!\n"
            f"  ID: #{task['id']}\n"
            f"  Label: {task['label']}\n"
            f"  Schedule: {task['schedule_type']} ({schedule})\n"
            f"  Next run: {task['next_run']}\n"
            f"  Task: {task['description']}"
        )
        return ToolResult(success=True, stdout=msg, stderr="", return_code=0)
    except ValueError as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Scheduler error: {e}", return_code=1)


async def list_scheduled_tasks() -> ToolResult:
    """List all active scheduled tasks with their next run times."""
    try:
        tasks = await _engine().list_tasks()
        if not tasks:
            return ToolResult(success=True, stdout="No scheduled tasks.", stderr="", return_code=0)

        from datetime import datetime
        lines = [f"Scheduled tasks ({len(tasks)} active):\n"]
        for t in tasks:
            next_run = datetime.fromtimestamp(t["next_run"]).strftime("%Y-%m-%d %H:%M:%S")
            last_run = (
                datetime.fromtimestamp(t["last_run"]).strftime("%Y-%m-%d %H:%M:%S")
                if t["last_run"] else "never"
            )
            lines.append(
                f"  #{t['id']} [{t['schedule_type']}] {t['label']!r}\n"
                f"    Task: {t['description'][:80]}\n"
                f"    Next: {next_run}  |  Last: {last_run}  |  Runs: {t['run_count']}\n"
            )
        return ToolResult(success=True, stdout="\n".join(lines), stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Error: {e}", return_code=1)


async def cancel_scheduled_task(task_id: str) -> ToolResult:
    """
    Cancel (disable) a scheduled task by its ID number or label.
    The task is kept in history but will no longer fire.
    """
    try:
        ok = await _engine().cancel_task(str(task_id))
        if ok:
            return ToolResult(success=True, stdout=f"Task {task_id!r} cancelled.", stderr="", return_code=0)
        return ToolResult(success=False, stdout="", stderr=f"No enabled task found with ID/label: {task_id}", return_code=1)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Error: {e}", return_code=1)


async def run_task_now(task_id: str) -> ToolResult:
    """
    Immediately trigger a scheduled task by its ID or label,
    without waiting for its next scheduled time.
    """
    try:
        ok = await _engine().run_now(str(task_id))
        if ok:
            return ToolResult(
                success=True,
                stdout=f"Task {task_id!r} triggered immediately. Result will be sent to Telegram.",
                stderr="", return_code=0,
            )
        return ToolResult(success=False, stdout="", stderr=f"No enabled task found: {task_id}", return_code=1)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Error: {e}", return_code=1)


# ── Skill Registration ────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
    {
        "name": "schedule_task",
        "description": (
            "Create a scheduled / recurring task that runs automatically in the background. "
            "The task description is executed as if you typed it yourself — you can schedule "
            "any action: 'take a screenshot', 'check disk space', 'search for news', etc. "
            "Results are delivered to Telegram automatically. "
            "Use this when the user wants something done at a specific time or on a recurring basis."
        ),
        "parameters": {
            "description": {
                "type": "string",
                "description": "What to do when the task fires. Written as a natural-language command.",
            },
            "schedule": {
                "type": "string",
                "description": (
                    "When to run it. Examples: '2025-06-01 14:30', 'every 30 minutes', "
                    "'every 2 hours', 'every day at 09:00', 'every monday at 09:00', "
                    "'cron: 0 9 * * 1-5'."
                ),
            },
            "label": {
                "type": "string",
                "description": "Short name for the task (optional, auto-generated from description if omitted).",
            },
        },
    },
    {
        "name": "list_scheduled_tasks",
        "description": "List all active scheduled tasks with their next run times, run counts, and descriptions.",
        "parameters": {},
    },
    {
        "name": "cancel_scheduled_task",
        "description": "Cancel (disable) a scheduled task. Pass the task ID number or its label.",
        "parameters": {
            "task_id": {
                "type": "string",
                "description": "The task ID (number) or label string to cancel.",
            },
        },
    },
    {
        "name": "run_task_now",
        "description": "Immediately fire a scheduled task by ID or label, without waiting for its next scheduled time.",
        "parameters": {
            "task_id": {
                "type": "string",
                "description": "The task ID (number) or label string to run immediately.",
            },
        },
    },
]

SKILL_MAP = {
    "schedule_task": schedule_task,
    "list_scheduled_tasks": list_scheduled_tasks,
    "cancel_scheduled_task": cancel_scheduled_task,
    "run_task_now": run_task_now,
}
