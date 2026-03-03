"""
Skill: Skill Developer (Meta-Skill)
Allows SharkonAI to CREATE NEW SKILLS at runtime — the AI writes its own tools.

This is the self-evolution engine. When the AI encounters a task it doesn't have
a tool for, it can use these meta-tools to:
  1. develop_skill   — Write a brand-new skill .py file and hot-load it immediately
  2. list_skills     — See all currently loaded skills and their tools
  3. read_skill      — Read the source code of an existing skill (to learn/extend)
  4. update_skill    — Modify an existing AI-generated skill
  5. delete_skill    — Remove a skill that is no longer needed

The AI-generated skills follow the same interface as built-in skills and become
available immediately without restarting.
"""

import os
import re
import textwrap
from datetime import datetime

from logger import log
from skills.system_commands import ToolResult


# ── Memory Reference (injected at startup) ──────────────────────────────────
_memory_ref = None


def SKILL_SETUP(memory):
    """Called by the skill loader to inject the memory reference."""
    global _memory_ref
    _memory_ref = memory


async def _store_skill_knowledge(action: str, filename: str, skill_name: str,
                                  tool_names: list, description: str = ""):
    """Persist skill metadata to the knowledge base so the AI remembers its skills."""
    if not _memory_ref:
        return
    try:
        if action in ("created", "updated"):
            await _memory_ref.store_knowledge(
                category="ai_skills",
                key=filename,
                value=f"{skill_name} | tools: {', '.join(tool_names)} | {description}",
                confidence=1.0,
                source=f"skill_{action}",
            )
        elif action == "deleted":
            await _memory_ref.store_knowledge(
                category="ai_skills",
                key=filename,
                value=f"[DELETED] was: {skill_name}",
                confidence=0.0,
                source="skill_deleted",
            )
    except Exception as e:
        log.debug(f"Failed to persist skill knowledge: {e}")


# ── Constants ───────────────────────────────────────────────────────────────

_builtin_skills_dir = os.path.dirname(os.path.abspath(__file__))
_ai_skills_dir = os.path.join(os.path.dirname(_builtin_skills_dir), "skills_by_Sharkon")

# Ensure AI skills directory exists
os.makedirs(_ai_skills_dir, exist_ok=True)

# Built-in skills that cannot be modified or deleted by the AI
PROTECTED_SKILLS = {
    "system_commands.py",
    "file_operations.py",
    "gui_automation.py",
    "screen_vision.py",
    "system_info.py",
    "network.py",
    "clipboard.py",
    "memory_tools.py",
    "audio_transcription.py",
    "utility.py",
    "skill_developer.py",  # Protect itself
    "__init__.py",
}

# Template for AI-generated skills
SKILL_TEMPLATE = '''"""
Skill: {skill_name}
Description: {description}
Author: SharkonAI (auto-generated on {timestamp})
Version: {version}
"""

import asyncio
import os

from logger import log
from skills.system_commands import ToolResult  # ALWAYS use this ToolResult — never redefine it


# ── Tool Definitions ────────────────────────────────────────────────────────

SKILL_DEFINITIONS = {definitions_json}


# ── Tool Implementations ────────────────────────────────────────────────────

{implementations}


# ── Skill Map ───────────────────────────────────────────────────────────────

SKILL_MAP = {skill_map}
'''


# ── Definitions ─────────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
    {
        "name": "develop_skill",
        "description": (
            "CREATE A NEW SKILL (tool/capability) for yourself. "
            "Use this when you need a tool that doesn't exist yet. "
            "You write the Python code for the skill, and it becomes immediately available. "
            "The skill must follow the standard format with SKILL_DEFINITIONS and SKILL_MAP. "
            "Each tool function must be async and return a ToolResult. "
            "Example: if you need a 'translate_text' tool, you develop a skill for it. "
            "The skill file is saved to the skills/ folder and hot-loaded instantly. "
            "IMPORTANT: Use descriptive snake_case filenames like 'web_scraper.py', 'email_sender.py'. "
            "You can import from: os, asyncio, subprocess, json, re, urllib, and any pip package "
            "(install missing packages inside your code with execute_cmd('pip install X'))."
        ),
        "parameters": {
            "skill_name": {
                "type": "string",
                "description": (
                    "Human-readable name for the skill (e.g., 'Web Scraper', 'Email Sender', 'Weather API')."
                ),
            },
            "filename": {
                "type": "string",
                "description": (
                    "Python filename for the skill (e.g., 'web_scraper.py', 'email_sender.py'). "
                    "Must end in .py and use snake_case."
                ),
            },
            "description": {
                "type": "string",
                "description": "What this skill does — a clear description of its purpose.",
            },
            "tool_definitions": {
                "type": "string",
                "description": (
                    "JSON string of the SKILL_DEFINITIONS list. Each tool must have: "
                    "name (str), description (str), parameters (dict of param_name → {type, description}). "
                    'Example: [{"name": "translate", "description": "Translate text", '
                    '"parameters": {"text": {"type": "string", "description": "Text to translate"}, '
                    '"target_lang": {"type": "string", "description": "Target language code"}}}]'
                ),
            },
            "tool_code": {
                "type": "string",
                "description": (
                    "The Python source code implementing the tool functions. "
                    "Each function MUST be: async def tool_name(params...) -> ToolResult. "
                    "Use ToolResult(success=True/False, stdout='output', stderr='error', return_code=0/1). "
                    "Do NOT define or import ToolResult yourself — it is auto-provided by the template. "
                    "You can import any standard library module. For 3rd party packages, install them "
                    "first inside your code: subprocess.run(['pip', 'install', 'package_name']). "
                    "Include proper error handling with try/except."
                ),
            },
            "tool_map": {
                "type": "string",
                "description": (
                    'JSON string mapping tool names to function names. Example: {"translate": "translate"}. '
                    "The keys are the tool names from definitions, values are the function names in tool_code."
                ),
            },
        },
    },
    {
        "name": "list_skills",
        "description": (
            "List all currently loaded skills and their tools. "
            "Shows which skills are built-in vs AI-generated, and what tools each provides."
        ),
        "parameters": {},
    },
    {
        "name": "read_skill",
        "description": (
            "Read the source code of an existing skill. "
            "Use this to understand how a skill works, to learn from it, or as a reference for creating new ones."
        ),
        "parameters": {
            "filename": {
                "type": "string",
                "description": "The skill filename to read (e.g., 'network.py', 'clipboard.py').",
            },
        },
    },
    {
        "name": "update_skill",
        "description": (
            "Update/modify an existing AI-generated skill. "
            "Replaces the entire skill file with new code and hot-reloads it. "
            "Cannot modify built-in/protected skills."
        ),
        "parameters": {
            "filename": {
                "type": "string",
                "description": "The skill filename to update.",
            },
            "skill_name": {
                "type": "string",
                "description": "Updated skill name.",
            },
            "description": {
                "type": "string",
                "description": "Updated description.",
            },
            "tool_definitions": {
                "type": "string",
                "description": "Updated JSON SKILL_DEFINITIONS.",
            },
            "tool_code": {
                "type": "string",
                "description": "Updated Python implementation code.",
            },
            "tool_map": {
                "type": "string",
                "description": "Updated JSON tool map.",
            },
        },
    },
    {
        "name": "delete_skill",
        "description": (
            "Delete an AI-generated skill that is no longer needed. "
            "Cannot delete built-in/protected skills. "
            "The tools provided by the skill will be immediately unregistered."
        ),
        "parameters": {
            "filename": {
                "type": "string",
                "description": "The skill filename to delete (e.g., 'my_custom_skill.py').",
            },
        },
    },
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def _validate_filename(filename: str) -> str:
    """Validate and sanitize a skill filename."""
    if not filename.endswith(".py"):
        filename += ".py"
    # Only allow safe characters
    base = filename[:-3]
    if not re.match(r'^[a-z][a-z0-9_]*$', base):
        return ""
    return filename


def _parse_json_string(s: str) -> object:
    """Parse a JSON string, handling various formats."""
    import json
    s = s.strip()
    # Remove markdown code fences if present
    if s.startswith("```"):
        s = re.sub(r'^```(?:json)?\s*', '', s)
        s = re.sub(r'\s*```$', '', s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Try fixing common issues
        fixed = re.sub(r",\s*}", "}", s)
        fixed = re.sub(r",\s*]", "]", fixed)
        return json.loads(fixed)


def _build_skill_file(skill_name: str, description: str, definitions, code: str, tool_map_dict: dict) -> str:
    """Build the complete skill file content."""
    import json

    # Format definitions as a proper Python literal
    defs_str = json.dumps(definitions, indent=4)

    # Build the SKILL_MAP dict literal
    map_entries = []
    for tool_name, func_name in tool_map_dict.items():
        map_entries.append(f'    "{tool_name}": {func_name},')
    map_str = "{\n" + "\n".join(map_entries) + "\n}"

    return SKILL_TEMPLATE.format(
        skill_name=skill_name,
        description=description,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        version="1.0",
        definitions_json=defs_str,
        implementations=code,
        skill_map=map_str,
    )


# ── Implementations ─────────────────────────────────────────────────────────

async def develop_skill(skill_name: str, filename: str, description: str,
                        tool_definitions: str, tool_code: str, tool_map: str) -> ToolResult:
    """Create a new skill file and hot-load it into the system."""
    log.info(f"🧬 Developing new skill: {skill_name} ({filename})")

    # Validate filename
    safe_filename = _validate_filename(filename)
    if not safe_filename:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Invalid filename '{filename}'. Must be snake_case letters/numbers/underscores, ending in .py.",
            return_code=1,
        )

    # Check if it conflicts with a protected skill
    if safe_filename in PROTECTED_SKILLS:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Cannot overwrite protected built-in skill '{safe_filename}'. Use a different name.",
            return_code=1,
        )

    filepath = os.path.join(_ai_skills_dir, safe_filename)

    # Check if file already exists (use update_skill instead)
    if os.path.exists(filepath):
        return ToolResult(
            success=False, stdout="",
            stderr=f"Skill '{safe_filename}' already exists. Use update_skill to modify it, or choose a different name.",
            return_code=1,
        )

    try:
        # Parse the JSON definitions and map
        try:
            definitions = _parse_json_string(tool_definitions)
        except Exception as e:
            return ToolResult(success=False, stdout="", stderr=f"Invalid tool_definitions JSON: {e}", return_code=1)

        try:
            tool_map_dict = _parse_json_string(tool_map)
        except Exception as e:
            return ToolResult(success=False, stdout="", stderr=f"Invalid tool_map JSON: {e}", return_code=1)

        # Validate definitions structure
        if not isinstance(definitions, list) or len(definitions) == 0:
            return ToolResult(success=False, stdout="", stderr="tool_definitions must be a non-empty JSON array.", return_code=1)

        for d in definitions:
            if "name" not in d or "description" not in d:
                return ToolResult(success=False, stdout="", stderr=f"Each tool definition needs 'name' and 'description'. Got: {d}", return_code=1)

        # Validate tool_map
        if not isinstance(tool_map_dict, dict) or len(tool_map_dict) == 0:
            return ToolResult(success=False, stdout="", stderr="tool_map must be a non-empty JSON object.", return_code=1)

        # Build the skill file
        file_content = _build_skill_file(skill_name, description, definitions, tool_code, tool_map_dict)

        # Write the file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(file_content)

        log.info(f"Skill file written: {filepath}")

        # Hot-load the skill
        from skills import load_single_skill
        success = load_single_skill(safe_filename, ai_created=True)

        if success:
            tool_names = list(tool_map_dict.keys())
            log.info(f"✅ Skill '{skill_name}' created and loaded! Tools: {tool_names}")
            # Persist skill metadata to knowledge base
            await _store_skill_knowledge("created", safe_filename, skill_name, tool_names, description)
            return ToolResult(
                success=True,
                stdout=(
                    f"✅ New skill '{skill_name}' created successfully!\n"
                    f"📁 File: skills_by_Sharkon/{safe_filename}\n"
                    f"🔧 New tools available: {', '.join(tool_names)}\n"
                    f"The skill is loaded and ready to use immediately."
                ),
                stderr="", return_code=0,
            )
        else:
            # Load failed — read the file back to check for syntax errors
            # Try to give a helpful error message
            import py_compile
            try:
                py_compile.compile(filepath, doraise=True)
                error_msg = "Skill file has valid syntax but failed to load. Check the imports and logic."
            except py_compile.PyCompileError as e:
                error_msg = f"Syntax error in generated skill: {e}"

            # Don't delete — let the AI fix it with update_skill
            return ToolResult(
                success=False, stdout="",
                stderr=f"Skill file was created but failed to hot-load.\n{error_msg}\nUse update_skill to fix it.",
                return_code=1,
            )

    except Exception as e:
        # Clean up on error
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        log.error(f"develop_skill error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Failed to create skill: {e}", return_code=1)


async def list_skills() -> ToolResult:
    """List all loaded skills and their tools."""
    log.info("Listing all skills...")
    try:
        from skills import get_loaded_skills, TOOL_MAP as all_tools, _loaded_modules

        lines = ["═══ SharkonAI Skills Registry ═══\n"]

        # Built-in skills
        lines.append("── Built-in Skills (skills/) ──")
        builtin_files = sorted(f for f in os.listdir(_builtin_skills_dir)
                              if f.endswith(".py") and f != "__init__.py")

        for filename in builtin_files:
            module_name = f"skills.{filename[:-3]}"
            is_loaded = module_name in _loaded_modules
            status = "🟢" if is_loaded else "🔴"

            lines.append(f"{status} {filename} [built-in]")

            if is_loaded:
                mod = _loaded_modules[module_name]
                smap = getattr(mod, "SKILL_MAP", {})
                if smap:
                    for tool_name in smap:
                        lines.append(f"    • {tool_name}")
                doc = getattr(mod, "__doc__", "")
                if doc:
                    first_line = doc.strip().split("\n")[0].strip()
                    if first_line:
                        lines.append(f"    📝 {first_line}")
            lines.append("")

        # AI-generated skills
        lines.append("── AI-Created Skills (skills_by_Sharkon/) ──")
        ai_files = []
        if os.path.isdir(_ai_skills_dir):
            ai_files = sorted(f for f in os.listdir(_ai_skills_dir)
                             if f.endswith(".py") and f != "__init__.py")

        if not ai_files:
            lines.append("  (none yet — use develop_skill to create one!)")
        else:
            for filename in ai_files:
                module_name = f"skills_by_Sharkon.{filename[:-3]}"
                is_loaded = module_name in _loaded_modules
                status = "🟢" if is_loaded else "🔴"

                lines.append(f"{status} {filename} [AI-generated]")

                if is_loaded:
                    mod = _loaded_modules[module_name]
                    smap = getattr(mod, "SKILL_MAP", {})
                    if smap:
                        for tool_name in smap:
                            lines.append(f"    • {tool_name}")
                    doc = getattr(mod, "__doc__", "")
                    if doc:
                        first_line = doc.strip().split("\n")[0].strip()
                        if first_line:
                            lines.append(f"    📝 {first_line}")
                lines.append("")

        lines.append(f"Total: {len(builtin_files) + len(ai_files)} skill files, {len(all_tools)} tools loaded.")

        return ToolResult(success=True, stdout="\n".join(lines), stderr="", return_code=0)
    except Exception as e:
        log.error(f"list_skills error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def read_skill(filename: str) -> ToolResult:
    """Read the source code of a skill."""
    log.info(f"Reading skill: {filename}")
    if not filename.endswith(".py"):
        filename += ".py"
    # Check AI skills dir first, then built-in
    filepath = os.path.join(_ai_skills_dir, filename)
    if not os.path.exists(filepath):
        filepath = os.path.join(_builtin_skills_dir, filename)
    if not os.path.exists(filepath):
        return ToolResult(success=False, stdout="", stderr=f"Skill '{filename}' not found.", return_code=1)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return ToolResult(success=True, stdout=content, stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def update_skill(filename: str, skill_name: str, description: str,
                       tool_definitions: str, tool_code: str, tool_map: str) -> ToolResult:
    """Update an existing AI-generated skill."""
    log.info(f"Updating skill: {filename}")

    safe_filename = _validate_filename(filename)
    if not safe_filename:
        return ToolResult(success=False, stdout="", stderr=f"Invalid filename '{filename}'.", return_code=1)

    if safe_filename in PROTECTED_SKILLS:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Cannot modify protected built-in skill '{safe_filename}'. Create a new skill instead.",
            return_code=1,
        )

    filepath = os.path.join(_ai_skills_dir, safe_filename)
    if not os.path.exists(filepath):
        return ToolResult(success=False, stdout="", stderr=f"Skill '{safe_filename}' not found in skills_by_Sharkon/. Use develop_skill to create it.", return_code=1)

    # Backup the current version
    backup_path = filepath + ".bak"
    try:
        with open(filepath, "r") as f:
            backup_content = f.read()
        with open(backup_path, "w") as f:
            f.write(backup_content)
    except Exception:
        pass

    try:
        definitions = _parse_json_string(tool_definitions)
        tool_map_dict = _parse_json_string(tool_map)
        file_content = _build_skill_file(skill_name, description, definitions, tool_code, tool_map_dict)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(file_content)

        from skills import load_single_skill
        success = load_single_skill(safe_filename, ai_created=True)

        if success:
            # Clean up backup
            try:
                os.remove(backup_path)
            except OSError:
                pass
            tool_names = list(tool_map_dict.keys())
            # Persist updated skill metadata
            await _store_skill_knowledge("updated", safe_filename, skill_name, tool_names, description)
            return ToolResult(
                success=True,
                stdout=f"✅ Skill '{skill_name}' updated and reloaded! Tools: {', '.join(tool_names)}",
                stderr="", return_code=0,
            )
        else:
            # Restore backup
            try:
                with open(backup_path, "r") as f:
                    with open(filepath, "w") as out:
                        out.write(f.read())
                from skills import load_single_skill as reload
                reload(safe_filename)
            except Exception:
                pass
            return ToolResult(
                success=False, stdout="",
                stderr="Updated skill failed to load. Previous version restored. Check your code for errors.",
                return_code=1,
            )
    except Exception as e:
        # Restore backup
        try:
            if os.path.exists(backup_path):
                with open(backup_path, "r") as f:
                    with open(filepath, "w") as out:
                        out.write(f.read())
        except Exception:
            pass
        log.error(f"update_skill error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Update failed: {e}", return_code=1)


async def delete_skill(filename: str) -> ToolResult:
    """Delete an AI-generated skill."""
    log.info(f"Deleting skill: {filename}")

    if not filename.endswith(".py"):
        filename += ".py"

    if filename in PROTECTED_SKILLS:
        return ToolResult(success=False, stdout="", stderr=f"Cannot delete protected built-in skill '{filename}'.", return_code=1)

    filepath = os.path.join(_ai_skills_dir, filename)
    if not os.path.exists(filepath):
        return ToolResult(success=False, stdout="", stderr=f"Skill '{filename}' not found in skills_by_Sharkon/. Only AI-generated skills can be deleted.", return_code=1)

    try:
        # Unregister tools from the global registry
        from skills import TOOL_DEFINITIONS as all_defs, TOOL_MAP as all_tools, _loaded_modules
        import sys

        module_name = f"skills_by_Sharkon.{filename[:-3]}"
        if module_name in _loaded_modules:
            mod = _loaded_modules[module_name]
            old_map = getattr(mod, "SKILL_MAP", {})
            old_defs = getattr(mod, "SKILL_DEFINITIONS", [])

            removed_tools = list(old_map.keys())

            for name in old_map:
                all_tools.pop(name, None)
            all_defs[:] = [d for d in all_defs if d.get("name") not in {dd.get("name") for dd in old_defs}]

            del _loaded_modules[module_name]
            sys.modules.pop(module_name, None)
        else:
            removed_tools = []

        # Delete the file
        os.remove(filepath)

        # Also delete backup if exists
        backup_path = filepath + ".bak"
        if os.path.exists(backup_path):
            os.remove(backup_path)

        # Persist deletion to knowledge
        await _store_skill_knowledge("deleted", filename, filename[:-3], removed_tools)

        return ToolResult(
            success=True,
            stdout=f"✅ Skill '{filename}' deleted. Removed tools: {', '.join(removed_tools) or 'none'}",
            stderr="", return_code=0,
        )
    except Exception as e:
        log.error(f"delete_skill error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Delete failed: {e}", return_code=1)


# ── Skill Map ───────────────────────────────────────────────────────────────

SKILL_MAP = {
    "develop_skill": develop_skill,
    "list_skills": list_skills,
    "read_skill": read_skill,
    "update_skill": update_skill,
    "delete_skill": delete_skill,
}
