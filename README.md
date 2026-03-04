
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
  <img src="https://img.shields.io/badge/v3.0-Stable-brightgreen?style=flat-square" alt="Version"/>
  <img src="https://img.shields.io/badge/Tools-51+-blue?style=flat-square" alt="Tools"/>
  <img src="https://img.shields.io/badge/Chain_Steps-25-orange?style=flat-square" alt="Chain Steps"/>
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Platform"/>
  <img src="https://img.shields.io/badge/Voice-Recognition-FF6F00?style=flat-square" alt="Voice"/>
  <img src="https://img.shields.io/badge/Self--Evolving-🧬-purple?style=flat-square" alt="Self-Evolving"/>
</p>

---

## 🌊 Overview

**SharkonAI** is a fully autonomous, self-recovering AI agent that lives in Telegram. It combines a powerful LLM brain (NVIDIA-hosted models) with **51+ executable tools** to perform virtually anything — from running system commands and writing code, to controlling your desktop GUI with pixel-perfect precision, to **creating its own new skills at runtime**.

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

</td>
<td width="50%" valign="top">

### 🔧 51+ Executable Tools
- **System**: CMD, PowerShell, Python execution
- **Files**: Read, write, append, search, create PDFs, send files
- **GUI**: Mouse, keyboard, drag & drop, screenshots, OCR vision
- **Network**: HTTP requests, file downloads
- **Memory**: Permanent knowledge storage & recall
- **Media**: Webcam capture, image & file delivery
- **Voice**: Speech-to-text transcription
- **Meta**: Self-evolving skill creation system

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 👁️ Screen Vision (OCR)
- Full-screen or regional OCR analysis via Tesseract
- Click, hover, drag, and find any visible text element
- Pixel-perfect drag-and-drop GUI automation
- Smart text selection (word, line, range, all)
- Active window detection
- Dual OCR engine: Tesseract + Windows WinRT fallback

</td>
<td width="50%" valign="top">

### 🎤 Voice Recognition
- Auto-transcription of Telegram voice messages
- Google Web Speech API (free, no key needed)
- Supports **50+ languages** (en, fr, ar, es, de, zh, ja…)
- OGG / MP3 / M4A / FLAC / WebM support via ffmpeg
- Windows System.Speech offline fallback
- Voice messages processed as if user typed the text

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📚 Persistent Memory
- SQLite-backed message & action history (WAL mode)
- Knowledge base with category/key/value + confidence scores
- Task tracking for multi-step operations with progress
- Conversation summarization for long-term context
- Full-text search across messages and knowledge
- System state management (heartbeat, version, stats)

</td>
<td width="50%" valign="top">

### 🧬 Self-Evolving Skills
- **Creates its own new tools at runtime** — saved to `skills_by_Sharkon/`
- Hot-reloads new skills instantly without restart
- Can read, update, and delete its AI-created skills
- Periodic autonomous skill evolution via cognition loop
- Full skill inventory and introspection
- Built-in vs AI-created skill separation

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🛡️ Self-Recovery
- **Watchdog** monitors all subsystems continuously
- Auto-restarts crashed cognition loops
- Stale heartbeat detection and alerting
- Graceful shutdown with OS signal handling
- Restart attempt tracking with configurable limits

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
│  NVIDIA AI API   │  │  51+ tools across 11 skill modules   │
│  Chain-of-thought│  │  + dynamically created AI skills      │
│  JSON decisions  │  │  Timeout protection per tool call     │
└────────┬─────────┘  └──────────────────────────────────────┘
         │
         ▼
┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐
│  Memory (SQLite) │  │  Cognition Loop  │  │    Watchdog    │
│  Messages/Actions│  │  Heartbeat       │  │  Health checks │
│  Knowledge Base  │  │  System health   │  │  Auto-restart  │
│  Tasks/Summaries │  │  Skill evolution │  │  Stale detect  │
└──────────────────┘  └──────────────────┘  └────────────────┘
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

### 2. Configure

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

### 3. Run

```bash
cd sharkonai
python main.py
```

You'll see the startup banner:

```
╔═══════════════════════════════════════════════════════════╗
║                      A I   v 3 . 0                        ║
║                                                           ║
║   🧠 Enhanced Brain • ⛓️ 25-Step Chains • 🔧 51+ Tools   ║
║   🧬 Self-Evolving • 📚 Memory • 🛡️ Self-Recovery       ║
╚═══════════════════════════════════════════════════════════╝
```

Open your Telegram bot and start chatting!

---

## 💬 Usage Examples

| You say | SharkonAI does |
|---------|---------------|
| `What's my IP address?` | Runs a system command and reports the result |
| `Take a screenshot` | Captures the screen and sends the image |
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

> **You:** *"Find all .py files in my project, count the lines of code in each, and create a summary PDF"*

SharkonAI will:
1. `find_files` — Search for `.py` files
2. `read_file` — Read each file (multiple steps)
3. `run_python` — Count lines
4. `create_pdf` — Generate the report
5. `send_file` — Deliver it to you

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
```

**System requirements:**
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) — for screen vision / OCR tools
- [ffmpeg](https://ffmpeg.org/download.html) — for voice message audio conversion

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
| **Brain** | `brain.py` | LLM reasoning, JSON decisions, task classification |
| **Memory** | `memory.py` | SQLite persistence (messages, actions, knowledge, tasks) |
| **Telegram** | `telegram_handler.py` | Bot interface, tool chains, stop command, voice/file handling |
| **Tools** | `tools.py` | Tool dispatch with timeout, result coercion |
| **Skills** | `skills/` | 11 built-in skill modules + dynamic loader |
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

> ⚠️ **Warning:** SharkonAI has full access to your system (commands, files, GUI). Only run it on machines you trust and keep your bot token / config private.

---

## 🗺️ Roadmap

- [x] Multi-step tool chaining (up to 25 steps)
- [x] Voice message transcription
- [x] Self-evolving skill creation
- [x] Task stop/cancel command
- [ ] Web browsing skill (Playwright/Selenium integration)
- [ ] Scheduled tasks and cron-like automation
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
