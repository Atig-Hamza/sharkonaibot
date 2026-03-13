"""
SharkonAI Autonomous Engine — Self-Directed Goal System
Runs in the background, generates its own goals, plans steps,
executes them autonomously, and lets the user query status at any time.

The engine does NOT wait for user input.  It continuously:
  1. Reflects on what it knows / what it can improve
  2. Generates goals (skill gaps, optimisations, self-maintenance)
  3. Plans step-by-step execution
  4. Executes each step via the tool system
  5. Logs everything so the user can ask "what are you doing?" at any time
"""

import asyncio
import json
import traceback
from datetime import datetime
from typing import Optional

from config import CONFIG
from logger import log
from memory import Memory


class AutonomousEngine:
    """Background autonomous agent that self-directs without user input."""

    def __init__(self, memory: Memory):
        self.memory = memory
        self._brain = None
        self._running = False
        self._task: asyncio.Task = None
        self._current_goal: Optional[dict] = None
        self._current_activity: str = "Idle"
        self._pause_for_user = False  # Pause autonomous work while user is chatting
        self._user_active_until: float = 0  # timestamp
        self._cycle_count = 0

    def set_brain(self, brain):
        self._brain = brain
        log.info("Autonomous engine: brain reference set.")

    def notify_user_active(self):
        """Called when user sends a message — pauses autonomous work briefly."""
        import time
        self._user_active_until = time.time() + CONFIG.AUTONOMOUS_PAUSE_AFTER_USER

    @property
    def current_activity(self) -> str:
        return self._current_activity

    @property
    def is_busy(self) -> bool:
        return self._current_goal is not None

    async def get_status_summary(self) -> str:
        """Build a human-readable status summary for when user asks 'what are you doing?'"""
        status = await self.memory.get_current_status()
        lines = []

        if self._current_goal:
            goal = self._current_goal
            plan = json.loads(goal.get("plan", "[]")) if isinstance(goal.get("plan"), str) else goal.get("plan", [])
            step = goal.get("current_step", 0)
            total = len(plan)
            lines.append(f"Currently working on: {goal['title']}")
            lines.append(f"  Progress: step {step}/{total}")
            if step < total and plan:
                lines.append(f"  Current step: {plan[step] if step < len(plan) else 'finishing up'}")
            lines.append(f"  Activity: {self._current_activity}")
        else:
            lines.append("Not actively working on any goal right now.")

        active_goals = status.get("active_goals", [])
        if active_goals:
            lines.append(f"\nPending goals in queue: {len(active_goals)}")
            for g in active_goals[:3]:
                lines.append(f"  - [{g['priority']}] {g['title']} ({g['status']})")

        recent = status.get("recent_activity", [])
        if recent:
            lines.append(f"\nRecent activity:")
            for a in recent[-3:]:
                lines.append(f"  - [{a['timestamp'][:19]}] {a['description']}")

        lines.append(f"\nSession stats: {status['total_messages']} messages, {status['total_actions']} actions")
        lines.append(f"Autonomous cycles completed: {self._cycle_count}")

        return "\n".join(lines)

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._main_loop())
        log.info("Autonomous engine started.")

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Autonomous engine stopped.")

    async def add_goal(self, title: str, description: str, priority: int = 5,
                       source: str = "user") -> int:
        """Externally add a goal (from user or from the agent itself)."""
        goal_id = await self.memory.create_goal(
            title=title, description=description, priority=priority, source=source
        )
        await self.memory.log_activity("goal_created", f"New goal: {title}", {"goal_id": goal_id})
        return goal_id

    # ── Main Loop ───────────────────────────────────────────────────────────

    async def _main_loop(self):
        # Wait for brain to be set and system to stabilise
        await asyncio.sleep(10)
        log.info("Autonomous engine entering main cycle...")

        while self._running:
            try:
                # Respect user activity pause
                import time
                if time.time() < self._user_active_until:
                    self._current_activity = "Paused (user active)"
                    await asyncio.sleep(5)
                    continue

                # Back off if the brain's API is unhealthy (e.g. 403 key error)
                if self._brain and not self._brain.api_healthy:
                    self._current_activity = "Paused (API error — check API key)"
                    log.warning("Autonomous engine paused: brain API is unhealthy.")
                    await asyncio.sleep(120)
                    continue

                await self._autonomous_cycle()
                self._cycle_count += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Autonomous engine error: {e}", exc_info=True)
                self._current_activity = f"Error: {str(e)[:100]}"
                await self.memory.log_activity("autonomous_error", str(e)[:300])

            await asyncio.sleep(CONFIG.AUTONOMOUS_CYCLE_SECONDS)

    async def _autonomous_cycle(self):
        """One full autonomous cycle: check goals → plan → execute → reflect."""
        if not self._brain:
            return

        self._current_activity = "Checking for pending goals..."
        await self.memory.log_activity("cycle_start", f"Autonomous cycle #{self._cycle_count}")

        # 1. Check for pending goals
        goals = await self.memory.get_pending_goals(limit=5)

        # 2. If no goals, generate new ones by self-reflection
        if not goals:
            self._current_activity = "Self-reflecting to find improvements..."
            await self._self_reflect()
            goals = await self.memory.get_pending_goals(limit=5)

        if not goals:
            self._current_activity = "Idle — no goals to pursue"
            return

        # 3. Pick highest priority goal
        goal = goals[0]
        self._current_goal = goal
        await self.memory.update_goal(goal["id"], status="in_progress")
        self._current_activity = f"Working on: {goal['title']}"
        await self.memory.log_activity("goal_started", f"Starting goal: {goal['title']}", {"goal_id": goal["id"]})

        try:
            # 4. Plan if no plan exists yet
            plan = json.loads(goal["plan"]) if isinstance(goal["plan"], str) else goal["plan"]
            if not plan:
                plan = await self._plan_goal(goal)
                await self.memory.update_goal(goal["id"], plan=plan)

            # 5. Execute the plan step by step
            await self._execute_goal(goal, plan)

        except Exception as e:
            log.error(f"Goal execution error: {e}", exc_info=True)
            await self.memory.update_goal(goal["id"], status="failed", error=str(e)[:500])
            await self.memory.log_activity("goal_failed", f"Goal failed: {goal['title']}: {e}", {"goal_id": goal["id"]})
        finally:
            self._current_goal = None
            self._current_activity = "Idle"

    async def _self_reflect(self):
        """Ask the brain to reflect on what improvements/goals to pursue."""
        try:
            # Gather context
            recent_actions = await self.memory.get_recent_actions(limit=15)
            knowledge = await self.memory.get_knowledge(limit=10)
            all_goals = await self.memory.get_all_goals(limit=10)

            from skills import get_skill_summary, TOOL_MAP

            action_summary = ""
            failure_count = 0
            for act in recent_actions:
                if not act.get("success"):
                    failure_count += 1
            if recent_actions:
                action_types = {}
                for a in recent_actions:
                    t = a.get("action_type", "?")
                    action_types[t] = action_types.get(t, 0) + 1
                action_summary = ", ".join(f"{k}({v}x)" for k, v in sorted(action_types.items(), key=lambda x: -x[1])[:8])

            completed_goals = [g for g in all_goals if g.get("status") == "completed"]
            failed_goals = [g for g in all_goals if g.get("status") == "failed"]

            reflect_prompt = (
                "AUTONOMOUS SELF-REFLECTION\n\n"
                "You are running autonomously. No user input is needed. Think about what you should do next.\n\n"
                f"Current skills: {get_skill_summary()}\n"
                f"Total tools: {len(TOOL_MAP)}\n"
                f"Recent tool usage: {action_summary or 'none yet'}\n"
                f"Recent failures: {failure_count}\n"
                f"Completed goals: {len(completed_goals)}\n"
                f"Failed goals: {len(failed_goals)}\n\n"
                "Generate 1-2 useful goals you can pursue RIGHT NOW. Focus on:\n"
                "  - Creating useful new skills/tools you don't have yet\n"
                "  - Improving existing capabilities\n"
                "  - System optimization and maintenance\n"
                "  - Learning about the host system\n"
                "  - Fixing any issues from recent failures\n\n"
                "Respond with JSON:\n"
                '{"goals": [{"title": "short title", "description": "what to do and why", "priority": 1-10}]}\n'
                "Priority 1 = most urgent, 10 = least. Be specific and actionable.\n"
                "If nothing useful to do, return {\"goals\": []}"
            )

            decision = await self._brain.think(reflect_prompt)
            response_text = decision.get("response", "")

            # Try to extract goals from the brain's response
            goals_data = None

            # First check if the brain returned structured parameters
            params = decision.get("parameters", {})
            if "goals" in params:
                goals_data = params["goals"]

            # Otherwise try to parse from response
            if not goals_data:
                try:
                    import re
                    # Look for JSON in the response
                    match = re.search(r'\{.*"goals".*\}', response_text, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group(0))
                        goals_data = parsed.get("goals", [])
                except (json.JSONDecodeError, AttributeError):
                    pass

            # Also check the thought field
            if not goals_data:
                thought = decision.get("thought", "")
                try:
                    import re
                    match = re.search(r'\{.*"goals".*\}', thought, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group(0))
                        goals_data = parsed.get("goals", [])
                except (json.JSONDecodeError, AttributeError):
                    pass

            if goals_data and isinstance(goals_data, list):
                for g in goals_data[:2]:  # Max 2 goals per reflection
                    if isinstance(g, dict) and g.get("title") and g.get("description"):
                        await self.add_goal(
                            title=g["title"],
                            description=g["description"],
                            priority=g.get("priority", 5),
                            source="self_reflection",
                        )
                        log.info(f"Self-reflection generated goal: {g['title']}")

        except Exception as e:
            log.error(f"Self-reflection error: {e}", exc_info=True)

    async def _plan_goal(self, goal: dict) -> list:
        """Ask the brain to create a step-by-step plan for a goal."""
        plan_prompt = (
            f"AUTONOMOUS PLANNING — Create a step-by-step plan.\n\n"
            f"Goal: {goal['title']}\n"
            f"Description: {goal['description']}\n\n"
            "Create a detailed plan with concrete, executable steps.\n"
            "Each step should be a single tool call or action.\n\n"
            "Respond with JSON:\n"
            '{"plan": ["step 1 description", "step 2 description", ...]}\n'
            "Keep it practical — 2-8 steps max. Be specific about what tools to use."
        )

        decision = await self._brain.think(plan_prompt)
        plan = []

        # Try to extract plan from various locations
        params = decision.get("parameters", {})
        if "plan" in params and isinstance(params["plan"], list):
            plan = params["plan"]

        if not plan:
            for field in ["response", "thought"]:
                text = decision.get(field, "")
                try:
                    import re
                    match = re.search(r'\{.*"plan".*\}', text, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group(0))
                        if "plan" in parsed and isinstance(parsed["plan"], list):
                            plan = parsed["plan"]
                            break
                except (json.JSONDecodeError, AttributeError):
                    continue

        if not plan:
            # Fallback: use the description as a single step
            plan = [goal["description"]]

        log.info(f"Planned {len(plan)} steps for goal: {goal['title']}")
        await self.memory.log_activity(
            "goal_planned",
            f"Planned {len(plan)} steps for: {goal['title']}",
            {"goal_id": goal["id"], "steps": plan},
        )
        return plan

    async def _execute_goal(self, goal: dict, plan: list):
        """Execute a goal's plan step by step."""
        from tools import dispatch_tool

        current_step = goal.get("current_step", 0)

        for step_idx in range(current_step, len(plan)):
            # Check if we should pause for user activity
            import time
            if time.time() < self._user_active_until:
                self._current_activity = "Paused (user active)"
                await self.memory.update_goal(goal["id"], current_step=step_idx)
                await asyncio.sleep(CONFIG.AUTONOMOUS_PAUSE_AFTER_USER)
                continue

            if not self._running:
                break

            step_desc = plan[step_idx]
            self._current_activity = f"Step {step_idx + 1}/{len(plan)}: {step_desc[:80]}"
            await self.memory.log_activity(
                "goal_step",
                f"Executing step {step_idx + 1}/{len(plan)}: {step_desc[:100]}",
                {"goal_id": goal["id"], "step": step_idx},
            )

            # Ask brain what tool to use for this step
            exec_prompt = (
                f"AUTONOMOUS EXECUTION — Execute this step.\n\n"
                f"Goal: {goal['title']}\n"
                f"Current step ({step_idx + 1}/{len(plan)}): {step_desc}\n\n"
                f"Full plan: {json.dumps(plan)}\n\n"
                "Execute this step using the appropriate tool. "
                "Respond with your normal JSON format with action and parameters."
            )

            decision = await self._brain.think(exec_prompt)
            action = decision.get("action", "none")
            parameters = decision.get("parameters", {})

            if action and action != "none":
                try:
                    result = await dispatch_tool(action, parameters)

                    await self.memory.store_action(
                        action_type=action,
                        parameters=parameters,
                        result=result.stdout or result.stderr,
                        success=result.success,
                        thought=f"Autonomous: {goal['title']} step {step_idx + 1}",
                        response=decision.get("response", ""),
                    )

                    if result.success:
                        log.info(f"Autonomous step {step_idx + 1} succeeded: {action}")
                    else:
                        log.warning(f"Autonomous step {step_idx + 1} failed: {result.stderr[:200]}")
                        # Don't abort on failure — let brain try alternatives on next cycle

                except Exception as e:
                    log.error(f"Autonomous step execution error: {e}")

            await self.memory.update_goal(goal["id"], current_step=step_idx + 1)

            # Small delay between steps to avoid overwhelming the system
            await asyncio.sleep(3)

        # Goal complete
        await self.memory.update_goal(goal["id"], status="completed", result="All steps executed")
        await self.memory.log_activity(
            "goal_completed",
            f"Goal completed: {goal['title']}",
            {"goal_id": goal["id"], "steps_total": len(plan)},
        )
        log.info(f"Autonomous goal completed: {goal['title']}")

    @property
    def is_running(self) -> bool:
        return self._running
