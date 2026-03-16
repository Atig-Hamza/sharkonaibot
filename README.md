
<h1 align="center">🦈 SharkonAI</h1>

<p align="center">
  <b>Autonomous AI Agent for Telegram — Powered by NVIDIA AI</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"/>
  <img src="https://img.shields.io/badge/NVIDIA-AI_Endpoint-76B900?style=for-the-badge&logo=nvidia&logoColor=white" alt="NVIDIA"/>
  <img src="https://img.shields.io/badge/SQLite-Memory-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/>
  <img src="https://img.shields.io/badge/License-Private-red?style=for-the-badge" alt="License"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/v4.0-Stable-brightgreen?style=flat-square" alt="Version"/>
  <img src="https://img.shields.io/badge/Tools-60+-blue?style=flat-square" alt="Tools"/>
  <img src="https://img.shields.io/badge/Chain_Steps-25-orange?style=flat-square" alt="Chain Steps"/>
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Platform"/>
  <img src="https://img.shields.io/badge/Voice-Recognition-FF6F00?style=flat-square" alt="Voice"/>
  <img src="https://img.shields.io/badge/Web-Browsing-1a73e8?style=flat-square&logo=googlechrome&logoColor=white" alt="Web Browsing"/>
  <img src="https://img.shields.io/badge/Scheduler-⏰_Cron-f59e0b?style=flat-square" alt="Scheduler"/>
  <img src="https://img.shields.io/badge/Self--Evolving-🧬-purple?style=flat-square" alt="Self-Evolving"/>
</p>

---

## 🌊 Overview

**SharkonAI** is a fully autonomous, self-recovering AI agent that lives in Telegram. It combines a powerful LLM brain (NVIDIA-hosted models) with **60+ executable tools** to perform virtually anything — from running system commands and writing code, to controlling your desktop GUI with pixel-perfect precision, to **searching and browsing the full web**, to **scheduling recurring tasks**, to **creating its own new skills at runtime**.

Think of it as your personal AI operator that can **see your screen**, **type on your keyboard**, **click with your mouse**, **manage files**, **browse the web**, **listen to your voice**, **remember everything**, and **evolve its own capabilities** — all orchestrated through a simple Telegram chat.

Send **`stop`** at any time to immediately cancel a running task.

---

## ✨ Key Features

<table>
<tr>
<td width="50%" valign="top">

### 🧠 Enhanced AI Brain
- Chain-of-thought reasoning with deep task decomposition
- Multi-step auto-continuation (up to **25 steps** per task)
- Dual-temperature system: creative mode (0.7) & precise mode (0.2)
- Robust JSON extraction with 5 fallback strategies
- Automatic retry on parsing failures (3 attempts)
- Rich memory context injection (knowledge, summaries, active tasks)
- **Smart shortest-path resolution** — always picks the fastest tool

</td>
<td width="50%" valign="top">

### 🔧 60+ Executable Tools
- **System**: CMD, PowerShell, Python execution
- **Files**: Read, write, append, search, create PDFs, send files
- **GUI**: Mouse, keyboard, drag & drop, screenshots, OCR vision
- **Web**: Search, browse, screenshot, form automation, data extraction
- **Scheduler**: Cron tasks, recurring automation, one-shot reminders
- **Network**: HTTP requests, file downloads
- **Memory**: Permanent knowledge storage & recall
- **Media**: Webcam capture, image & file delivery
- **Voice**: Speech-to-text transcription
- **Meta**: Self-evolving skill creation system

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🌐 Web Browsing (NEW)
- **`web_search`** — DuckDuckGo search, no JS, instant results
- **`web_browse`** — Read any URL (fast HTTP or JS-rendered)
- **`web_screenshot`** — Full-page screenshot → sent to Telegram
- **`web_interact`** — Fill forms, click buttons, multi-step flows
- **`web_extract_data`** — Smart extraction: emails, prices, links, phones
- Playwright (Chromium headless) for JS-heavy sites
- Always picks the fastest path: search snippet → browse → JS

</td>
<td width="50%" valign="top">

### 👁️ Screen Vision (OCR)
- Full-screen or regional OCR analysis via Tesseract
- Click, hover, drag, and find any visible text element
- Pixel-perfect drag-and-drop GUI automation
- Smart text selection (word, line, range, all)
- Active window detection
- Dual OCR engine: Tesseract + Windows WinRT fallback

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🎤 Voice Recognition
- Auto-transcription of Telegram voice messages
- Google Web Speech API (free, no key needed)
- Supports **50+ languages** (en, fr, ar, es, de, zh, ja…)
- OGG / MP3 / M4A / FLAC / WebM support via ffmpeg
- Windows System.Speech offline fallback
- Voice messages processed as if user typed the text

</td>
<td width="50%" valign="top">

### 📚 Persistent Memory
- SQLite-backed message & action history (WAL mode)
- Knowledge base with category/key/value + confidence scores
- Task tracking for multi-step operations with progress
- Conversation summarization for long-term context
- Full-text search across messages and knowledge
- System state management (heartbeat, version, stats)

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🧬 Self-Evolving Skills
- **Creates its own new tools at runtime** — saved to `skills_by_Sharkon/`
- Hot-reloads new skills instantly without restart
- Can read, update, and delete its AI-created skills
- Periodic autonomous skill evolution via cognition loop
- Full skill inventory and introspection
- Built-in vs AI-created skill separation

</td>
<td width="50%" valign="top">

### 🛡️ Self-Recovery & Error Handling
- **Watchdog** monitors all subsystems continuously
- Auto-restarts crashed cognition loops
- Stale heartbeat detection and alerting
- **API circuit breaker** — detects 403/auth errors instantly, stops retries, sends clear fix instructions
- Responsive to new API keys without restart
- Graceful shutdown with OS signal handling

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ⏰ Cron Scheduler (NEW)
- Schedule **any task** to run once or on a recurring basis
- Supports: specific datetime, interval, daily, weekly, cron expressions
- Results delivered to Telegram automatically when tasks fire
- `schedule_task` — create from natural language ("every day at 09:00")
- `list_scheduled_tasks` — see all active tasks and next run times
- `cancel_scheduled_task` — disable by ID or name
- `run_task_now` — trigger immediately without waiting
- Persisted in SQLite — survives restarts

</td>
<td width="50%" valign="top">

### 🤖 Autonomous Engine
- Background self-directed goal generation & execution
- Periodic self-reflection to find capability gaps
- Goal planning, step-by-step execution, activity logging
- User can query "what are you doing?" at any time
- Pauses during user conversations, resumes after
- Backs off automatically on API errors

</td>
<td width="50%" valign="top">

### 🛑 Task Control
- Send **`stop`** or **`/stop`** to cancel any running task instantly
- Cancels multi-step tool chains mid-execution
- Cleans up status messages and typing indicators
- Safe stop with partial progress preserved
- Immediate feedback on stop confirmation

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Telegram User                          │
│                    (Authorized Only)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │  text / voice / files / photos
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               Telegram Handler (aiogram v3)                 │
│  • Message routing       • Voice transcription              │
│  • Tool chain executor   • File/image delivery              │
│  • Stop/cancel command   • Status messages                  │
└─────────┬────────────────────┬──────────────────────────────┘
          │                    │
          ▼                    ▼
┌──────────────────┐  ┌──────────────────────────────────────┐
│   Brain (LLM)    │  │         Tool Dispatcher               │
│  NVIDIA AI API   │  │  56+ tools across 12 skill modules   │
│  Chain-of-thought│  │  + dynamically created AI skills      │
│  JSON decisions  │  │  Timeout protection per tool call     │
│  API circuit     │  │                                      │
│  breaker (403)   │  │                                      │
└────────┬─────────┘  └──────────────────────────────────────┘
         │
         ▼
┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐
│  Memory (SQLite) │  │  Cognition Loop  │  │    Watchdog    │
│  Messages/Actions│  │  Heartbeat       │  │  Health checks │
│  Knowledge Base  │  │  System health   │  │  Auto-restart  │
│  Tasks/Summaries │  │  Skill evolution │  │  Stale detect  │
└──────────────────┘  └──────────────────┘  └────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│               Autonomous Engine (background)                  │
│  Self-reflection → Goal generation → Step execution          │
│  Pauses on user activity • Backs off on API errors           │
└──────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
Sharkon AI/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
└── sharkonai/
    ├── main.py                  # Entry point — starts all subsystems
    ├── config.py                # All settings and credentials
    ├── config.example.py        # Template config (safe to share)
    ├── brain.py                 # LLM reasoning engine (NVIDIA AI)
    ├── memory.py                # SQLite persistent memory
    ├── tools.py                 # Tool dispatcher with timeout & coercion
    ├── telegram_handler.py      # Telegram bot (aiogram v3)
    ├── cognition_loop.py        # Background autonomous loop
    ├── autonomous_engine.py     # Self-directed goal system
    ├── scheduler_engine.py      # Cron-like task scheduler ← NEW
    ├── watchdog.py              # Self-recovery monitor
    ├── logger.py                # Rotating file + console logging
    ├── database.db              # SQLite database (auto-created)
    ├── sharkonai.log            # Log file (auto-created)
    ├── media/                   # Generated files and media
    │   └── downloads/           # Downloaded/uploaded files
    ├── skills/                  # Built-in skill modules
    │   ├── __init__.py          # Dynamic skill loader & registry
    │   ├── system_commands.py   # CMD, PowerShell, Python execution
    │   ├── file_operations.py   # File read/write/search/PDF/send
    │   ├── web_browser.py       # Web search, browse, screenshot, forms ← NEW
    │   ├── scheduler.py         # Cron task scheduling tools ← NEW
    │   ├── gui_automation.py    # Mouse, keyboard, drag & drop
    │   ├── screen_vision.py     # Screenshot, OCR, click-by-text
    │   ├── audio_transcription.py  # Voice-to-text
    │   ├── clipboard.py         # System clipboard access
    │   ├── memory_tools.py      # Remember / recall knowledge
    │   ├── network.py           # HTTP requests, downloads
    │   ├── system_info.py       # System info, processes, webcam
    │   ├── skill_developer.py   # Self-evolution: create/edit/delete skills
    │   └── utility.py           # wait() and helpers
    └── skills_by_Sharkon/       # AI-created skills (auto-generated)
        └── *.py                 # Dynamically created at runtime
```

---

## 🛠️ Complete Tool Reference

### System & Execution
| Tool | Description |
|------|-------------|
| `execute_cmd` | Execute any CMD / terminal command |
| `execute_powershell` | Execute PowerShell scripts |
| `run_python` | Execute Python code in a subprocess |

### File Operations
| Tool | Description |
|------|-------------|
| `read_file` | Read contents of a file |
| `write_file` | Write content to a file |
| `append_file` | Append content to an existing file |
| `list_directory` | List directory contents |
| `find_files` | Search for files by glob pattern |
| `create_file` | Create a file and send it via Telegram |
| `create_pdf` | Generate a PDF document |
| `send_file` | Send an existing file as Telegram document |
| `send_image` | Send an image to the user |

### 🌐 Web Browsing (NEW)
| Tool | Description |
|------|-------------|
| `web_search` | Search DuckDuckGo — returns titles, URLs, snippets (fastest, no JS) |
| `web_browse` | Fetch a URL and return clean text content; set `use_js=true` for SPAs |
| `web_screenshot` | Headless screenshot of any URL → sent as photo to Telegram |
| `web_interact` | Automate web pages: fill forms, click buttons, extract data |
| `web_extract_data` | Smart extraction: emails, prices, links, phones, images, headings |

### GUI Automation
| Tool | Description |
|------|-------------|
| `type_text` | Type text (ASCII + Unicode support) |
| `press_key` | Press a keyboard key |
| `hotkey` | Press a key combination (e.g., Ctrl+C) |
| `mouse_click` | Click at screen coordinates |
| `mouse_move` | Move mouse cursor |
| `mouse_scroll` | Scroll up or down |
| `drag_and_drop` | Pixel-perfect drag operation |
| `mouse_hover` | Hover at a position |
| `select_text` | Select text (word / line / range / all) |
| `select_region` | Rectangular drag-select |
| `scroll_smooth` | Fine-grained directional scrolling |
| `mouse_hold` | Press and hold / release mouse button |
| `get_mouse_position` | Get cursor position + pixel color |
| `right_click_at` | Right-click at coordinates |

### Screen Vision & OCR
| Tool | Description |
|------|-------------|
| `screenshot` | Capture a screenshot |
| `analyze_screen` | OCR all on-screen text with coordinates |
| `click_text` | Find text on screen via OCR and click it |
| `find_text_on_screen` | Locate text position on screen |
| `drag_text` | Drag from one text label to another |
| `hover_text` | Hover over OCR-detected text |
| `get_active_window` | Get the currently focused window name |

### Voice & Audio
| Tool | Description |
|------|-------------|
| `transcribe_audio` | Transcribe audio/voice to text |

### Clipboard
| Tool | Description |
|------|-------------|
| `get_clipboard` | Read system clipboard |
| `set_clipboard` | Set system clipboard text |

### Memory & Knowledge
| Tool | Description |
|------|-------------|
| `remember` | Store a fact / preference in permanent memory |
| `recall` | Retrieve stored knowledge by category or search |

### ⏰ Scheduler (NEW)
| Tool | Description |
|------|-------------|
| `schedule_task` | Schedule a task to run once or repeatedly (interval/daily/weekly/cron) |
| `list_scheduled_tasks` | List all active scheduled tasks with next run times and run counts |
| `cancel_scheduled_task` | Disable a scheduled task by ID or label |
| `run_task_now` | Immediately trigger a scheduled task without waiting |

### Network
| Tool | Description |
|------|-------------|
| `http_request` | Make an HTTP GET request |
| `download_file` | Download a file from a URL |

### System Info & Apps
| Tool | Description |
|------|-------------|
| `get_system_info` | Get OS, CPU, memory, disk information |
| `get_running_processes` | List running processes |
| `kill_process` | Kill a process by name or PID |
| `open_application` | Launch an application (smart Windows app registry) |
| `take_photo` | Capture a photo via webcam |

### Self-Evolution (Meta)
| Tool | Description |
|------|-------------|
| `develop_skill` | Create a brand-new skill and hot-load it |
| `list_skills` | Inventory all loaded skills and tools |
| `read_skill` | Read source code of any skill |
| `update_skill` | Modify an existing AI-created skill |
| `delete_skill` | Remove an AI-created skill |

### Utility
| Tool | Description |
|------|-------------|
| `wait` | Sleep for N seconds (max 60) |

> **+ any skills dynamically created by the AI** — these appear in `skills_by_Sharkon/` and are loaded automatically.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Windows** (GUI automation and OCR require a desktop environment)
- **Tesseract OCR** installed and on PATH ([download](https://github.com/UB-Mannheim/tesseract/wiki))
- **ffmpeg** installed and on PATH (for voice message transcription)
- A **Telegram Bot** token from [@BotFather](https://t.me/BotFather)
- An **NVIDIA AI** API key from [build.nvidia.com](https://build.nvidia.com/)

### 1. Clone & Install

```bash
git clone https://github.com/your-username/sharkon-ai.git
cd sharkon-ai
pip install -r requirements.txt
```

### 2. Install Playwright browser (for web browsing)

```bash
playwright install chromium
```

> Only needed once. Downloads a headless Chromium (~200 MB). Required for `web_screenshot`, `web_interact`, and JS-heavy `web_browse`.

### 3. Configure

Copy the example config and fill in your credentials:

```bash
cd sharkonai
cp config.example.py config.py
```

Edit `config.py`:

```python
TELEGRAM_BOT_TOKEN = "your-bot-token-here"
AUTHORIZED_USER_ID = 123456789          # Your Telegram user ID
NVIDIA_API_KEY     = "nvapi-your-key"   # NVIDIA AI endpoint key
```

> **Tip:** Send `/start` to [@userinfobot](https://t.me/userinfobot) on Telegram to get your user ID.

### 4. Run

```bash
cd sharkonai
python main.py
```

You'll see the startup banner:

```
╔═══════════════════════════════════════════════════════════╗
║                      A I   v 4 . 0                        ║
║                                                           ║
║   🧠 Autonomous Brain • ⛓️ 25-Step Chains • 🔧 60+ Tools ║
║   🌐 Web Browsing • ⏰ Cron Scheduler • 🧬 Self-Evolving  ║
║   🤖 Self-Directing • 🎯 Goal Engine • 💬 Non-Blocking   ║
╚═══════════════════════════════════════════════════════════╝
```

Open your Telegram bot and start chatting!

---

## 💬 Usage Examples

| You say | SharkonAI does |
|---------|---------------|
| `What's my IP address?` | Runs a system command and reports the result |
| `Search for the latest Python 3.13 release notes` | `web_search` → reads highlights from snippet |
| `Browse https://example.com and summarize it` | `web_browse` → returns clean text summary |
| `Take a screenshot of google.com` | `web_screenshot` → sends the photo to Telegram |
| `Remind me every day at 9am to check emails` | `schedule_task` — daily reminder, fires automatically |
| `Check CPU usage every 30 minutes and report` | `schedule_task` — recurring system monitor |
| `Run a disk cleanup every sunday at 2am` | `schedule_task` — weekly maintenance task |
| `Show me all scheduled tasks` | `list_scheduled_tasks` — lists with next run times |
| `Cancel the CPU monitor task` | `cancel_scheduled_task` — by label |
| `Find all email addresses on https://example.com` | `web_extract_data` → returns list of emails |
| `Login to site X, fill form Y, submit` | `web_interact` with actions JSON |
| `Take a desktop screenshot` | Captures the screen and sends the image |
| `Open Chrome and go to github.com` | Launches Chrome, types the URL, presses Enter (multi-step) |
| `Create a PDF report of my system info` | Gathers system info → generates a PDF → sends it to you |
| `Remember that my server IP is 192.168.1.100` | Stores it in permanent knowledge base |
| `What was my server IP?` | Recalls it from memory |
| `Read the file C:\data\report.csv` | Reads and sends the file contents |
| `Download https://example.com/data.json` | Downloads the file to `media/downloads/` |
| `stop` | **Immediately cancels** whatever task is running |
| *(send a voice message)* | Transcribes it and processes as text |

### Multi-Step Chains

SharkonAI can autonomously execute up to **25 steps** for complex tasks. For example:

> **You:** *"Search for the top 5 Python web frameworks, browse each homepage, and create a comparison PDF"*

SharkonAI will:
1. `web_search` — Find the top 5 frameworks
2. `web_browse` — Read each homepage (×5 steps)
3. `create_pdf` — Generate the comparison report
4. `send_file` — Deliver it to you

All automatically, with real-time status updates in chat.

### Stopping a Task

At any point during a multi-step operation, send:

```
stop
```

The current tool execution is cancelled immediately and you get a confirmation:

> 🛑 Stopping the current task...

---

## ⚙️ Configuration Reference

All settings live in `sharkonai/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Your Telegram bot token |
| `AUTHORIZED_USER_ID` | — | Your Telegram user ID (only this user can interact) |
| `NVIDIA_API_KEY` | — | NVIDIA AI endpoint API key |
| `NVIDIA_MODEL` | `moonshotai/kimi-k2-instruct` | LLM model to use |
| `MAX_CHAIN_STEPS` | `25` | Maximum auto-continuation steps per task |
| `MAX_TOKENS` | `4096` | Max tokens per LLM response |
| `CREATIVE_TEMPERATURE` | `0.7` | Temperature for creative/conversational tasks |
| `PRECISE_TEMPERATURE` | `0.2` | Temperature for tool execution |
| `CMD_TIMEOUT` | `180` | Seconds timeout for shell commands |
| `TOOL_TIMEOUT` | `120` | Seconds timeout per tool invocation |
| `COGNITION_INTERVAL_SECONDS` | `60` | Background cognition loop interval |
| `SKILL_EVOLUTION_ENABLED` | `True` | Allow autonomous skill creation |
| `SKILL_EVOLUTION_INTERVAL` | `30` | Cognition ticks between evolution checks |
| `AUTONOMOUS_ENABLED` | `True` | Enable self-directed autonomous operation |
| `AUTONOMOUS_CYCLE_SECONDS` | `120` | Autonomous engine cycle interval |
| `MAX_CONTEXT_MESSAGES` | `50` | Messages included in LLM context |
| `VOICE_LANGUAGES` | `["fr-FR", "en-US", "ar-SA"]` | Speech recognition language priority |
| `WATCHDOG_CHECK_INTERVAL` | `30` | Health check interval (seconds) |
| `MAX_RESTART_ATTEMPTS` | `5` | Max auto-restart attempts |

---

## 🔌 Dependencies

```
aiogram>=3.4.0          # Telegram bot framework (v3, async)
openai>=1.12.0          # NVIDIA AI endpoint (OpenAI-compatible)
aiohttp>=3.9.0          # Async HTTP client
aiofiles>=23.0.0        # Async file I/O
pyautogui>=0.9.54       # GUI automation (mouse, keyboard)
pyperclip>=1.8.0        # System clipboard access
Pillow>=10.0.0          # Image processing
opencv-python>=4.8.0    # Webcam capture
fpdf2>=2.7.0            # PDF generation
SpeechRecognition>=3.10.0  # Voice-to-text
pydub>=0.25.1           # Audio format conversion
playwright>=1.40.0      # Headless browser (web browsing skill)
```

**System requirements:**
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) — for screen vision / OCR tools
- [ffmpeg](https://ffmpeg.org/download.html) — for voice message audio conversion
- Chromium (via `playwright install chromium`) — for web browsing / screenshot / form automation

---

## ⏰ Scheduled Tasks

Schedule **any task** in natural language — the bot executes it automatically and delivers results to Telegram.

### Supported schedule formats

| Format | Example | Type |
|--------|---------|------|
| Exact date/time | `"2025-06-01 14:30"` | One-shot |
| Every N minutes | `"every 30 minutes"` | Interval |
| Every N hours | `"every 2 hours"` | Interval |
| Daily at a time | `"every day at 09:00"` | Daily |
| Weekly on a weekday | `"every monday at 09:00"` | Weekly |
| Cron expression | `"cron: 0 9 * * 1-5"` | Cron |

### Examples

```
You: Check my CPU and RAM every 30 minutes and report
Bot: schedule_task("Get CPU usage and RAM usage and report them", "every 30 minutes", "system-monitor")
     → Task scheduled! Next run in 30 minutes. Results sent to Telegram automatically.

You: Take a screenshot of my desktop every morning at 8am
Bot: schedule_task("Take a screenshot of the desktop and send it", "every day at 08:00", "morning-shot")

You: Search for Bitcoin price every hour
Bot: schedule_task("Search for current Bitcoin price and report it", "every 1 hour", "btc-tracker")

You: Show me all scheduled tasks
Bot: list_scheduled_tasks()
     → #1 [interval] "system-monitor" — next: 2025-06-01 10:30:00
        #2 [daily]    "morning-shot"   — next: 2025-06-02 08:00:00
        #3 [interval] "btc-tracker"    — next: 2025-06-01 11:00:00

You: Cancel the BTC tracker
Bot: cancel_scheduled_task("btc-tracker") → Done.
```

Scheduled tasks persist across restarts (stored in SQLite). They fire every 30 seconds of wall-clock checking.

---

## 🌐 Web Browsing

SharkonAI can **search, read, screenshot, and automate** any website using a built-in Playwright browser.

### Decision tree — fastest path first

```
Need info online?         → web_search        (fastest — no browser needed)
Need to read a page?      → web_browse        (plain HTTP by default)
JS-heavy page?            → web_browse use_js=true
User wants to see a page? → web_screenshot    (Chromium → photo to Telegram)
Need emails/prices/links? → web_extract_data  (smart regex, no JS)
Fill a form / multi-step? → web_interact      (full Playwright automation)
```

### Example: search & browse

```
You:  What's the current price of Bitcoin?
Bot:  web_search("bitcoin price usd") → reads snippet → answers instantly
```

```
You:  Summarize the Wikipedia page for Python programming language
Bot:  web_browse("https://en.wikipedia.org/wiki/Python_(programming_language)")
      → returns clean text summary
```

### Example: form automation

```json
[
  {"type": "goto",  "value": "https://example.com/login"},
  {"type": "fill",  "selector": "#email",    "value": "you@example.com"},
  {"type": "fill",  "selector": "#password", "value": "secret"},
  {"type": "click", "selector": "button[type=submit]"},
  {"type": "extract", "selector": ".welcome-msg", "extract_as": "greeting"}
]
```

---

## 🧬 Skill Evolution

SharkonAI can **create its own new tools** at runtime. When the AI encounters a task it doesn't have a tool for, it can:

1. **Design** a new skill with full tool definitions
2. **Write** the Python code and save it to `skills_by_Sharkon/`
3. **Hot-load** the skill immediately — no restart required
4. **Use** the new tool in the current task chain

The cognition loop also periodically reviews the AI's capabilities and autonomously creates skills it thinks would be useful.

All AI-created skills follow the same interface as built-in skills:

```python
# skills_by_Sharkon/my_new_skill.py
SKILL_DEFINITIONS = [
    {
        "name": "my_new_tool",
        "description": "Does something useful",
        "parameters": {"param1": "Description of param1"}
    }
]

async def my_new_tool(param1: str) -> dict:
    # ... implementation ...
    return {"success": True, "stdout": "Result here"}

SKILL_MAP = {"my_new_tool": my_new_tool}
```

---

## 📋 Subsystem Overview

| Subsystem | File | Purpose |
|-----------|------|---------|
| **Main** | `main.py` | Entry point, starts all subsystems, graceful shutdown |
| **Brain** | `brain.py` | LLM reasoning, JSON decisions, task classification, API circuit breaker |
| **Memory** | `memory.py` | SQLite persistence (messages, actions, knowledge, tasks) |
| **Telegram** | `telegram_handler.py` | Bot interface, tool chains, stop command, voice/file handling |
| **Tools** | `tools.py` | Tool dispatch with timeout, result coercion |
| **Skills** | `skills/` | 13 built-in skill modules + dynamic loader |
| **Autonomous** | `autonomous_engine.py` | Self-directed goal generation & execution |
| **Scheduler** | `scheduler_engine.py` | Cron-like background task scheduling |
| **Cognition** | `cognition_loop.py` | Background health checks, stats, skill evolution |
| **Watchdog** | `watchdog.py` | Auto-restart, heartbeat monitoring |
| **Logger** | `logger.py` | Rotating file + console logging |
| **Config** | `config.py` | All settings and credentials |

---

## 🔒 Security

- **Single-user authorization** — only one Telegram user ID can interact with the bot
- All unauthorized access attempts are logged
- Credentials are stored in `config.py` (excluded from version control)
- The bot runs locally on your machine — no cloud servers required
- **Fail-safe GUI** — PyAutoGUI fail-safe enabled (move mouse to top-left corner to abort)
- Command timeouts prevent runaway processes

> ⚠️ **Warning:** SharkonAI has full access to your system (commands, files, GUI, web). Only run it on machines you trust and keep your bot token / config private.

---

## 🗺️ Roadmap

- [x] Multi-step tool chaining (up to 25 steps)
- [x] Voice message transcription
- [x] Self-evolving skill creation
- [x] Task stop/cancel command
- [x] **Web browsing skill** (Playwright integration — search, browse, screenshot, forms)
- [x] Autonomous engine (self-directed goal system)
- [x] API circuit breaker (instant 403 detection, no wasted retries)
- [x] **Scheduled tasks & cron automation** (once, interval, daily, weekly, cron expressions)
- [ ] Multi-user support with role-based access
- [ ] Plugin marketplace for community skills
- [ ] Linux / macOS GUI automation support
- [ ] Image generation / editing tools
- [ ] Text-to-Speech voice replies
- [ ] Email sending and reading

---

<p align="center">
  <b>Built with 🦈 by the SharkonAI team</b><br/>
  <sub>Autonomous AI that sees, thinks, acts, and evolves.</sub>
</p>
