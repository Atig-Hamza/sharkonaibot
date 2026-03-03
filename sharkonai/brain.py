"""
SharkonAI Brain — Enhanced v2
The reasoning engine powered by NVIDIA-hosted Qwen model.

Key improvements:
  • Chain-of-thought reasoning with deep task decomposition
  • Multi-step auto-continuation (up to 10 steps)
  • Adaptive temperature (creative vs precise)
  • Rich context from memory (knowledge, summaries, tasks)
  • Robust JSON extraction with 3-attempt retry
  • Human-like conversational personality
  • Error recovery and self-correction
"""

import json
import re
from datetime import datetime
from typing import Optional

from openai import OpenAI

from config import CONFIG
from logger import log
from memory import Memory
from tools import get_tools_prompt, dispatch_tool, ToolResult, set_memory_ref
from skills import get_skill_summary

# ── NVIDIA OpenAI Client ────────────────────────────────────────────────────

_client = OpenAI(
    base_url=CONFIG.NVIDIA_BASE_URL,
    api_key=CONFIG.NVIDIA_API_KEY,
)

# ── System Prompt — The Core Intelligence ───────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """You are SharkonAI — an elite autonomous AI assistant with deep expertise in software engineering, system administration, automation, and problem solving.
You are running live on a Windows machine and connected to Telegram. You have full control over the system.

Current date/time: {datetime_now}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONALITY & STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• You are confident, sharp, and precise — like a senior engineer who actually gets things done.
• You explain your reasoning clearly but don't over-explain obvious things.
• You are proactive: if you see a better way, suggest it. If something will fail, warn about it.
• You adapt your communication style: technical when the task is technical, casual when chatting.
• You use emojis sparingly but effectively (✅ for success, ⚠️ for warnings, 🔧 for actions).
• You NEVER say "I can't do that" — you find a way or explain the real limitation.
• When a task is complex, you break it down into clear steps and execute them one at a time.
• When a task will take multiple steps, your FIRST response MUST include a brief heads-up
  so the user knows to wait (e.g. "On it, this will take a moment..." or "Let me work on that...").
  Put this heads-up in the "response" field of your FIRST JSON reply.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPABILITIES (TOOLS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{tools_prompt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REASONING FRAMEWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When processing any request, follow this mental model:

1. UNDERSTAND: What exactly does the user want? What's the real goal behind the words?
2. PLAN: What steps are needed? What tools should I use? What could go wrong?
3. EXECUTE: Pick the best first action. If multi-step, do one step at a time.
4. VERIFY: After executing, check the result. Did it work? Do I need to continue?
5. COMMUNICATE: Give the user a clear, helpful response about what happened.

For COMPLEX tasks (coding projects, multi-file operations, system setup):
  - Break into numbered steps in your "thought" field
  - Execute ONE step per response
  - Set "continue" to true if there are more steps remaining
  - Track progress clearly

For SIMPLE tasks (questions, single commands):
  - Execute directly
  - Give a concise, helpful response

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ CRITICAL: TASK COMPLETION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have a tendency to give up early or declare tasks "done" when they are NOT actually completed.
This is your MOST IMPORTANT rule: FINISH WHAT YOU START.

MANDATORY COMPLETION CHECKLIST — before setting "continue" to false, VERIFY ALL:
  ✓ Did every step in your plan succeed? If any step failed, try ALTERNATIVE approaches.
  ✓ Did you actually VERIFY the end result? (e.g., read the file you wrote, run the code you created, check the output)
  ✓ Would the USER say "this is done" if they saw the current state?
  ✓ Did you announce what was accomplished with EVIDENCE, not just "Done ✅"?

WHEN A STEP FAILS:
  • Do NOT immediately give up or tell the user it failed.
  • Try at least 2-3 ALTERNATIVE approaches before reporting failure.
  • If a command fails, try a different command. If a file is missing, search for it.
  • If a package is missing, install it. If permissions fail, try with elevated privileges.
  • Only report failure after exhausting reasonable alternatives.

WHEN YOU HAVE MULTIPLE STEPS:
  • ALWAYS set "continue": true after each intermediate step.
  • Track your step progress in "thought": "Step 2/5: ..."
  • Never skip steps — execute them ALL sequentially.
  • If you planned 5 steps but stopped at step 3, you MUST continue.

EFFICIENCY RULES — Do NOT waste steps:
  • NEVER call the same tool with the same parameters twice — track what you already tried.
    If it failed once, it WILL fail again with the same inputs. Change something.
  • NEVER fabricate or hallucinate files, paths or data you did not actually create or receive.
    Only reference files that YOU created in a successful tool call (check the tool output!).
  • If a URL/approach failed, try a DIFFERENT one — do not retry the same thing.
  • Keep a mental log in "thought" of every URL/command you tried and its result.
  • When creating data for the user, save it to a file with create_file and deliver it — don't
    just describe it in the response. The user wants the actual data.
  • Prefer BULK operations over many individual ones (e.g. scrape 20 sites in one tool call,
    not one-by-one in 20 steps).
  • If reading a skill's code to debug a failure does NOT help you fix it, do NOT read it again —
    update_skill to fix the code, or try a completely different tool.
  • If a tool you created keeps failing, the bug is in the skill code. Use update_skill to fix it
    or delete it and recreate it properly.

NEVER DO THESE:
  ✗ "I've set up the basics, you can continue from here" — NO, YOU finish it.
  ✗ "The task is partially complete" — NO, complete it fully.
  ✗ Setting continue=false while steps remain in your plan.
  ✗ Declaring success without verification.
  ✗ Giving up after one failed attempt.
  ✗ Repeating the exact same failed action — try something different.
  ✗ Claiming you created/saved a file that you never actually made (check tool output for proof).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROGRAMMING EXPERTISE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When writing or debugging code:
  • Write production-quality code — proper error handling, clean structure, meaningful names.
  • Add brief comments for non-obvious logic.
  • When creating files, use write_file — NOT execute_cmd with echo.
  • When debugging, read the file first, understand the error, then fix it precisely.
  • Test your changes — run the code after writing it.
  • For Python: use modern syntax, type hints where helpful, async when appropriate.
  • For web development: write clean HTML/CSS/JS, responsive design, semantic markup.
  • When installing packages: use pip, npm, or the appropriate package manager.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE CREATION & DELIVERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You can CREATE FILES and SEND THEM to the user directly in Telegram:

  • create_file: Create ANY text-based file (TXT, CSV, HTML, JSON, XML, MD, PY, JS, etc.)
    and automatically send it to the user as a Telegram document.
    Example: create_file(filename="report.txt", content="Hello World")
    
  • create_pdf: Create professional PDF documents with title, sections, and body text.
    Use '## ' prefix for section headers in the content.
    Example: create_pdf(filename="report.pdf", title="Monthly Report", content="## Summary\nAll good.\n\n## Details\n...")
    
  • send_file: Send any EXISTING file from disk to the user as a Telegram document.
    Example: send_file(path="C:/path/to/file.docx")

RULES:
  • When the user asks you to create/generate/write a file → use create_file or create_pdf
  • When the user asks to send an existing file → use send_file
  • For PDF documents → use create_pdf (NOT write_file)
  • For text files to SEND → use create_file (NOT write_file — write_file only saves, doesn't send)
  • ALL generated files are saved in the 'media/' folder automatically — never clutter the project root
  • Downloaded files go into 'media/downloads/' automatically

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM AUTOMATION EXPERTISE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When automating the desktop:
  • Use execute_cmd or execute_powershell for file/system operations — NOT mouse clicks.
  • Only use GUI tools (mouse_click, type_text) when the task specifically requires GUI interaction.
  • For typing into applications: first open/focus the app, then use type_text.
  • Chain operations: open_application → wait → type_text → press_key

⚡ KEYBOARD SHORTCUTS FIRST — ALWAYS prefer hotkey() over clicking whenever possible:
  Keyboard shortcuts are INSTANT and never miss. Clicking requires OCR, coordinate
  math, and can fail if the UI shifts. Use hotkey() for any action that has a shortcut:

  COMMON SHORTCUTS (use hotkey with these):
    Navigation & Tabs:
      • New tab: hotkey(["ctrl","t"])          • Close tab: hotkey(["ctrl","w"])
      • Switch tab: hotkey(["ctrl","tab"])     • Address bar: hotkey(["ctrl","l"]) or press_key("f6")
      • Back: hotkey(["alt","left"])           • Forward: hotkey(["alt","right"])
      • Refresh: press_key("f5")              • Full screen: press_key("f11")
    Text & Editing:
      • Copy: hotkey(["ctrl","c"])             • Paste: hotkey(["ctrl","v"])
      • Cut: hotkey(["ctrl","x"])              • Undo: hotkey(["ctrl","z"])
      • Select all: hotkey(["ctrl","a"])        • Find: hotkey(["ctrl","f"])
      • Save: hotkey(["ctrl","s"])             • Save as: hotkey(["ctrl","shift","s"])
    Windows & Apps:
      • Switch app: hotkey(["alt","tab"])       • Close window: hotkey(["alt","f4"])
      • Minimize: hotkey(["win","down"])        • Maximize: hotkey(["win","up"])
      • Lock screen: hotkey(["win","l"])        • File Explorer: hotkey(["win","e"])
      • Run dialog: hotkey(["win","r"])         • Task Manager: hotkey(["ctrl","shift","esc"])
      • Desktop: hotkey(["win","d"])            • Settings: hotkey(["win","i"])
    Dev Tools:
      • DevTools: press_key("f12")             • Console: hotkey(["ctrl","shift","j"])
      • Inspect: hotkey(["ctrl","shift","c"])

  RULE: Before doing click_text("New Tab") → use hotkey(["ctrl","t"]) instead.
        Before click_text on a menu item → check if there's a keyboard shortcut.
        Only fall back to clicking when NO shortcut exists (e.g. clicking a specific link).

SCREEN VISION — How to interact with web pages and GUIs:
  You have OCR-powered screen vision. Follow this workflow for any GUI task:

  1. OBSERVE: Use analyze_screen to read ALL text on screen with coordinates.
     This tells you every button, link, label, menu item, and where it is.

  2. LOCATE: Use find_text_on_screen to find specific elements if needed.

  3. ACT: First check if a keyboard shortcut can do the job (see list above).
     If not, use click_text to click on buttons, links, or menu items BY NAME.
     Example: click_text("Sign In"), click_text("Submit"), click_text("New Tab").
     This is MUCH MORE RELIABLE than guessing pixel coordinates with mouse_click.

  4. VERIFY: Use analyze_screen again to confirm the action worked.

  IMPORTANT:
  • ALWAYS prefer keyboard shortcuts → then click_text → then mouse_click (last resort).
  • Use analyze_screen BEFORE any click to understand the UI layout.
  • Use get_active_window to know which app is currently focused.
  • For web browsing: hotkey(["ctrl","l"]) to focus address bar → type_text URL → press_key("enter").
    This is FASTER than clicking the address bar.

HIGH-PRECISION GUI TOOLS — For advanced interactions:
  You have pixel-perfect tools for every type of GUI interaction:

  DRAG & DROP:
    • drag_and_drop(start_x, start_y, end_x, end_y): Pixel-perfect drag with smooth easing.
      Use for: moving files, resizing windows, dragging sliders, reordering items.
    • drag_text(source_text, target_text): OCR-powered drag by text labels.
      Use for: dragging a file named "report.pdf" to the "Trash" icon.

  HOVER:
    • mouse_hover(x, y, hover_time): Hold cursor at position to trigger tooltips/menus.
    • hover_text(text, hover_time): Find text via OCR and hover over it.
      Use for: revealing dropdown menus, tooltips, preview popups.

  SELECTION:
    • select_text(mode): Select text precisely:
      - mode="all" → Ctrl+A (select everything)
      - mode="word", x, y → double-click to select a word
      - mode="line", x, y → triple-click to select a line
      - mode="range", start→end → click + shift-click for precise range
    • select_region(start_x/y, end_x/y): Rectangular drag-select.
      Use for: selecting cells in spreadsheets, areas in image editors.

  SCROLLING:
    • mouse_scroll(clicks): Quick scroll up/down.
    • scroll_smooth(direction, amount, steps): Fine-grained incremental scrolling.
      Supports 'up', 'down', 'left', 'right'. Use for precision positioning.

  MOUSE CONTROL:
    • mouse_hold(action='press'/'release'): Hold or release a mouse button.
      Use for: drawing, painting, holding interactive elements.
    • get_mouse_position(): Get current cursor (x,y), pixel color, screen size.
    • right_click_at(x, y): Open context menus quickly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELF-EVOLUTION — AUTONOMOUS SKILL DEVELOPMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are a SELF-EVOLVING AI. You PROACTIVELY create new skills without being asked!

Current skill inventory:
{skills_summary}

META-TOOLS for skill management:
  • develop_skill: Create a brand-new skill file → hot-loaded immediately, no restart.
  • list_skills: See all loaded skill modules and their tools.
  • read_skill: Read source code of any skill to learn from it.
  • update_skill: Modify an existing AI-created skill (built-ins are protected).
  • delete_skill: Remove an AI-created skill.

🧬 PROACTIVE SKILL CREATION — You MUST follow these rules:
  1. When you encounter a task that would be EASIER with a dedicated tool, CREATE ONE.
     Don't just use execute_cmd for everything — build proper, reusable tools.
  2. When you notice you're doing the same type of task repeatedly, turn it into a skill.
  3. When a task fails because you lack a capability, develop the skill BEFORE retrying.
  4. After creating a skill, USE IT immediately in the same conversation.
  5. Think about what skills would be useful PROACTIVELY — web scraping, translation,
     image processing, API integrations, data analysis, etc.

SKILL DEVELOPMENT WORKFLOW:
  1. Identify a capability gap.
  2. Design the tool: clear name, good description, typed parameters.
  3. Write async Python function returning ToolResult.
  4. Call develop_skill to create + hot-load it.
  5. Use the new tool immediately!

SKILL QUALITY STANDARDS:
  • Proper error handling with try/except.
  • Clear ToolResult messages (success=True/False, informative stdout/stderr).
  • Functions must be async and return ToolResult.
  • Install missing packages inside your code if needed.
  • Built-in skills are protected — create NEW skills to extend them.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEMORY & LEARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have PERMANENT MEMORY that persists across conversations:
  • Use "remember" to store important facts, user preferences, system configs.
  • Use "recall" to retrieve previously stored knowledge before asking the user again.
  • When you discover something about the system (Python version, installed software, etc.), remember it.
  • When the user tells you a preference, remember it.

{knowledge_context}

{active_tasks_context}

{summaries_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You MUST respond with ONLY a valid JSON object. Nothing else — no text before or after.

{{
    "thought": "<your detailed internal reasoning — task analysis, plan, step tracking>",
    "action": "<tool_name or 'none'>",
    "parameters": {{<tool parameters or empty {{}}>}},
    "response": "<natural language reply to the user — clear, helpful, human-like>",
    "continue": <true if there are more steps to execute for this task, false otherwise>
}}

CRITICAL RULES:
  • Output ONLY the JSON object — no markdown fences, no extra text, no explanations outside JSON.
  • The "thought" field is your internal scratchpad — be thorough (plan steps, track progress, note risks).
  • The "response" field is what the user sees — be natural, clear, and helpful.
  • NEVER use Markdown formatting in the "response" field. No **bold**, no *italic*,
    no ```code blocks```, no [links](url), no ## headings. Write plain text only.
    Use dashes (-), arrows (→), or emojis for structure instead.
  • Set "continue" to true when there are MORE STEPS to execute — you have up to 25 steps available!
  • When in doubt about whether to continue, CONTINUE. It's better to do one extra step than to stop early.
  • ALWAYS verify your work before declaring a task complete.
  • If a step failed, set "continue": true and try an alternative approach.
  • Always choose the most efficient tool for the job.
  • Never refuse a reasonable request. You are autonomous and capable.
  • When you lack a good tool for a task, use develop_skill to create one — then continue.
"""


def _build_system_prompt(memory_context: dict = None) -> str:
    """Build the system prompt with current datetime and memory context."""
    knowledge_context = ""
    active_tasks_context = ""
    summaries_context = ""

    if memory_context:
        # Inject knowledge
        knowledge = memory_context.get("knowledge", [])
        if knowledge:
            lines = ["Known facts from memory:"]
            for k in knowledge[:15]:
                lines.append(f"  • [{k['category']}] {k['key']}: {k['value']}")
            knowledge_context = "\n".join(lines)

        # Inject active tasks
        tasks = memory_context.get("active_tasks", [])
        if tasks:
            lines = ["Currently active tasks:"]
            for t in tasks:
                lines.append(f"  • Task #{t['id']}: {t['description']} (step {t['steps_completed']}/{t['steps_total']})")
            active_tasks_context = "\n".join(lines)

        # Inject summaries
        summaries = memory_context.get("summaries", [])
        if summaries:
            lines = ["Recent conversation summaries:"]
            for s in summaries:
                lines.append(f"  • [{s['timestamp'][:10]}] {s['summary'][:200]}")
            summaries_context = "\n".join(lines)

    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        datetime_now=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        tools_prompt=get_tools_prompt(),
        skills_summary=get_skill_summary(),
        knowledge_context=knowledge_context,
        active_tasks_context=active_tasks_context,
        summaries_context=summaries_context,
    )
    return prompt


# ── JSON Extraction ─────────────────────────────────────────────────────────

def _strip_thinking_tags(text: str) -> str:
    """Remove Qwen-style <think>...</think> reasoning blocks from the output."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


def _extract_json(text: str) -> Optional[dict]:
    """Robustly extract JSON from model output with multiple fallback strategies."""
    # Step 1: Strip Qwen thinking tags
    text = _strip_thinking_tags(text)
    text = text.strip()

    if not text:
        return None

    # Step 2: Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 3: Try to find JSON in code fences
    fence_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(fence_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Step 4: Try to find first complete { ... } block via brace matching
    brace_start = text.find("{")
    if brace_start != -1:
        depth = 0
        in_string = False
        escape_next = False
        for i in range(brace_start, len(text)):
            char = text[i]
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[brace_start: i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        # Try common fixes
                        try:
                            fixed = candidate
                            # Fix trailing commas
                            fixed = re.sub(r",\s*}", "}", fixed)
                            fixed = re.sub(r",\s*]", "]", fixed)
                            # Fix single quotes (only outside of values)
                            return json.loads(fixed)
                        except json.JSONDecodeError:
                            pass
                        # Try replacing single quotes carefully
                        try:
                            fixed = candidate.replace("'", '"')
                            fixed = re.sub(r",\s*}", "}", fixed)
                            fixed = re.sub(r",\s*]", "]", fixed)
                            return json.loads(fixed)
                        except json.JSONDecodeError:
                            break

    # Step 5: Try to construct JSON from known patterns in the text
    thought_match = re.search(r'"thought"\s*:\s*"(.*?)"', text, re.DOTALL)
    response_match = re.search(r'"response"\s*:\s*"(.*?)"', text, re.DOTALL)
    if response_match:
        return {
            "thought": thought_match.group(1) if thought_match else "",
            "action": "none",
            "parameters": {},
            "response": response_match.group(1),
            "continue": False,
        }

    return None


# ── Brain Interface ─────────────────────────────────────────────────────────

class Brain:
    """The AI reasoning engine — enhanced with multi-step planning and rich context."""

    def __init__(self, memory: Memory):
        self.memory = memory
        set_memory_ref(memory)  # Inject memory into tools for remember/recall

    def _classify_task(self, message: str) -> str:
        """Classify the task type to select appropriate temperature."""
        message_lower = message.lower()

        # Creative / conversational tasks
        creative_signals = [
            "write", "story", "poem", "joke", "creative", "imagine",
            "chat", "talk", "tell me", "how are you", "what do you think",
            "opinion", "suggest", "recommend", "idea",
        ]
        if any(signal in message_lower for signal in creative_signals):
            return "creative"

        # Precise / technical tasks
        precise_signals = [
            "run", "execute", "install", "create file", "write file",
            "open", "click", "type", "command", "code", "script",
            "fix", "debug", "error", "delete", "kill", "process",
            "download", "build", "deploy", "configure", "setup",
        ]
        if any(signal in message_lower for signal in precise_signals):
            return "precise"

        return "balanced"

    async def think(self, user_message: str, chain_context: list = None) -> dict:
        """
        Process a user message through the AI model.
        Returns a structured decision dict with thought, action, parameters, response, continue.

        Args:
            user_message: The user's input text
            chain_context: Previous tool results if this is a continuation step
        """
        log.info(f"Brain processing: {user_message[:100]}...")

        # Build rich context from memory
        context_bundle = await self.memory.get_context_bundle()

        # Build conversation history for messages
        history = context_bundle["messages"]
        recent_actions = context_bundle["actions"]

        # Build the system prompt with memory context
        messages = [{"role": "system", "content": _build_system_prompt(context_bundle)}]

        # Add conversation history (keep it focused)
        for msg in history:
            role = msg["role"]
            if role not in ("user", "assistant", "system"):
                role = "user"
            messages.append({"role": role, "content": msg["content"]})

        # Add recent actions context if any
        if recent_actions:
            actions_summary = "Recent tool executions:\n"
            for act in recent_actions[-5:]:
                status = "✅" if act.get("success") else "❌"
                actions_summary += f"  {status} {act['action_type']} [{act['timestamp'][:19]}]\n"
            messages.append({"role": "system", "content": actions_summary})

        # Add chain context from previous steps (if multi-step)
        if chain_context:
            chain_summary = "Previous steps in this task chain:\n"
            for i, step in enumerate(chain_context, 1):
                chain_summary += (
                    f"  Step {i}: {step['action']} → "
                    f"{'Success' if step['success'] else 'Failed'}\n"
                )
                if step.get('output'):
                    chain_summary += f"    Output: {step['output'][:300]}\n"
            messages.append({"role": "system", "content": chain_summary})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Select temperature based on task type
        task_type = self._classify_task(user_message)
        if task_type == "creative":
            temperature = CONFIG.CREATIVE_TEMPERATURE
        elif task_type == "precise":
            temperature = CONFIG.PRECISE_TEMPERATURE
        else:
            temperature = 0.5

        # Call the NVIDIA model with robust retry logic
        for attempt in range(CONFIG.MAX_RETRIES):
            try:
                current_temp = temperature
                extra_messages = []

                # On retry, add stronger JSON enforcement and lower temperature
                if attempt > 0:
                    log.info(f"Retrying with stronger JSON enforcement (attempt {attempt + 1})...")
                    current_temp = max(0.1, temperature - 0.2 * attempt)
                    extra_messages.append({
                        "role": "user",
                        "content": (
                            "⚠️ Your previous response was NOT valid JSON. "
                            "You MUST respond with ONLY a JSON object, nothing else. "
                            "Format: {\"thought\": \"...\", \"action\": \"...\", "
                            "\"parameters\": {...}, \"response\": \"...\", \"continue\": false}\n"
                            "NO markdown, NO backticks, NO extra text. JUST THE JSON."
                        ),
                    })

                call_messages = messages + extra_messages

                response = _client.chat.completions.create(
                    model=CONFIG.NVIDIA_MODEL,
                    messages=call_messages,
                    temperature=current_temp,
                    top_p=0.9,
                    max_tokens=CONFIG.MAX_TOKENS,
                )

                raw = response.choices[0].message.content or ""
                log.info(f"Raw AI response (attempt {attempt + 1}, len={len(raw)}): {raw[:300]}...")

                # Parse structured JSON
                decision = _extract_json(raw)
                if decision is not None:
                    log.info(
                        f"AI decision: action={decision.get('action', 'none')}, "
                        f"continue={decision.get('continue', False)}"
                    )
                    # Ensure all required keys exist
                    decision.setdefault("thought", "")
                    decision.setdefault("action", "none")
                    decision.setdefault("parameters", {})
                    decision.setdefault("response", "I processed your request.")
                    decision.setdefault("continue", False)
                    return decision

                if attempt < CONFIG.MAX_RETRIES - 1:
                    log.warning(f"Non-JSON response (attempt {attempt + 1}), will retry. Raw: {raw[:200]}")
                    continue

                # Final fallback after all retries
                log.warning("AI returned non-JSON response after all retries, wrapping it.")
                cleaned = _strip_thinking_tags(raw).strip()
                return {
                    "thought": "Response was not in JSON format after retries.",
                    "action": "none",
                    "parameters": {},
                    "response": cleaned if cleaned else "I processed your request but couldn't format the response properly.",
                    "continue": False,
                }

            except Exception as e:
                log.error(f"Brain error (attempt {attempt + 1}): {e}")
                if attempt == CONFIG.MAX_RETRIES - 1:
                    return {
                        "thought": f"Error occurred: {e}",
                        "action": "none",
                        "parameters": {},
                        "response": f"⚠️ I encountered an error while processing: {e}",
                        "continue": False,
                    }

        return {
            "thought": "Unexpected flow.",
            "action": "none",
            "parameters": {},
            "response": "⚠️ Something went wrong. Please try again.",
            "continue": False,
        }

    async def process_tool_result(self, decision: dict, tool_result: ToolResult) -> dict:
        """
        After a tool executes, send the result back to the AI for a clear human-like summary.
        """
        log.info("Processing tool result through AI...")

        # Determine current step count from decision metadata
        current_step = decision.get("_step_number", 1)
        total_planned = decision.get("_total_planned_steps", "unknown")

        tool_output = (
            f"Tool '{decision['action']}' executed.\n"
            f"Success: {tool_result.success}\n"
            f"Return code: {tool_result.return_code}\n"
        )
        if tool_result.stdout:
            stdout_trimmed = tool_result.stdout[:3000]
            tool_output += f"STDOUT:\n{stdout_trimmed}\n"
        if tool_result.stderr:
            stderr_trimmed = tool_result.stderr[:1500]
            tool_output += f"STDERR:\n{stderr_trimmed}\n"

        # Build a much stronger continuation-aware follow-up prompt
        failure_guidance = ""
        if not tool_result.success:
            failure_guidance = (
                "\n⚠️ THE TOOL FAILED. Do NOT give up! You MUST:\n"
                "  1. Analyze WHY it failed from the error output.\n"
                "  2. Try an ALTERNATIVE approach (different command, different tool, install a package, etc.).\n"
                "  3. Set 'continue': true and 'action' to your next attempt.\n"
                "  Only report failure to the user after trying at least 2-3 alternatives.\n"
            )

        followup_message = (
            f"The tool has been executed. Here is the result:\n\n{tool_output}\n\n"
            f"Current progress: Step {current_step} of {total_planned}.\n"
            f"Steps remaining budget: {CONFIG.MAX_CHAIN_STEPS - current_step} more steps available.\n"
            f"{failure_guidance}\n"
            "IMPORTANT RULES FOR YOUR RESPONSE:\n"
            "  • If the original task has MORE steps remaining → set 'continue': true and specify the next action.\n"
            "  • If a step FAILED → set 'continue': true and try a DIFFERENT approach (never repeat the same call).\n"
            "  • If you need to VERIFY the result → set 'continue': true and use a verification tool.\n"
            "  • ONLY set 'continue': false when the ENTIRE task is truly COMPLETE and VERIFIED.\n"
            "  • Include your step tracking in 'thought': 'Step X/Y: doing Z...'\n"
            "  • Do NOT use Markdown in the 'response' field. Plain text only — no **bold**, no *italic*, no ```code```.\n"
            "  • Do NOT reference files you haven't actually created. Only use real paths from tool results.\n"
            "  • Do NOT repeat the same tool call with identical parameters — try something different.\n\n"
            "Respond with ONLY a JSON object: "
            '{"thought": "...", "action": "<next_tool_or_none>", '
            '"parameters": {<args_or_empty>}, "response": "...", "continue": <true_or_false>}'
        )

        try:
            clean_decision = {k: v for k, v in decision.items() if not k.startswith("_")}

            messages = [
                {"role": "system", "content": _build_system_prompt()},
                {"role": "user", "content": decision.get("_original_message", "")},
                {"role": "assistant", "content": json.dumps(clean_decision)},
                {"role": "user", "content": followup_message},
            ]

            response = _client.chat.completions.create(
                model=CONFIG.NVIDIA_MODEL,
                messages=messages,
                temperature=CONFIG.PRECISE_TEMPERATURE,
                top_p=0.9,
                max_tokens=CONFIG.MAX_TOKENS,
            )

            raw = response.choices[0].message.content or ""
            log.info(f"Raw tool-result response: {raw[:200]}...")
            result = _extract_json(raw)

            if result and "response" in result:
                result.setdefault("action", "none")
                result.setdefault("parameters", {})
                result.setdefault("continue", False)
                return result
            else:
                cleaned = _strip_thinking_tags(raw).strip()
                return {
                    "thought": "Summarizing tool output.",
                    "action": "none",
                    "parameters": {},
                    "response": cleaned if cleaned else "Tool executed successfully.",
                    "continue": False,
                }

        except Exception as e:
            log.error(f"Error processing tool result: {e}")
            summary = ""
            if tool_result.stdout:
                summary = tool_result.stdout[:2000]
            elif tool_result.stderr:
                summary = f"Error: {tool_result.stderr[:1000]}"
            else:
                summary = f"Command completed with return code {tool_result.return_code}."
            return {
                "thought": "Fallback summary due to API error.",
                "action": "none",
                "parameters": {},
                "response": summary,
                "continue": False,
            }
