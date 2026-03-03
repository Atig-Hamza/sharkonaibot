"""
SharkonAI Cognition Loop — Enhanced v3
Background autonomous cognition with system monitoring,
proactive health checks, periodic memory maintenance,
and AUTONOMOUS SKILL EVOLUTION.
"""

import asyncio
import platform
import shutil
from datetime import datetime

from config import CONFIG
from logger import log
from memory import Memory


class CognitionLoop:
    """
    Runs a background loop that maintains SharkonAI's internal state.
    Includes system health monitoring, memory stats, skill inventory,
    and autonomous skill evolution.
    """

    def __init__(self, memory: Memory):
        self.memory = memory
        self._running = False
        self._task: asyncio.Task = None
        self._tick_count = 0
        self._brain = None  # Injected later for skill evolution

    def set_brain(self, brain):
        """Inject the brain reference for autonomous skill evolution."""
        self._brain = brain
        log.info("Cognition loop: brain reference set for skill evolution.")

    async def start(self):
        """Start the cognition loop as a background task."""
        if self._running:
            log.warning("Cognition loop is already running.")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        log.info("Cognition loop started.")

    async def stop(self):
        """Stop the cognition loop gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Cognition loop stopped.")

    async def _loop(self):
        """Main cognition loop."""
        log.info("Cognition loop entering main cycle...")

        while self._running:
            try:
                await self._tick()
                self._tick_count += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Cognition loop error: {e}", exc_info=True)

            await asyncio.sleep(CONFIG.COGNITION_INTERVAL_SECONDS)

    async def _tick(self):
        """Single cognition tick — comprehensive system and memory health check."""
        now = datetime.utcnow().isoformat()

        # ── Core heartbeat ──
        await self.memory.set_state("last_heartbeat", now)
        await self.memory.set_state("tick_count", str(self._tick_count))

        # ── Gather stats ──
        msg_count = await self.memory.get_message_count()
        action_count = await self.memory.get_action_count()

        await self.memory.set_state("total_messages", str(msg_count))
        await self.memory.set_state("total_actions", str(action_count))

        # ── System health (every 5 ticks) ──
        if self._tick_count % 5 == 0:
            await self._check_system_health()

        # ── Skill inventory (every 10 ticks) ──
        if self._tick_count % 10 == 0:
            await self._inventory_skills()

        # ── Autonomous skill evolution (every SKILL_EVOLUTION_INTERVAL ticks) ──
        if (CONFIG.SKILL_EVOLUTION_ENABLED
                and self._brain is not None
                and self._tick_count > 0
                and self._tick_count % CONFIG.SKILL_EVOLUTION_INTERVAL == 0):
            await self._evolve_skills()

        # ── Log periodic status (every 10 ticks) ──
        if self._tick_count % 10 == 0:
            log.info(
                f"Cognition tick #{self._tick_count} | "
                f"Messages: {msg_count} | Actions: {action_count} | "
                f"Time: {now}"
            )

    async def _check_system_health(self):
        """Check system resources and store metrics."""
        try:
            # Disk space
            total, used, free = shutil.disk_usage("/")
            disk_pct = (used / total) * 100
            await self.memory.set_state("disk_used_pct", f"{disk_pct:.1f}")
            await self.memory.set_state("disk_free_gb", f"{free / (1024 ** 3):.1f}")

            if disk_pct > 90:
                log.warning(f"Disk usage is high: {disk_pct:.1f}% used!")

        except Exception as e:
            log.debug(f"System health check error: {e}")

        try:
            # Database file size
            import os
            db_size = os.path.getsize(CONFIG.DATABASE_PATH) if os.path.exists(CONFIG.DATABASE_PATH) else 0
            await self.memory.set_state("db_size_mb", f"{db_size / (1024 * 1024):.2f}")
        except Exception:
            pass

    async def _inventory_skills(self):
        """Inventory all loaded skills and store metadata in knowledge base."""
        try:
            from skills import get_loaded_skills, TOOL_MAP, _loaded_modules, get_skill_summary
            import os

            base_dir = os.path.dirname(os.path.abspath(__file__))
            builtin_dir = os.path.join(base_dir, "skills")
            ai_dir = os.path.join(base_dir, "skills_by_Sharkon")

            builtin_files = sorted(f for f in os.listdir(builtin_dir)
                                   if f.endswith(".py") and f != "__init__.py")

            ai_files = []
            if os.path.isdir(ai_dir):
                ai_files = sorted(f for f in os.listdir(ai_dir)
                                  if f.endswith(".py") and f != "__init__.py")

            skill_files = builtin_files + ai_files

            # Collect AI-generated skill details
            ai_generated = []
            for filename in ai_files:
                module_name = f"skills_by_Sharkon.{filename[:-3]}"
                if module_name in _loaded_modules:
                    mod = _loaded_modules[module_name]
                    smap = getattr(mod, "SKILL_MAP", {})
                    ai_generated.append(f"{filename}: {', '.join(smap.keys())}")

            # Store inventory in state
            await self.memory.set_state("skills_total", str(len(skill_files)))
            await self.memory.set_state("skills_ai_generated", str(len(ai_generated)))
            await self.memory.set_state("tools_total", str(len(TOOL_MAP)))

            if ai_generated:
                await self.memory.set_state("ai_skills_list", "; ".join(ai_generated))

            log.debug(f"Skill inventory: {len(skill_files)} skills, {len(TOOL_MAP)} tools, {len(ai_generated)} AI-generated")

        except Exception as e:
            log.debug(f"Skill inventory error: {e}")

    async def _evolve_skills(self):
        """
        Autonomous skill evolution — review recent actions and failures,
        then ask the brain to consider creating new skills.
        This runs periodically without user interaction.
        """
        try:
            log.info("🧬 Skill evolution cycle starting...")

            # Gather context: recent actions, failures, and current skills
            recent_actions = await self.memory.get_recent_actions(limit=20)
            from skills import get_skill_summary, TOOL_MAP

            # Analyze patterns: look for repeated tool uses, failures, and gaps
            action_counts = {}
            failure_types = {}
            for act in recent_actions:
                atype = act.get("action_type", "unknown")
                action_counts[atype] = action_counts.get(atype, 0) + 1
                if not act.get("success"):
                    failure_types[atype] = failure_types.get(atype, 0) + 1

            # Build the evolution prompt
            skills_summary = get_skill_summary()
            action_summary = ", ".join(f"{k}({v}x)" for k, v in sorted(action_counts.items(), key=lambda x: -x[1])[:10])
            failure_summary = ", ".join(f"{k}({v} fails)" for k, v in failure_types.items()) if failure_types else "none"

            evolution_prompt = (
                "AUTONOMOUS SKILL EVOLUTION CHECK\n\n"
                f"Current skills: {skills_summary}\n"
                f"Recent tool usage pattern: {action_summary}\n"
                f"Recent failures: {failure_summary}\n"
                f"Available tools: {len(TOOL_MAP)}\n\n"
                "Based on the usage patterns and failures above, do you see an opportunity to "
                "create a new skill that would improve your capabilities? Consider:\n"
                "  • Tools that are being used repeatedly in complex ways (combine into one)\n"
                "  • Failures that could be avoided with a dedicated tool\n"
                "  • Common tasks that would benefit from a specialized skill\n"
                "  • Useful utilities like: web scraping, data parsing, API clients, etc.\n\n"
                "If you identify a useful skill to create, use develop_skill to build it.\n"
                "If no improvement is needed right now, respond with action='none'.\n"
                "Be selective — only create skills that provide real value."
            )

            # Ask the brain to evaluate
            decision = await self._brain.think(evolution_prompt)

            action = decision.get("action", "none")
            if action and action != "none":
                log.info(f"🧬 Skill evolution: AI chose to execute '{action}'")
                from tools import dispatch_tool

                # Execute the skill development action
                result = await dispatch_tool(action, decision.get("parameters", {}))

                if result.success:
                    log.info(f"🧬 Skill evolution SUCCESS: {result.stdout[:200]}")
                    # Store the evolution event
                    await self.memory.store_knowledge(
                        category="skill_evolution",
                        key=f"evolution_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                        value=f"Auto-created: {result.stdout[:300]}",
                        source="autonomous_evolution",
                    )

                    # If the AI wants to continue (e.g., test the new skill), let it
                    if decision.get("continue", False):
                        next_action = decision.get("action", "none")
                        if next_action and next_action != "none":
                            follow_result = await dispatch_tool(next_action, decision.get("parameters", {}))
                            log.info(f"🧬 Follow-up action: {follow_result.success}")
                else:
                    log.warning(f"🧬 Skill evolution FAILED: {result.stderr[:200]}")
            else:
                log.debug("🧬 Skill evolution: no improvements needed this cycle.")

        except Exception as e:
            log.error(f"Skill evolution error: {e}", exc_info=True)

    @property
    def is_running(self) -> bool:
        return self._running
