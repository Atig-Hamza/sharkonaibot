"""
SharkonAI Scheduler Engine
Background cron-like task runner.

Supports:
  • One-shot tasks:     "2025-06-01 09:00"
  • Interval tasks:     "every 30 minutes" / "every 2 hours" / "every 1 day"
  • Daily tasks:        "every day at 09:00"
  • Weekly tasks:       "every monday at 09:00"
  • Cron expressions:   "cron: 0 9 * * 1"
"""

import asyncio
import json
import re
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional

from config import CONFIG
from logger import log

# ── Markdown stripper ─────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Remove common Markdown so messages arrive as clean plain text."""
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)          # **bold**
    text = re.sub(r'__(.+?)__', r'\1', text)               # __bold__
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'\1', text)  # *italic*
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)    # _italic_
    text = re.sub(r'~~(.+?)~~', r'\1', text)               # ~~strike~~
    text = re.sub(r'`([^`]+)`', r'\1', text)               # `code`
    text = re.sub(r'```[\s\S]*?```', lambda m: m.group(0).strip('`').strip(), text)  # ```block```
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # ## headings
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)   # [link](url) → link
    return text.strip()

# ── Days of week ──────────────────────────────────────────────────────────────

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}


# ── Schedule parser ───────────────────────────────────────────────────────────

def parse_schedule(schedule_str: str) -> tuple[str, str, float]:
    """
    Parse a human-readable schedule string.
    Returns (schedule_type, schedule_value, next_run_timestamp).

    Supported formats:
      "2025-06-01 09:00"              → once
      "every 30 minutes"              → interval  (value = seconds as str)
      "every 2 hours"                 → interval
      "every 1 day" / "every day"     → interval
      "every day at 09:00"            → daily     (value = "HH:MM")
      "every monday at 09:00"         → weekly    (value = "0 09:00")
      "cron: 0 9 * * 1"               → cron      (value = "0 9 * * 1")
    """
    s = schedule_str.strip().lower()

    # ── One-shot: ISO datetime ───────────────────────────────────────────────
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2}(?::\d{2})?)", s)
    if m:
        dt = datetime.strptime(schedule_str.strip(), "%Y-%m-%d %H:%M" if len(m.group(2)) <= 5 else "%Y-%m-%d %H:%M:%S")
        return "once", schedule_str.strip(), dt.timestamp()

    # ── Cron expression ──────────────────────────────────────────────────────
    m = re.match(r"cron:\s*(.+)", s)
    if m:
        cron_expr = m.group(1).strip()
        nxt = _next_cron(cron_expr, datetime.now())
        return "cron", cron_expr, nxt.timestamp()

    # ── Daily at HH:MM ───────────────────────────────────────────────────────
    m = re.match(r"every\s+day\s+at\s+(\d{1,2}:\d{2})", s)
    if m:
        hhmm = m.group(1)
        nxt = _next_daily(hhmm)
        return "daily", hhmm, nxt.timestamp()

    # ── Weekly on WEEKDAY at HH:MM ───────────────────────────────────────────
    m = re.match(r"every\s+(\w+)\s+at\s+(\d{1,2}:\d{2})", s)
    if m and m.group(1) in _WEEKDAYS:
        day_idx = _WEEKDAYS[m.group(1)]
        hhmm = m.group(2)
        nxt = _next_weekly(day_idx, hhmm)
        return "weekly", f"{day_idx} {hhmm}", nxt.timestamp()

    # ── Interval: every N unit ───────────────────────────────────────────────
    m = re.match(r"every\s+(\d+)?\s*(minute|minutes|hour|hours|day|days|second|seconds)", s)
    if m:
        n = int(m.group(1)) if m.group(1) else 1
        unit = m.group(2).rstrip("s")
        multipliers = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
        seconds = n * multipliers[unit]
        return "interval", str(seconds), time.time() + seconds

    raise ValueError(
        f"Cannot parse schedule: {schedule_str!r}\n"
        "Supported: 'YYYY-MM-DD HH:MM', 'every N minutes/hours/days', "
        "'every day at HH:MM', 'every monday at HH:MM', 'cron: MIN HOUR DOM MON DOW'"
    )


def compute_next_run(schedule_type: str, schedule_value: str) -> float:
    """Given a schedule type+value, compute the next fire timestamp."""
    if schedule_type == "once":
        return 0.0  # Don't reschedule one-shot tasks

    if schedule_type == "interval":
        return time.time() + float(schedule_value)

    if schedule_type == "daily":
        return _next_daily(schedule_value).timestamp()

    if schedule_type == "weekly":
        parts = schedule_value.split(" ", 1)
        day_idx, hhmm = int(parts[0]), parts[1]
        return _next_weekly(day_idx, hhmm).timestamp()

    if schedule_type == "cron":
        return _next_cron(schedule_value, datetime.now()).timestamp()

    return 0.0


# ── Time helpers ──────────────────────────────────────────────────────────────

def _next_daily(hhmm: str) -> datetime:
    now = datetime.now()
    h, m = map(int, hhmm.split(":"))
    candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _next_weekly(day_idx: int, hhmm: str) -> datetime:
    now = datetime.now()
    h, m = map(int, hhmm.split(":"))
    days_ahead = (day_idx - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(hour=h, minute=m, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(weeks=1)
    return candidate


def _next_cron(expr: str, after: datetime) -> datetime:
    """Minimal cron evaluator. Supports * and single values for each field."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Cron must have 5 fields: {expr!r}")

    def _matches(field, val):
        if field == "*":
            return True
        try:
            return int(field) == val
        except ValueError:
            return False

    m_f, h_f, dom_f, mon_f, dow_f = parts
    # Scan forward minute-by-minute (max 1 week)
    dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(60 * 24 * 7 + 1):
        if (_matches(m_f, dt.minute) and _matches(h_f, dt.hour) and
                _matches(dom_f, dt.day) and _matches(mon_f, dt.month) and
                _matches(dow_f, dt.weekday())):
            return dt
        dt += timedelta(minutes=1)
    raise ValueError(f"Could not find next run for cron: {expr!r}")


# ── Scheduler Engine ──────────────────────────────────────────────────────────

class SchedulerEngine:
    """Persistent background task scheduler with Telegram delivery."""

    CHECK_INTERVAL = 30  # seconds between schedule checks

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._brain = None
        self._bot = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def set_brain(self, brain):
        self._brain = brain

    def set_bot(self, bot):
        self._bot = bot

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _conn(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    async def init_db(self):
        """Create the scheduled_tasks table if it doesn't exist."""
        def _create():
            with self._conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scheduled_tasks (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        label       TEXT NOT NULL,
                        description TEXT NOT NULL,
                        schedule_type  TEXT NOT NULL,
                        schedule_value TEXT NOT NULL,
                        next_run    REAL NOT NULL,
                        last_run    REAL DEFAULT 0,
                        run_count   INTEGER DEFAULT 0,
                        enabled     INTEGER DEFAULT 1,
                        created_at  REAL NOT NULL
                    )
                """)
                conn.commit()
        await asyncio.get_event_loop().run_in_executor(None, _create)
        log.info("Scheduler DB table ready.")

    # ── Public API (called by skill) ──────────────────────────────────────────

    async def add_task(self, label: str, description: str, schedule_str: str) -> dict:
        """Parse schedule and persist a new task. Returns the created task dict."""
        schedule_type, schedule_value, next_run = parse_schedule(schedule_str)

        def _insert():
            with self._conn() as conn:
                cur = conn.execute(
                    """INSERT INTO scheduled_tasks
                       (label, description, schedule_type, schedule_value, next_run, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (label, description, schedule_type, schedule_value, next_run, time.time()),
                )
                conn.commit()
                task_id = cur.lastrowid
            return task_id

        task_id = await asyncio.get_event_loop().run_in_executor(None, _insert)
        next_dt = datetime.fromtimestamp(next_run).strftime("%Y-%m-%d %H:%M:%S")
        log.info(f"Scheduled task #{task_id} '{label}' ({schedule_type}) — next run: {next_dt}")
        return {"id": task_id, "label": label, "schedule_type": schedule_type,
                "next_run": next_dt, "description": description}

    async def list_tasks(self) -> list[dict]:
        """Return all enabled scheduled tasks."""
        def _fetch():
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM scheduled_tasks WHERE enabled=1 ORDER BY next_run ASC"
                ).fetchall()
            return [dict(r) for r in rows]
        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def cancel_task(self, identifier: str) -> bool:
        """Disable a task by ID or label."""
        def _cancel():
            with self._conn() as conn:
                if identifier.isdigit():
                    n = conn.execute(
                        "UPDATE scheduled_tasks SET enabled=0 WHERE id=?", (int(identifier),)
                    ).rowcount
                else:
                    n = conn.execute(
                        "UPDATE scheduled_tasks SET enabled=0 WHERE label=?", (identifier,)
                    ).rowcount
                conn.commit()
            return n > 0
        return await asyncio.get_event_loop().run_in_executor(None, _cancel)

    async def run_now(self, identifier: str) -> bool:
        """Immediately fire a task by ID or label."""
        def _fetch():
            with self._conn() as conn:
                if identifier.isdigit():
                    row = conn.execute(
                        "SELECT * FROM scheduled_tasks WHERE id=? AND enabled=1", (int(identifier),)
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT * FROM scheduled_tasks WHERE label=? AND enabled=1", (identifier,)
                    ).fetchone()
            return dict(row) if row else None

        task = await asyncio.get_event_loop().run_in_executor(None, _fetch)
        if not task:
            return False
        asyncio.create_task(self._fire_task(task))
        return True

    # ── Background loop ───────────────────────────────────────────────────────

    async def start(self):
        await self.init_db()
        self._running = True
        self._task = asyncio.create_task(self._main_loop())
        log.info("Scheduler engine started.")

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Scheduler engine stopped.")

    async def _main_loop(self):
        await asyncio.sleep(5)  # Wait for bot/brain to be ready
        log.info("Scheduler loop running (check interval: 30s).")
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Scheduler tick error: {e}", exc_info=True)
            await asyncio.sleep(self.CHECK_INTERVAL)

    async def _tick(self):
        """Find all tasks due now and fire them."""
        now = time.time()

        def _due_tasks():
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM scheduled_tasks WHERE enabled=1 AND next_run<=?", (now,)
                ).fetchall()
            return [dict(r) for r in rows]

        due = await asyncio.get_event_loop().run_in_executor(None, _due_tasks)
        for task in due:
            asyncio.create_task(self._fire_task(task))

    async def _fire_task(self, task: dict):
        """Execute one scheduled task and send the result to Telegram."""
        task_id = task["id"]
        label = task["label"]
        description = task["description"]
        schedule_type = task["schedule_type"]
        schedule_value = task["schedule_value"]

        # Re-check enabled flag to avoid race condition where task is cancelled
        # between _tick() fetching it and _fire_task() actually running.
        def _is_enabled():
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT enabled FROM scheduled_tasks WHERE id=?", (task_id,)
                ).fetchone()
            return row and row["enabled"] == 1

        try:
            still_enabled = await asyncio.get_running_loop().run_in_executor(None, _is_enabled)
        except Exception as e:
            log.warning(f"_is_enabled check failed for task #{task_id}: {e} — proceeding anyway")
            still_enabled = True  # fail-safe: proceed rather than silently drop

        if not still_enabled:
            log.info(f"Skipping task #{task_id} '{label}' — was cancelled before execution.")
            return

        log.info(f"Firing scheduled task #{task_id}: {label!r}")

        # Compute next_run before execution (so it's ready even if brain crashes)
        next_run = compute_next_run(schedule_type, schedule_value)

        def _update_running():
            with self._conn() as conn:
                # Use CASE to respect any cancellation that raced between _is_enabled
                # and now: if enabled was set to 0 by cancel_task, keep it 0.
                conn.execute(
                    "UPDATE scheduled_tasks SET last_run=?, run_count=run_count+1, "
                    "next_run=?, enabled=CASE WHEN enabled=1 THEN ? ELSE 0 END WHERE id=?",
                    (
                        time.time(),
                        next_run,
                        0 if schedule_type == "once" else 1,  # disable one-shots after fire
                        task_id,
                    ),
                )
                conn.commit()

        await asyncio.get_event_loop().run_in_executor(None, _update_running)

        if not self._brain or not self._brain.api_healthy:
            await self._send(f"⚠️ Cannot execute — brain API is unhealthy.")
            return

        # Execute via brain (full tool-chain, up to MAX_CHAIN_STEPS)
        from tools import dispatch_tool
        chain_context = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_msg = (
            f"[SCHEDULED TASK — {now_str}]\n"
            f"Task: {description}\n\n"
            "Execute this task using tools. Rules:\n"
            "- Need news or current info? → call web_search FIRST with a good query\n"
            "- Need to run a command?     → call execute_cmd / execute_powershell\n"
            "- Need a screenshot?         → call screenshot or web_screenshot\n"
            "- Need file data?            → call read_file\n"
            "Do NOT answer from memory or training data. "
            "Use tools, get real results, then format a clear report for the user."
        )
        step = 0
        final_response = ""

        try:
            decision = await self._brain.think(task_msg, chain_context, isolated=True)

            while step < CONFIG.MAX_CHAIN_STEPS:
                action = decision.get("action", "none")
                parameters = decision.get("parameters", {})
                should_continue = decision.get("continue", False)
                final_response = decision.get("response", final_response)

                if action and action != "none":
                    step += 1
                    log.info(f"  Scheduler step {step}/{CONFIG.MAX_CHAIN_STEPS}: {action}")
                    tool_result = await dispatch_tool(action, parameters)
                    chain_context.append({
                        "step": step, "action": action,
                        "parameters": parameters,
                        "success": tool_result.success,
                        "output": (tool_result.stdout or tool_result.stderr)[:400],
                    })
                    # Always send tool result back for a formatted summary
                    result_msg = (
                        f"Tool '{action}' result (step {step}):\n"
                        f"Success: {tool_result.success}\n"
                        f"Output:\n{(tool_result.stdout or tool_result.stderr)[:1400]}\n\n"
                        "Format a clear report of these results for the user. "
                        "If the task needs more steps, set continue=true and call the next tool. "
                        "If done, set action=none and continue=false."
                    )
                    decision = await self._brain.think(result_msg, chain_context, isolated=True)
                else:
                    # action=none → task complete (brain answered directly or after tools)
                    break

            # Deliver the result — strip heavy prefix, keep it readable
            if final_response:
                await self._send(f"⏰ [{label}]\n\n{final_response}")
            else:
                await self._send(f"⏰ [{label}] completed ({step} steps).")

        except Exception as e:
            log.error(f"Scheduled task #{task_id} execution error: {e}", exc_info=True)
            await self._send(f"❌ Scheduled task '{label}' failed: {e}")

    async def _send(self, text: str):
        """Send a plain-text message to the authorized Telegram user."""
        if not self._bot:
            log.warning(f"Scheduler: no bot set, cannot send: {text[:80]}")
            return
        try:
            text = _strip_markdown(text)
            if len(text) > 4096:
                text = text[:4090] + "..."
            await self._bot.send_message(CONFIG.AUTHORIZED_USER_ID, text)
        except Exception as e:
            log.error(f"Scheduler send error: {e}")


# ── Module-level singleton (injected at startup) ──────────────────────────────

_engine: Optional[SchedulerEngine] = None


def set_scheduler_engine(engine: SchedulerEngine):
    global _engine
    _engine = engine


def get_scheduler_engine() -> Optional[SchedulerEngine]:
    return _engine
