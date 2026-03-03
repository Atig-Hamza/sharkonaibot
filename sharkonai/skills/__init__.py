"""
SharkonAI Skills System — Dynamic Skill Loader & Manager
Automatically discovers and loads all skill modules from this folder.
Supports hot-reloading of new skills created at runtime by the AI.

Every skill file must expose:
  • SKILL_DEFINITIONS : list[dict]   — tool definitions (name, description, parameters)
  • SKILL_MAP         : dict[str, callable] — mapping of tool name → async function

Optional:
  • SKILL_SETUP(memory) — called once at startup if the skill needs the memory ref
"""

import importlib
import importlib.util
import os
import sys
import traceback
from typing import Callable, Dict, List, Optional

from logger import log

# ── Skill Registry ──────────────────────────────────────────────────────────

TOOL_DEFINITIONS: List[dict] = []
TOOL_MAP: Dict[str, Callable] = {}

_skills_dir = os.path.dirname(os.path.abspath(__file__))
_loaded_modules: Dict[str, object] = {}
_memory_ref = None


def set_memory_ref(memory):
    """Inject the memory reference into skills that need it."""
    global _memory_ref
    _memory_ref = memory
    # Push to any already-loaded skill that has a SKILL_SETUP
    for name, mod in _loaded_modules.items():
        setup_fn = getattr(mod, "SKILL_SETUP", None)
        if setup_fn:
            try:
                setup_fn(memory)
            except Exception as e:
                log.error(f"SKILL_SETUP failed for '{name}': {e}")


def _load_skill_module(file_path: str, module_name: str) -> Optional[object]:
    """Load a single skill module from disk."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            log.warning(f"Cannot create spec for skill: {file_path}")
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        log.error(f"Failed to load skill '{module_name}' from {file_path}: {e}")
        log.debug(traceback.format_exc())
        return None


def _register_skill(mod, module_name: str):
    """Extract SKILL_DEFINITIONS and SKILL_MAP from a loaded module."""
    defs = getattr(mod, "SKILL_DEFINITIONS", [])
    smap = getattr(mod, "SKILL_MAP", {})

    if not defs and not smap:
        log.debug(f"Skill '{module_name}' has no SKILL_DEFINITIONS or SKILL_MAP, skipping.")
        return 0

    count = 0
    for d in defs:
        name = d.get("name")
        if name and name not in TOOL_MAP:
            TOOL_DEFINITIONS.append(d)
        elif name and name in TOOL_MAP:
            # Update the existing definition
            for i, existing in enumerate(TOOL_DEFINITIONS):
                if existing.get("name") == name:
                    TOOL_DEFINITIONS[i] = d
                    break

    for name, func in smap.items():
        TOOL_MAP[name] = func
        count += 1

    # If the skill has a SKILL_SETUP and we already have memory, call it
    setup_fn = getattr(mod, "SKILL_SETUP", None)
    if setup_fn and _memory_ref:
        try:
            setup_fn(_memory_ref)
        except Exception as e:
            log.error(f"SKILL_SETUP failed for '{module_name}': {e}")

    return count


def load_all_skills():
    """
    Discover and load all .py skill files in the skills/ directory.
    Called once at startup.
    """
    global TOOL_DEFINITIONS, TOOL_MAP
    TOOL_DEFINITIONS.clear()
    TOOL_MAP.clear()
    _loaded_modules.clear()

    if not os.path.isdir(_skills_dir):
        log.warning(f"Skills directory not found: {_skills_dir}")
        return

    total_tools = 0
    skill_files = sorted(f for f in os.listdir(_skills_dir)
                         if f.endswith(".py") and f != "__init__.py")

    for filename in skill_files:
        filepath = os.path.join(_skills_dir, filename)
        module_name = f"skills.{filename[:-3]}"

        mod = _load_skill_module(filepath, module_name)
        if mod is None:
            continue

        count = _register_skill(mod, module_name)
        _loaded_modules[module_name] = mod
        if count > 0:
            log.info(f"  Loaded skill: {filename} ({count} tools)")
        total_tools += count

    log.info(f"Skills system loaded: {len(_loaded_modules)} skills, {total_tools} tools total.")


def load_single_skill(filename: str) -> bool:
    """
    Hot-load (or reload) a single skill file. Used when the AI creates a new skill at runtime.
    Returns True on success.
    """
    filepath = os.path.join(_skills_dir, filename)
    if not os.path.exists(filepath):
        log.error(f"Skill file not found: {filepath}")
        return False

    module_name = f"skills.{filename[:-3]}"

    # If already loaded, remove old registrations
    if module_name in _loaded_modules:
        old_mod = _loaded_modules[module_name]
        old_map = getattr(old_mod, "SKILL_MAP", {})
        old_defs = getattr(old_mod, "SKILL_DEFINITIONS", [])
        for name in old_map:
            TOOL_MAP.pop(name, None)
        for d in old_defs:
            TOOL_DEFINITIONS[:] = [x for x in TOOL_DEFINITIONS if x.get("name") != d.get("name")]
        # Remove from sys.modules for clean reload
        sys.modules.pop(module_name, None)

    mod = _load_skill_module(filepath, module_name)
    if mod is None:
        return False

    count = _register_skill(mod, module_name)
    _loaded_modules[module_name] = mod
    log.info(f"Hot-loaded skill: {filename} ({count} tools)")
    return True


def get_loaded_skills() -> List[str]:
    """Return list of loaded skill module names."""
    return list(_loaded_modules.keys())


def get_tools_prompt() -> str:
    """Generate a system-prompt-friendly description of all available tools."""
    lines = ["Available tools:\n"]
    for tool in TOOL_DEFINITIONS:
        params = ", ".join(
            f'{k} ({v["type"]}): {v["description"]}'
            for k, v in tool.get("parameters", {}).items()
        )
        lines.append(f'• {tool["name"]}: {tool["description"]}')
        if params:
            lines.append(f'  Parameters: {params}\n')
        else:
            lines.append(f'  Parameters: (none)\n')
    return "\n".join(lines)


def get_skill_summary() -> str:
    """
    Return a compact summary of all loaded skills and their tools.
    Used by the brain to maintain awareness of current capabilities.
    """
    lines = []
    skill_files = sorted(f for f in os.listdir(_skills_dir)
                         if f.endswith(".py") and f != "__init__.py")

    builtin = set()
    custom = set()

    for filename in skill_files:
        module_name = f"skills.{filename[:-3]}"
        if module_name not in _loaded_modules:
            continue
        mod = _loaded_modules[module_name]
        smap = getattr(mod, "SKILL_MAP", {})
        tool_names = list(smap.keys())
        if not tool_names:
            continue

        # Detect if AI-generated (has "Author: SharkonAI" in docstring)
        doc = getattr(mod, "__doc__", "") or ""
        is_custom = "SharkonAI (auto-generated" in doc or "Author: SharkonAI" in doc

        if is_custom:
            desc_line = doc.strip().split("\n")[0].strip() if doc.strip() else filename
            custom.add(filename)
            lines.append(f"  [AI-created] {filename}: {', '.join(tool_names)} — {desc_line}")
        else:
            builtin.add(filename)

    summary = f"Skills loaded: {len(builtin)} built-in, {len(custom)} AI-created. "
    summary += f"Total tools: {len(TOOL_MAP)}."
    if lines:
        summary += "\nAI-created skills:\n" + "\n".join(lines)
    return summary


# ── Auto-load on import ────────────────────────────────────────────────────
load_all_skills()
