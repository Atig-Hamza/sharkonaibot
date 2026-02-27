"""
SharkonAI Tools — Enhanced
Dynamic tool execution system with expanded capabilities:
  • System commands, file I/O, directory operations
  • GUI automation (keyboard, mouse, screenshots)
  • Web/network tools (HTTP requests, downloads)
  • System info, process management
  • Clipboard, application launcher, wait/sleep
  • Python code execution sandbox
  • Audio transcription (speech-to-text)
"""

import asyncio
import json
import os
import platform
import re
import subprocess
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import pyautogui

from config import CONFIG
from logger import log

# PyAutoGUI safety settings
pyautogui.FAILSAFE = True       # Move mouse to top-left corner to abort
pyautogui.PAUSE = 0.1           # Small pause between actions for stability


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    image_path: str = ""  # If set, the telegram handler will send this as a photo
    file_path: str = ""   # If set, the telegram handler will send this as a document


# ── Tool Registry ────────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    # ── System Commands ──
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

    # ── File Creation & Sending ──
    {
        "name": "create_file",
        "description": (
            "Create a file (TXT, CSV, HTML, JSON, XML, MD, PY, JS, etc.) with the given content "
            "and SEND IT to the user as a document in Telegram. "
            "Use this when the user asks you to create/generate/write a file for them. "
            "The file is saved in the media folder and automatically sent to the chat. "
            "Supports ANY text-based file format."
        ),
        "parameters": {
            "filename": {
                "type": "string",
                "description": "The filename with extension (e.g., 'report.txt', 'data.csv', 'page.html', 'notes.md').",
            },
            "content": {
                "type": "string",
                "description": "The text content to write into the file.",
            },
            "caption": {
                "type": "string",
                "description": "Optional caption to display with the file in Telegram.",
            },
        },
    },
    {
        "name": "create_pdf",
        "description": (
            "Create a PDF document with the given title and content, then SEND IT to the user in Telegram. "
            "Use this when the user asks for a PDF report, document, letter, resume, etc. "
            "Supports multi-page documents with automatic page breaks. "
            "The PDF is saved in the media folder and automatically sent to the chat."
        ),
        "parameters": {
            "filename": {
                "type": "string",
                "description": "The PDF filename (e.g., 'report.pdf', 'resume.pdf'). Will add .pdf if missing.",
            },
            "title": {
                "type": "string",
                "description": "The document title displayed at the top of the PDF.",
            },
            "content": {
                "type": "string",
                "description": "The body text of the PDF. Use newlines for paragraphs. Use '## ' prefix for section headers.",
            },
            "caption": {
                "type": "string",
                "description": "Optional caption to display with the file in Telegram.",
            },
        },
    },
    {
        "name": "send_file",
        "description": (
            "Send any existing file to the user as a document in Telegram. "
            "Use this to send files that already exist on disk: downloads, generated files, logs, etc. "
            "Supports ALL file types (PDF, DOCX, ZIP, EXE, PY, TXT, etc.)."
        ),
        "parameters": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file to send.",
            },
            "caption": {
                "type": "string",
                "description": "Optional caption to display with the file.",
            },
        },
    },

    # ── File Operations ──
    {
        "name": "read_file",
        "description": (
            "Read the contents of a file on disk. "
            "Useful for inspecting scripts, logs, configuration files, etc. "
            "Supports reading partial files with start_line and end_line."
        ),
        "parameters": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file.",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional starting line number (1-indexed). Reads from beginning if omitted.",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional ending line number (1-indexed). Reads to end if omitted.",
            },
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file on disk. Creates the file if it doesn't exist, "
            "overwrites if it does. Creates parent directories automatically. "
            "Useful for creating scripts, saving data, writing config files, etc."
        ),
        "parameters": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file.",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file.",
            },
        },
    },
    {
        "name": "append_file",
        "description": (
            "Append content to an existing file (or create it). "
            "Useful for adding to logs, appending data, etc."
        ),
        "parameters": {
            "path": {
                "type": "string",
                "description": "Path to the file to append to.",
            },
            "content": {
                "type": "string",
                "description": "The content to append.",
            },
        },
    },
    {
        "name": "list_directory",
        "description": (
            "List files and folders in a directory with details (size, type). "
            "Defaults to the current working directory."
        ),
        "parameters": {
            "path": {
                "type": "string",
                "description": "Path to the directory to list. Defaults to '.'",
            }
        },
    },
    {
        "name": "find_files",
        "description": (
            "Search for files matching a pattern recursively in a directory. "
            "Uses glob patterns (e.g., '*.py', '**/*.txt'). "
            "Returns matching file paths."
        ),
        "parameters": {
            "directory": {
                "type": "string",
                "description": "The directory to search in.",
            },
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match files (e.g., '*.py', '**/*.log').",
            },
        },
    },

    # ── GUI Automation ──
    {
        "name": "type_text",
        "description": (
            "Type text using the keyboard, as if a human is typing. "
            "Simulates real keystrokes. The text is typed wherever the cursor is. "
            "Handles both ASCII and Unicode (Arabic, emoji, etc.) text."
        ),
        "parameters": {
            "text": {
                "type": "string",
                "description": "The text to type.",
            },
            "interval": {
                "type": "number",
                "description": "Seconds between each keystroke (default 0.03). Use 0 for instant.",
            },
        },
    },
    {
        "name": "press_key",
        "description": (
            "Press a single keyboard key or a sequence of keys. "
            "Examples: 'enter', 'tab', 'escape', 'space', 'backspace', 'delete', "
            "'up', 'down', 'left', 'right', 'f1'-'f12', 'home', 'end', etc."
        ),
        "parameters": {
            "key": {
                "type": "string",
                "description": "The key to press (e.g. 'enter', 'tab', 'escape', 'a', 'f5').",
            },
            "presses": {
                "type": "integer",
                "description": "Number of times to press the key (default 1).",
            },
        },
    },
    {
        "name": "hotkey",
        "description": (
            "Press a keyboard shortcut (multiple keys at once). "
            "Examples: ['ctrl', 'c'] for copy, ['ctrl', 'v'] for paste, "
            "['alt', 'tab'] switch windows, ['win', 'd'] show desktop."
        ),
        "parameters": {
            "keys": {
                "type": "array",
                "description": "List of keys to press simultaneously, e.g. ['ctrl', 'c'].",
            },
        },
    },
    {
        "name": "mouse_click",
        "description": (
            "Click the mouse at a specific screen position (x, y pixels). "
            "Supports left, right, and middle click, single/double/triple click."
        ),
        "parameters": {
            "x": {
                "type": "integer",
                "description": "X coordinate (pixels from left edge of screen).",
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate (pixels from top edge of screen).",
            },
            "button": {
                "type": "string",
                "description": "Mouse button: 'left' (default), 'right', or 'middle'.",
            },
            "clicks": {
                "type": "integer",
                "description": "Number of clicks (1=single, 2=double). Default 1.",
            },
        },
    },
    {
        "name": "mouse_move",
        "description": "Move the mouse cursor to a specific screen position.",
        "parameters": {
            "x": {"type": "integer", "description": "X coordinate."},
            "y": {"type": "integer", "description": "Y coordinate."},
            "duration": {
                "type": "number",
                "description": "Seconds for movement animation (0 = instant). Default 0.3.",
            },
        },
    },
    {
        "name": "mouse_scroll",
        "description": "Scroll the mouse wheel. Positive = up, negative = down.",
        "parameters": {
            "clicks": {
                "type": "integer",
                "description": "Scroll clicks. Positive = up, negative = down.",
            },
            "x": {"type": "integer", "description": "Optional X position."},
            "y": {"type": "integer", "description": "Optional Y position."},
        },
    },

    # ── High-Precision GUI Tools ──
    {
        "name": "drag_and_drop",
        "description": (
            "Drag from one screen position and drop at another with pixel-perfect precision. "
            "Use this to move files, rearrange items, resize windows, drag sliders, "
            "reorder list items, move objects in editors, etc. "
            "Supports adjustable speed for reliability."
        ),
        "parameters": {
            "start_x": {"type": "integer", "description": "X coordinate to start dragging from."},
            "start_y": {"type": "integer", "description": "Y coordinate to start dragging from."},
            "end_x": {"type": "integer", "description": "X coordinate to drop at."},
            "end_y": {"type": "integer", "description": "Y coordinate to drop at."},
            "duration": {
                "type": "number",
                "description": "Seconds for the drag movement (default 0.5). Slower = more reliable for precision tasks.",
            },
            "button": {
                "type": "string",
                "description": "Mouse button to use: 'left' (default), 'right', 'middle'.",
            },
        },
    },
    {
        "name": "drag_text",
        "description": (
            "Find text on screen using OCR and DRAG it to a target position or to another text. "
            "Perfect for drag-and-drop operations by text label instead of coordinates. "
            "Example: drag a file named 'report.pdf' to the 'Trash' icon."
        ),
        "parameters": {
            "source_text": {
                "type": "string",
                "description": "The text to find and start dragging from.",
            },
            "target_text": {
                "type": "string",
                "description": "Optional text to drag to. If not set, use target_x/target_y.",
            },
            "target_x": {"type": "integer", "description": "Optional X coordinate to drop at (if no target_text)."},
            "target_y": {"type": "integer", "description": "Optional Y coordinate to drop at (if no target_text)."},
            "duration": {
                "type": "number",
                "description": "Seconds for the drag movement (default 0.5).",
            },
        },
    },
    {
        "name": "mouse_hover",
        "description": (
            "Move the mouse to a position and HOLD it there (hover). "
            "Triggers hover effects like tooltips, dropdown menus, preview popups, etc. "
            "Use before clicking to reveal hidden UI elements."
        ),
        "parameters": {
            "x": {"type": "integer", "description": "X coordinate to hover at."},
            "y": {"type": "integer", "description": "Y coordinate to hover at."},
            "hover_time": {
                "type": "number",
                "description": "Seconds to hold the hover position (default 1.0). Longer for slow tooltips.",
            },
        },
    },
    {
        "name": "hover_text",
        "description": (
            "Find text on screen and hover over it to trigger tooltips, menus, or previews. "
            "Uses OCR to locate text, then moves the cursor there and waits."
        ),
        "parameters": {
            "text": {
                "type": "string",
                "description": "The text to find and hover over.",
            },
            "hover_time": {
                "type": "number",
                "description": "Seconds to hover (default 1.0).",
            },
        },
    },
    {
        "name": "select_text",
        "description": (
            "Select text on screen precisely. Works in three modes:\n"
            "1. click+shift+click: Click at start position, then shift+click at end position.\n"
            "2. triple_click: Triple-click at position to select entire line/paragraph.\n"
            "3. keyboard: Use Ctrl+A to select all, or shift+arrow keys for fine selection.\n"
            "After selection, you can use hotkey(['ctrl','c']) to copy."
        ),
        "parameters": {
            "mode": {
                "type": "string",
                "description": "Selection mode: 'range' (start→end positions), 'line' (triple-click), 'all' (Ctrl+A), 'word' (double-click).",
            },
            "start_x": {"type": "integer", "description": "X coordinate of selection start (for 'range' mode)."},
            "start_y": {"type": "integer", "description": "Y coordinate of selection start (for 'range' mode)."},
            "end_x": {"type": "integer", "description": "X coordinate of selection end (for 'range' mode)."},
            "end_y": {"type": "integer", "description": "Y coordinate of selection end (for 'range' mode)."},
            "x": {"type": "integer", "description": "X coordinate (for 'line', 'word' modes)."},
            "y": {"type": "integer", "description": "Y coordinate (for 'line', 'word' modes)."},
        },
    },
    {
        "name": "select_region",
        "description": (
            "Select a rectangular region on screen by click-dragging. "
            "Useful for selecting areas in image editors, spreadsheet cells, "
            "cropping regions, drawing selection boxes, etc."
        ),
        "parameters": {
            "start_x": {"type": "integer", "description": "Top-left X coordinate of selection rectangle."},
            "start_y": {"type": "integer", "description": "Top-left Y coordinate of selection rectangle."},
            "end_x": {"type": "integer", "description": "Bottom-right X coordinate of selection rectangle."},
            "end_y": {"type": "integer", "description": "Bottom-right Y coordinate of selection rectangle."},
            "duration": {
                "type": "number",
                "description": "Seconds for the drag (default 0.3). Slower = more precise.",
            },
        },
    },
    {
        "name": "scroll_smooth",
        "description": (
            "Scroll smoothly with fine-grained control. Unlike mouse_scroll, this scrolls "
            "in small incremental steps for precision. Good for navigating long documents, "
            "fine-positioning in video editors, adjusting values in sliders, etc."
        ),
        "parameters": {
            "direction": {
                "type": "string",
                "description": "Scroll direction: 'up', 'down', 'left', 'right'.",
            },
            "amount": {
                "type": "integer",
                "description": "Total scroll distance in clicks (default 5).",
            },
            "steps": {
                "type": "integer",
                "description": "Number of incremental steps to divide the scroll into (default 10). More steps = smoother.",
            },
            "x": {"type": "integer", "description": "Optional X position to scroll at."},
            "y": {"type": "integer", "description": "Optional Y position to scroll at."},
        },
    },
    {
        "name": "mouse_hold",
        "description": (
            "Press and HOLD a mouse button down, or RELEASE a held button. "
            "Use 'press' to hold down, 'release' to let go. "
            "Essential for drag operations, drawing, painting, holding buttons, etc."
        ),
        "parameters": {
            "action": {
                "type": "string",
                "description": "'press' to hold button down, 'release' to let go.",
            },
            "button": {
                "type": "string",
                "description": "Mouse button: 'left' (default), 'right', 'middle'.",
            },
            "x": {"type": "integer", "description": "Optional X position (moves there first)."},
            "y": {"type": "integer", "description": "Optional Y position (moves there first)."},
        },
    },
    {
        "name": "get_mouse_position",
        "description": (
            "Get the current mouse cursor position (X, Y coordinates) and the pixel color under it. "
            "Use this to know where the cursor is, or as a reference point for precision operations."
        ),
        "parameters": {},
    },
    {
        "name": "right_click_at",
        "description": (
            "Right-click at a specific position to open a context menu. "
            "Shortcut for mouse_click with button='right'. Commonly used for opening "
            "context menus in file explorer, editors, desktop, browsers, etc."
        ),
        "parameters": {
            "x": {"type": "integer", "description": "X coordinate to right-click at."},
            "y": {"type": "integer", "description": "Y coordinate to right-click at."},
        },
    },

    {
        "name": "screenshot",
        "description": (
            "Take a screenshot of the entire screen and SEND IT to the user as a photo in Telegram. "
            "Use this when the user asks to see the screen, or when you need to show the user what's happening. "
            "The screenshot will be automatically sent as an image in the chat."
        ),
        "parameters": {
            "filename": {
                "type": "string",
                "description": "Optional filename (default: 'screenshot.png').",
            },
        },
    },
    {
        "name": "send_image",
        "description": (
            "Send an image file to the user as a photo in Telegram. "
            "Use this to send any image: screenshots, downloaded images, generated charts, etc. "
            "The image will appear as a photo in the chat. Supports PNG, JPG, BMP, GIF."
        ),
        "parameters": {
            "path": {
                "type": "string",
                "description": "Absolute path to the image file to send.",
            },
            "caption": {
                "type": "string",
                "description": "Optional caption to display under the image.",
            },
        },
    },

    # ── Screen Vision / Analysis ──
    {
        "name": "analyze_screen",
        "description": (
            "Read and analyze ALL text visible on the screen using OCR. "
            "Returns every piece of text with its position (x, y coordinates). "
            "ESSENTIAL: Use this BEFORE clicking to understand what's on screen — "
            "buttons, menus, links, labels, input fields, etc. "
            "This is how you 'see' the screen and know where to click."
        ),
        "parameters": {
            "region": {
                "type": "string",
                "description": "Optional region to analyze: 'full' (default), 'top', 'bottom', 'left', 'right', 'center'.",
            },
        },
    },
    {
        "name": "click_text",
        "description": (
            "Find specific text on the screen and CLICK on it. "
            "Uses OCR to locate the text, then clicks at its position. "
            "Perfect for clicking buttons, links, menu items, tabs, etc. "
            "Example: click_text('Sign In'), click_text('Submit'), click_text('File')."
        ),
        "parameters": {
            "text": {
                "type": "string",
                "description": "The text to find and click on (e.g., 'Submit', 'OK', 'Settings').",
            },
            "button": {
                "type": "string",
                "description": "Mouse button: 'left' (default), 'right', or 'middle'.",
            },
            "occurrence": {
                "type": "integer",
                "description": "Which occurrence to click if text appears multiple times (1 = first, default).",
            },
        },
    },
    {
        "name": "find_text_on_screen",
        "description": (
            "Search for specific text on the screen and return its coordinates. "
            "Does NOT click — just tells you where the text is. "
            "Use this to plan clicks or verify elements are visible."
        ),
        "parameters": {
            "text": {
                "type": "string",
                "description": "The text to search for on screen.",
            },
        },
    },
    {
        "name": "get_active_window",
        "description": (
            "Get information about the currently active/focused window: "
            "title, process name, position, and size. "
            "Use this to know what application is in the foreground."
        ),
        "parameters": {},
    },

    # ── System Information ──
    {
        "name": "get_system_info",
        "description": (
            "Get detailed information about the system: OS, CPU, RAM, disk space, "
            "network interfaces, hostname, uptime, etc. No parameters needed."
        ),
        "parameters": {},
    },
    {
        "name": "get_running_processes",
        "description": (
            "List running processes with PID, name, and memory usage. "
            "Can filter by name to find specific processes."
        ),
        "parameters": {
            "filter_name": {
                "type": "string",
                "description": "Optional: filter processes by name (case-insensitive).",
            },
        },
    },
    {
        "name": "kill_process",
        "description": "Kill / terminate a process by its PID or name.",
        "parameters": {
            "target": {
                "type": "string",
                "description": "PID (number) or process name to kill.",
            },
        },
    },
    {
        "name": "open_application",
        "description": (
            "Open ANY Windows application by its common name. Has a built-in smart registry of 40+ apps. "
            "Examples: 'camera', 'notepad', 'chrome', 'firefox', 'edge', 'explorer', 'file explorer', "
            "'cmd', 'terminal', 'powershell', 'calculator', 'paint', 'word', 'excel', 'vscode', "
            "'task manager', 'settings', 'control panel', 'snipping tool', 'photos', 'mail', "
            "'spotify', 'discord', 'telegram', 'whatsapp', 'store', 'clock', 'calendar', "
            "'maps', 'weather', 'xbox', 'obs', 'vlc', 'media player', 'sound recorder', "
            "'screen recorder', 'magnifier', etc. Can also open files/folders/URLs directly."
        ),
        "parameters": {
            "target": {
                "type": "string",
                "description": "Application name (e.g., 'camera', 'chrome', 'notepad'), file path, or URL.",
            },
        },
    },
    {
        "name": "take_photo",
        "description": (
            "Take a photo using the computer's webcam/camera and SEND IT to the user in Telegram. "
            "The photo is captured instantly from the default camera device and sent as an image. "
            "Use this when the user asks to take a photo, selfie, or capture from camera."
        ),
        "parameters": {
            "filename": {
                "type": "string",
                "description": "Optional filename for the photo (default: 'camera_photo.jpg').",
            },
        },
    },

    # ── Network / Web ──
    {
        "name": "http_request",
        "description": (
            "Make an HTTP GET request to a URL and return the response body. "
            "Use this to fetch web pages, API data, check connectivity, etc."
        ),
        "parameters": {
            "url": {
                "type": "string",
                "description": "The URL to request.",
            },
            "headers": {
                "type": "object",
                "description": "Optional HTTP headers as key-value pairs.",
            },
        },
    },
    {
        "name": "download_file",
        "description": (
            "Download a file from a URL and save it to disk. "
            "Useful for downloading images, documents, installers, etc."
        ),
        "parameters": {
            "url": {
                "type": "string",
                "description": "The URL of the file to download.",
            },
            "save_path": {
                "type": "string",
                "description": "Where to save the downloaded file.",
            },
        },
    },

    # ── Clipboard ──
    {
        "name": "get_clipboard",
        "description": "Read the current contents of the system clipboard.",
        "parameters": {},
    },
    {
        "name": "set_clipboard",
        "description": "Set the system clipboard to the given text.",
        "parameters": {
            "text": {
                "type": "string",
                "description": "The text to copy to the clipboard.",
            },
        },
    },

    # ── Utility ──
    {
        "name": "wait",
        "description": "Wait/sleep for a specified number of seconds before continuing.",
        "parameters": {
            "seconds": {
                "type": "number",
                "description": "How many seconds to wait.",
            },
        },
    },
    {
        "name": "remember",
        "description": (
            "Store a fact, preference, or piece of knowledge in permanent memory. "
            "Use this to remember important information the user tells you, "
            "system configurations you've discovered, or anything useful for future reference."
        ),
        "parameters": {
            "category": {
                "type": "string",
                "description": "Category of the fact (e.g., 'user_preference', 'system_config', 'project_info').",
            },
            "key": {
                "type": "string",
                "description": "A short identifier for this fact (e.g., 'favorite_editor', 'python_version').",
            },
            "value": {
                "type": "string",
                "description": "The fact/information to remember.",
            },
        },
    },
    {
        "name": "recall",
        "description": (
            "Search your permanent memory for previously stored knowledge or facts. "
            "Use this to recall user preferences, past discoveries, system info, etc."
        ),
        "parameters": {
            "query": {
                "type": "string",
                "description": "What to search for in memory.",
            },
        },
    },
    {
        "name": "transcribe_audio",
        "description": (
            "Transcribe an audio file to text using speech recognition. "
            "Supports OGG, WAV, MP3, M4A, FLAC, and WebM formats. "
            "Uses Google Web Speech API (free, no key needed). "
            "Use this to convert voice messages, recordings, or any audio to text."
        ),
        "parameters": {
            "audio_path": {
                "type": "string",
                "description": "Path to the audio file to transcribe.",
            },
            "language": {
                "type": "string",
                "description": "Language code for recognition (default: 'en-US'). Examples: 'fr-FR', 'ar-SA', 'es-ES', 'de-DE'.",
            },
        },
    },
]


def get_tools_prompt() -> str:
    """Generate a system-prompt-friendly description of available tools."""
    lines = ["Available tools:\n"]
    for tool in TOOL_DEFINITIONS:
        params = ", ".join(
            f'{k} ({v["type"]}): {v["description"]}'
            for k, v in tool["parameters"].items()
        )
        lines.append(f'• {tool["name"]}: {tool["description"]}')
        if params:
            lines.append(f'  Parameters: {params}\n')
        else:
            lines.append(f'  Parameters: (none)\n')
    return "\n".join(lines)


# ── Tool Implementations ────────────────────────────────────────────────────

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
    # Wrap in powershell invocation
    command = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "{script}"'
    return await execute_cmd(command)


async def run_python(code: str) -> ToolResult:
    """Execute Python code in a subprocess."""
    log.info(f"Running Python code: {code[:80]}...")
    try:
        # Write code to a temp file and execute
        temp_path = os.path.join(os.path.dirname(__file__), "_temp_script.py")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(code)
        result = await execute_cmd(f'python "{temp_path}"')
        # Clean up temp file
        try:
            os.remove(temp_path)
        except OSError:
            pass
        return result
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=-1)


async def read_file(path: str, start_line: int = None, end_line: int = None) -> ToolResult:
    """Read file contents, optionally a specific line range."""
    log.info(f"Reading file: {path}")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            if start_line is not None or end_line is not None:
                lines = f.readlines()
                s = (start_line or 1) - 1
                e = end_line or len(lines)
                content = "".join(lines[s:e])
            else:
                content = f.read()
        max_len = 10000
        if len(content) > max_len:
            content = content[:max_len] + "\n... [file truncated]"
        return ToolResult(success=True, stdout=content, stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def write_file(path: str, content: str) -> ToolResult:
    """Write content to a file."""
    log.info(f"Writing file: {path}")
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return ToolResult(
            success=True,
            stdout=f"Successfully wrote {len(content)} characters to {path}",
            stderr="", return_code=0,
        )
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def append_file(path: str, content: str) -> ToolResult:
    """Append content to a file."""
    log.info(f"Appending to file: {path}")
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return ToolResult(
            success=True,
            stdout=f"Appended {len(content)} characters to {path}",
            stderr="", return_code=0,
        )
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def list_directory(path: str = ".") -> ToolResult:
    """List directory contents with details."""
    log.info(f"Listing directory: {path}")
    try:
        entries = os.listdir(path)
        result_lines = []
        for entry in sorted(entries):
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                try:
                    count = len(os.listdir(full))
                    result_lines.append(f"[DIR]  {entry}/ ({count} items)")
                except PermissionError:
                    result_lines.append(f"[DIR]  {entry}/ (access denied)")
            else:
                size = os.path.getsize(full)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                result_lines.append(f"[FILE] {entry} ({size_str})")
        return ToolResult(
            success=True,
            stdout="\n".join(result_lines) if result_lines else "(empty directory)",
            stderr="", return_code=0,
        )
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def find_files(directory: str, pattern: str) -> ToolResult:
    """Search for files matching a glob pattern recursively."""
    log.info(f"Finding files: {pattern} in {directory}")
    try:
        import glob
        matches = glob.glob(os.path.join(directory, pattern), recursive=True)
        if matches:
            result = "\n".join(matches[:100])
            if len(matches) > 100:
                result += f"\n... and {len(matches) - 100} more"
            return ToolResult(success=True, stdout=result, stderr="", return_code=0)
        else:
            return ToolResult(success=True, stdout="No files found matching the pattern.", stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── GUI Automation Tools ─────────────────────────────────────────────────────

async def type_text(text: str, interval: float = 0.03) -> ToolResult:
    """Type text using the keyboard, simulating real keystrokes."""
    log.info(f"Typing text: {text[:80]}...")
    try:
        if text.isascii():
            pyautogui.typewrite(text, interval=interval)
        else:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)
        return ToolResult(success=True, stdout=f"Typed {len(text)} characters.", stderr="", return_code=0)
    except Exception as e:
        log.error(f"type_text error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def press_key(key: str, presses: int = 1) -> ToolResult:
    """Press a keyboard key one or more times."""
    log.info(f"Pressing key: {key} (x{presses})")
    try:
        pyautogui.press(key, presses=presses, interval=0.05)
        return ToolResult(success=True, stdout=f"Pressed '{key}' {presses} time(s).", stderr="", return_code=0)
    except Exception as e:
        log.error(f"press_key error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def hotkey(keys: list) -> ToolResult:
    """Press a keyboard shortcut (multiple keys simultaneously)."""
    log.info(f"Pressing hotkey: {'+'.join(keys)}")
    try:
        pyautogui.hotkey(*keys)
        return ToolResult(success=True, stdout=f"Pressed hotkey: {'+'.join(keys)}", stderr="", return_code=0)
    except Exception as e:
        log.error(f"hotkey error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_click(x: int, y: int, button: str = "left", clicks: int = 1) -> ToolResult:
    """Click the mouse at a specific screen position."""
    log.info(f"Mouse click: ({x}, {y}) button={button} clicks={clicks}")
    try:
        pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=0.1)
        return ToolResult(success=True, stdout=f"Clicked ({x}, {y}) with {button} ({clicks}x).", stderr="", return_code=0)
    except Exception as e:
        log.error(f"mouse_click error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_move(x: int, y: int, duration: float = 0.3) -> ToolResult:
    """Move the mouse cursor to a specific screen position."""
    log.info(f"Mouse move to: ({x}, {y})")
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return ToolResult(success=True, stdout=f"Moved mouse to ({x}, {y}).", stderr="", return_code=0)
    except Exception as e:
        log.error(f"mouse_move error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_scroll(clicks: int, x: int = None, y: int = None) -> ToolResult:
    """Scroll the mouse wheel."""
    pos_str = f"at ({x}, {y})" if x is not None and y is not None else "at current position"
    log.info(f"Mouse scroll: {clicks} clicks {pos_str}")
    try:
        if x is not None and y is not None:
            pyautogui.scroll(clicks, x=x, y=y)
        else:
            pyautogui.scroll(clicks)
        direction = "up" if clicks > 0 else "down"
        return ToolResult(success=True, stdout=f"Scrolled {direction} by {abs(clicks)} clicks {pos_str}.", stderr="", return_code=0)
    except Exception as e:
        log.error(f"mouse_scroll error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── High-Precision GUI Tools ────────────────────────────────────────────────

async def drag_and_drop(start_x: int, start_y: int, end_x: int, end_y: int,
                        duration: float = 0.5, button: str = "left") -> ToolResult:
    """Drag from one position to another with pixel-perfect precision."""
    log.info(f"Drag & drop: ({start_x},{start_y}) → ({end_x},{end_y}) duration={duration}s")
    try:
        # Move to start position first
        pyautogui.moveTo(start_x, start_y, duration=0.15)
        time.sleep(0.1)

        # Use pyautogui's built-in drag (handles press, move, release)
        # Calculate relative movement
        rel_x = end_x - start_x
        rel_y = end_y - start_y

        pyautogui.mouseDown(button=button)
        time.sleep(0.05)  # Brief hold before moving — prevents missing the grab

        # Smooth interpolated movement using multiple intermediate steps
        steps = max(int(duration * 60), 10)  # ~60 steps per second
        for i in range(1, steps + 1):
            t = i / steps
            # Ease-in-out for natural feeling drag
            t_smooth = t * t * (3 - 2 * t)  # Smoothstep
            ix = int(start_x + rel_x * t_smooth)
            iy = int(start_y + rel_y * t_smooth)
            pyautogui.moveTo(ix, iy, _pause=False)
            time.sleep(duration / steps)

        time.sleep(0.05)  # Tiny pause before release
        pyautogui.mouseUp(button=button)

        return ToolResult(
            success=True,
            stdout=f"✅ Dragged from ({start_x},{start_y}) to ({end_x},{end_y}) with {button} button.",
            stderr="", return_code=0,
        )
    except Exception as e:
        # Safety: always release the mouse
        try:
            pyautogui.mouseUp(button=button)
        except Exception:
            pass
        log.error(f"drag_and_drop error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def drag_text(source_text: str, target_text: str = None,
                    target_x: int = None, target_y: int = None,
                    duration: float = 0.5) -> ToolResult:
    """Find text on screen using OCR and drag it to a target."""
    log.info(f"Drag text: '{source_text}' → '{target_text or f'({target_x},{target_y})'}")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot())

        if results is None:
            return ToolResult(
                success=False, stdout="",
                stderr="OCR unavailable — cannot locate text for dragging. Use drag_and_drop with coordinates.",
                return_code=1,
            )

        # Find source text
        source_match = None
        for r in results:
            if source_text.lower() in r["text"].lower():
                source_match = r
                break

        if not source_match:
            visible = [r["text"] for r in results if len(r["text"]) > 1][:20]
            return ToolResult(
                success=False, stdout="",
                stderr=f"Source text '{source_text}' not found. Visible: {', '.join(visible)}",
                return_code=1,
            )

        sx, sy = source_match["center_x"], source_match["center_y"]

        # Determine target position
        if target_text:
            target_match = None
            for r in results:
                if target_text.lower() in r["text"].lower():
                    target_match = r
                    break
            if not target_match:
                return ToolResult(
                    success=False, stdout="",
                    stderr=f"Target text '{target_text}' not found on screen.",
                    return_code=1,
                )
            tx, ty = target_match["center_x"], target_match["center_y"]
        elif target_x is not None and target_y is not None:
            tx, ty = target_x, target_y
        else:
            return ToolResult(
                success=False, stdout="",
                stderr="Must provide either target_text or both target_x and target_y.",
                return_code=1,
            )

        # Perform the drag
        return await drag_and_drop(sx, sy, tx, ty, duration=duration)

    except Exception as e:
        log.error(f"drag_text error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_hover(x: int, y: int, hover_time: float = 1.0) -> ToolResult:
    """Move to position and hold (hover) to trigger tooltips/menus."""
    log.info(f"Hovering at ({x}, {y}) for {hover_time}s")
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        await asyncio.sleep(hover_time)

        return ToolResult(
            success=True,
            stdout=f"✅ Hovered at ({x}, {y}) for {hover_time}s. Any tooltips/menus should now be visible.",
            stderr="", return_code=0,
        )
    except Exception as e:
        log.error(f"mouse_hover error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def hover_text(text: str, hover_time: float = 1.0) -> ToolResult:
    """Find text on screen and hover over it."""
    log.info(f"Hover over text: '{text}' for {hover_time}s")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot())

        if results is None:
            return ToolResult(
                success=False, stdout="",
                stderr="OCR unavailable. Use mouse_hover with coordinates instead.",
                return_code=1,
            )

        text_lower = text.lower().strip()
        for r in results:
            if text_lower in r["text"].lower():
                return await mouse_hover(r["center_x"], r["center_y"], hover_time)

        visible = [r["text"] for r in results if len(r["text"]) > 1][:20]
        return ToolResult(
            success=False, stdout="",
            stderr=f"Text '{text}' not found. Visible: {', '.join(visible)}",
            return_code=1,
        )
    except Exception as e:
        log.error(f"hover_text error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def select_text(mode: str = "all", start_x: int = None, start_y: int = None,
                      end_x: int = None, end_y: int = None,
                      x: int = None, y: int = None) -> ToolResult:
    """Select text with various precision modes."""
    log.info(f"Selecting text: mode={mode}")
    try:
        if mode == "all":
            # Select all text (Ctrl+A)
            pyautogui.hotkey('ctrl', 'a')
            return ToolResult(success=True, stdout="✅ Selected all text (Ctrl+A).", stderr="", return_code=0)

        elif mode == "word":
            # Double-click to select word
            if x is None or y is None:
                return ToolResult(success=False, stdout="", stderr="'word' mode requires x, y coordinates.", return_code=1)
            pyautogui.click(x=x, y=y, clicks=2, interval=0.05)
            return ToolResult(success=True, stdout=f"✅ Selected word at ({x}, {y}) (double-click).", stderr="", return_code=0)

        elif mode == "line":
            # Triple-click to select line
            if x is None or y is None:
                return ToolResult(success=False, stdout="", stderr="'line' mode requires x, y coordinates.", return_code=1)
            pyautogui.click(x=x, y=y, clicks=3, interval=0.05)
            return ToolResult(success=True, stdout=f"✅ Selected line at ({x}, {y}) (triple-click).", stderr="", return_code=0)

        elif mode == "range":
            # Click at start, then shift+click at end
            if None in (start_x, start_y, end_x, end_y):
                return ToolResult(success=False, stdout="", stderr="'range' mode requires start_x, start_y, end_x, end_y.", return_code=1)
            pyautogui.click(x=start_x, y=start_y)
            time.sleep(0.1)
            pyautogui.keyDown('shift')
            time.sleep(0.05)
            pyautogui.click(x=end_x, y=end_y)
            time.sleep(0.05)
            pyautogui.keyUp('shift')
            return ToolResult(
                success=True,
                stdout=f"✅ Selected text range from ({start_x},{start_y}) to ({end_x},{end_y}).",
                stderr="", return_code=0,
            )

        else:
            return ToolResult(
                success=False, stdout="",
                stderr=f"Unknown selection mode '{mode}'. Use: 'all', 'word', 'line', or 'range'.",
                return_code=1,
            )
    except Exception as e:
        try:
            pyautogui.keyUp('shift')  # Safety release
        except Exception:
            pass
        log.error(f"select_text error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def select_region(start_x: int, start_y: int, end_x: int, end_y: int,
                        duration: float = 0.3) -> ToolResult:
    """Select a rectangular region by click-dragging."""
    log.info(f"Selecting region: ({start_x},{start_y}) → ({end_x},{end_y})")
    try:
        return await drag_and_drop(start_x, start_y, end_x, end_y, duration=duration)
    except Exception as e:
        log.error(f"select_region error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def scroll_smooth(direction: str = "down", amount: int = 5, steps: int = 10,
                        x: int = None, y: int = None) -> ToolResult:
    """Scroll smoothly in small incremental steps for precision."""
    log.info(f"Smooth scroll: {direction} amount={amount} steps={steps}")
    try:
        # Move to target position if specified
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.1)

        if direction in ("up", "down"):
            click_val = amount if direction == "up" else -amount
            per_step = max(1, abs(click_val) // steps)
            sign = 1 if click_val > 0 else -1

            scrolled = 0
            for _ in range(steps):
                remaining = abs(click_val) - scrolled
                if remaining <= 0:
                    break
                scroll_now = min(per_step, remaining)
                pyautogui.scroll(sign * scroll_now)
                scrolled += scroll_now
                await asyncio.sleep(0.03)

        elif direction in ("left", "right"):
            # Horizontal scrolling via Win32 API
            try:
                import ctypes
                user32 = ctypes.windll.user32
                # WM_HSCROLL: SB_LINELEFT=0, SB_LINERIGHT=1
                hwnd = user32.GetForegroundWindow()
                WM_HSCROLL = 0x0114
                SB_LINELEFT = 0
                SB_LINERIGHT = 1
                scroll_cmd = SB_LINERIGHT if direction == "right" else SB_LINELEFT

                for _ in range(amount):
                    user32.PostMessageW(hwnd, WM_HSCROLL, scroll_cmd, 0)
                    await asyncio.sleep(0.03)
            except Exception:
                # Fallback: shift+scroll for horizontal scrolling (works in many apps)
                import pyautogui
                click_val = -amount if direction == "left" else amount
                pyautogui.keyDown('shift')
                time.sleep(0.05)
                pyautogui.scroll(click_val)
                pyautogui.keyUp('shift')
        else:
            return ToolResult(success=False, stdout="", stderr=f"Invalid direction '{direction}'. Use: up, down, left, right.", return_code=1)

        pos_str = f" at ({x},{y})" if x is not None and y is not None else ""
        return ToolResult(
            success=True,
            stdout=f"✅ Scrolled {direction} by {amount} (in {steps} smooth steps){pos_str}.",
            stderr="", return_code=0,
        )
    except Exception as e:
        try:
            pyautogui.keyUp('shift')  # Safety
        except Exception:
            pass
        log.error(f"scroll_smooth error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_hold(action: str = "press", button: str = "left",
                     x: int = None, y: int = None) -> ToolResult:
    """Press and hold or release a mouse button."""
    log.info(f"Mouse hold: {action} {button} at ({x},{y})")
    try:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.1)

        if action == "press":
            pyautogui.mouseDown(button=button)
            pos = pyautogui.position()
            return ToolResult(
                success=True,
                stdout=f"✅ {button.capitalize()} button held DOWN at ({pos.x}, {pos.y}). Use mouse_hold(action='release') to let go.",
                stderr="", return_code=0,
            )
        elif action == "release":
            pyautogui.mouseUp(button=button)
            pos = pyautogui.position()
            return ToolResult(
                success=True,
                stdout=f"✅ {button.capitalize()} button RELEASED at ({pos.x}, {pos.y}).",
                stderr="", return_code=0,
            )
        else:
            return ToolResult(success=False, stdout="", stderr=f"Unknown action '{action}'. Use 'press' or 'release'.", return_code=1)
    except Exception as e:
        log.error(f"mouse_hold error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def get_mouse_position() -> ToolResult:
    """Get current mouse position and pixel color under cursor."""
    log.info("Getting mouse position...")
    try:
        pos = pyautogui.position()
        try:
            pixel = pyautogui.pixel(pos.x, pos.y)
            color_str = f"RGB({pixel[0]}, {pixel[1]}, {pixel[2]}) / #{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}"
        except Exception:
            color_str = "(could not read pixel color)"

        screen_w, screen_h = pyautogui.size()
        return ToolResult(
            success=True,
            stdout=(
                f"Mouse position: ({pos.x}, {pos.y})\n"
                f"Screen size: {screen_w} x {screen_h}\n"
                f"Pixel color: {color_str}\n"
                f"Relative position: ({pos.x / screen_w * 100:.1f}%, {pos.y / screen_h * 100:.1f}%)"
            ),
            stderr="", return_code=0,
        )
    except Exception as e:
        log.error(f"get_mouse_position error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def right_click_at(x: int, y: int) -> ToolResult:
    """Right-click at a position to open context menu."""
    log.info(f"Right-clicking at ({x}, {y})")
    try:
        pyautogui.click(x=x, y=y, button='right')
        return ToolResult(
            success=True,
            stdout=f"✅ Right-clicked at ({x}, {y}). Context menu should now be visible.",
            stderr="", return_code=0,
        )
    except Exception as e:
        log.error(f"right_click_at error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def screenshot(filename: str = "screenshot.png") -> ToolResult:
    """Take a screenshot of the entire screen and send it as a photo."""
    log.info(f"Taking screenshot: {filename}")
    try:
        filepath = os.path.join(CONFIG.MEDIA_DIR, filename)
        img = pyautogui.screenshot()
        img.save(filepath)
        return ToolResult(
            success=True,
            stdout=f"Screenshot saved to: {filepath}",
            stderr="", return_code=0,
            image_path=filepath,  # Signal to send this as a photo
        )
    except Exception as e:
        log.error(f"screenshot error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── System Information Tools ────────────────────────────────────────────────

async def get_system_info() -> ToolResult:
    """Get comprehensive system information."""
    log.info("Getting system info...")
    try:
        info_lines = [
            f"OS: {platform.system()} {platform.release()} ({platform.version()})",
            f"Machine: {platform.machine()}",
            f"Processor: {platform.processor()}",
            f"Hostname: {platform.node()}",
            f"Python: {platform.python_version()}",
        ]

        # Disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            info_lines.append(
                f"Disk (C:): {used / (1024**3):.1f} GB used / {total / (1024**3):.1f} GB total "
                f"({free / (1024**3):.1f} GB free)"
            )
        except Exception:
            pass

        # RAM (via PowerShell on Windows)
        try:
            proc = subprocess.run(
                ['powershell', '-Command',
                 "(Get-CimInstance Win32_OperatingSystem | "
                 "Select-Object TotalVisibleMemorySize, FreePhysicalMemory | "
                 "ConvertTo-Json)"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0:
                mem = json.loads(proc.stdout)
                total_mb = int(mem.get("TotalVisibleMemorySize", 0)) / 1024
                free_mb = int(mem.get("FreePhysicalMemory", 0)) / 1024
                info_lines.append(f"RAM: {total_mb - free_mb:.0f} MB used / {total_mb:.0f} MB total ({free_mb:.0f} MB free)")
        except Exception:
            pass

        # Screen resolution
        try:
            w, h = pyautogui.size()
            info_lines.append(f"Screen: {w}x{h}")
        except Exception:
            pass

        return ToolResult(success=True, stdout="\n".join(info_lines), stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def get_running_processes(filter_name: str = None) -> ToolResult:
    """List running processes, optionally filtered by name."""
    log.info(f"Getting running processes (filter: {filter_name})")
    try:
        cmd = 'powershell.exe -NoProfile -Command "Get-Process'
        if filter_name:
            cmd += f" | Where-Object {{$_.ProcessName -like '*{filter_name}*'}}"
        cmd += " | Sort-Object -Property WS -Descending | Select-Object -First 40 PID, ProcessName, @{N='Memory(MB)';E={[math]::Round($_.WS/1MB,1)}} | Format-Table -AutoSize"
        cmd += '"'
        return await execute_cmd(cmd)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def kill_process(target: str) -> ToolResult:
    """Kill a process by PID or name."""
    log.info(f"Killing process: {target}")
    try:
        if target.isdigit():
            cmd = f'taskkill /PID {target} /F'
        else:
            cmd = f'taskkill /IM {target} /F'
        return await execute_cmd(cmd)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── Smart Windows App Registry ──────────────────────────────────────────────

WINDOWS_APP_REGISTRY = {
    # Built-in Windows Apps (UWP / Store apps)
    "camera": "start microsoft.windows.camera:",
    "webcam": "start microsoft.windows.camera:",
    "photos": "start microsoft.photos:",
    "calculator": "start calculator:",
    "calc": "start calculator:",
    "calendar": "start outlookcal:",
    "clock": "start ms-clock:",
    "alarms": "start ms-clock:",
    "mail": "start outlookmail:",
    "maps": "start bingmaps:",
    "weather": "start bingweather:",
    "store": "start ms-windows-store:",
    "microsoft store": "start ms-windows-store:",
    "settings": "start ms-settings:",
    "sound settings": "start ms-settings:sound",
    "wifi settings": "start ms-settings:network-wifi",
    "bluetooth settings": "start ms-settings:bluetooth",
    "display settings": "start ms-settings:display",
    "snipping tool": "start snippingtool",
    "snip": "start snippingtool",
    "screen recorder": "start ms-screenclip:",
    "magnifier": "start magnify",
    "xbox": "start xbox:",
    "media player": "start mswindowsmusic:",
    "groove music": "start mswindowsmusic:",
    "movies": "start mswindowsvideo:",
    "voice recorder": "start windowssoundrecorder:",
    "sound recorder": "start windowssoundrecorder:",
    "feedback": "start feedback-hub:",
    "sticky notes": "start ms-stickynotes:",
    "tips": "start ms-get-started:",

    # Classic Windows Programs
    "notepad": "notepad",
    "paint": "mspaint",
    "wordpad": "wordpad",
    "task manager": "taskmgr",
    "taskmgr": "taskmgr",
    "control panel": "control",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "wt",
    "windows terminal": "wt",
    "powershell": "powershell",
    "file explorer": "explorer",
    "explorer": "explorer",
    "regedit": "regedit",
    "device manager": "devmgmt.msc",
    "disk management": "diskmgmt.msc",
    "services": "services.msc",
    "event viewer": "eventvwr.msc",
    "system info": "msinfo32",
    "remote desktop": "mstsc",
    "performance monitor": "perfmon",
    "resource monitor": "resmon",
    "character map": "charmap",
    "on-screen keyboard": "osk",

    # Browsers
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "firefox": "start firefox",
    "edge": "start msedge",
    "microsoft edge": "start msedge",
    "brave": "start brave",
    "opera": "start opera",

    # Popular Third-Party Apps
    "vscode": "code",
    "visual studio code": "code",
    "vs code": "code",
    "word": "start winword",
    "excel": "start excel",
    "powerpoint": "start powerpnt",
    "outlook": "start outlook",
    "teams": "start msteams:",
    "spotify": "start spotify:",
    "discord": "start discord:",
    "telegram": "start tg:",
    "whatsapp": "start whatsapp:",
    "vlc": "start vlc",
    "obs": "start obs64",
    "obs studio": "start obs64",
    "steam": "start steam:",
    "zoom": "start zoommtg:",
    "skype": "start skype:",
    "7zip": "start 7zFM",
    "winrar": "start winrar",
    "git bash": "start git-bash",
}


async def open_application(target: str) -> ToolResult:
    """Open any application using smart name resolution."""
    log.info(f"Opening application: {target}")
    target_lower = target.lower().strip()

    # Check the smart registry first
    if target_lower in WINDOWS_APP_REGISTRY:
        cmd = WINDOWS_APP_REGISTRY[target_lower]
        log.info(f"Resolved '{target}' to command: {cmd}")
        result = await execute_cmd(cmd)
        if result.success or result.return_code == 0:
            return ToolResult(
                success=True,
                stdout=f"✅ Opened {target} successfully.",
                stderr="", return_code=0,
            )
        # If the registry command failed, fall through to other methods
        log.warning(f"Registry command failed for '{target}', trying alternatives...")

    # Try os.startfile (works for files, URLs, and some apps)
    try:
        os.startfile(target)
        return ToolResult(success=True, stdout=f"✅ Opened: {target}", stderr="", return_code=0)
    except Exception:
        pass

    # Try 'start' command
    result = await execute_cmd(f'start "" "{target}"')
    if result.success:
        return ToolResult(success=True, stdout=f"✅ Opened: {target}", stderr="", return_code=0)

    # Try direct execution
    result = await execute_cmd(target)
    if result.success:
        return ToolResult(success=True, stdout=f"✅ Opened: {target}", stderr="", return_code=0)

    # Try searching for the executable in PATH and common locations
    search_result = await execute_cmd(f'where {target_lower} 2>nul')
    if search_result.success and search_result.stdout.strip():
        exe_path = search_result.stdout.strip().split('\n')[0]
        try:
            os.startfile(exe_path)
            return ToolResult(success=True, stdout=f"✅ Opened: {exe_path}", stderr="", return_code=0)
        except Exception:
            pass

    return ToolResult(
        success=False, stdout="",
        stderr=f"Could not open '{target}'. It may not be installed or the name might be different.",
        return_code=1,
    )


# ── Webcam / Camera Tool ────────────────────────────────────────────────────

async def take_photo(filename: str = "camera_photo.jpg") -> ToolResult:
    """Capture a photo from the webcam and return it for sending."""
    log.info(f"Taking webcam photo: {filename}")
    filepath = os.path.join(CONFIG.MEDIA_DIR, filename)

    try:
        import cv2
    except ImportError:
        # OpenCV not installed — try to install it
        log.info("OpenCV not found, attempting to install...")
        install_result = await execute_cmd('pip install opencv-python')
        if not install_result.success:
            return ToolResult(
                success=False, stdout="",
                stderr="opencv-python is required for camera. Install failed: " + install_result.stderr,
                return_code=1,
            )
        import cv2

    try:
        # Open default camera (index 0)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # CAP_DSHOW is better on Windows
        if not cap.isOpened():
            # Try without DSHOW
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return ToolResult(
                success=False, stdout="",
                stderr="Could not open webcam. No camera detected or camera is in use by another application.",
                return_code=1,
            )

        # Let the camera warm up — read a few frames
        for _ in range(10):
            cap.read()
            await asyncio.sleep(0.05)

        # Capture the actual frame
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return ToolResult(
                success=False, stdout="",
                stderr="Failed to capture frame from webcam.",
                return_code=1,
            )

        # Save the image
        cv2.imwrite(filepath, frame)
        height, width = frame.shape[:2]

        size = os.path.getsize(filepath)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"

        return ToolResult(
            success=True,
            stdout=f"📸 Photo captured! Resolution: {width}x{height}, Size: {size_str}",
            stderr="", return_code=0,
            image_path=filepath,  # Auto-send as photo in Telegram
        )

    except Exception as e:
        log.error(f"take_photo error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Camera error: {e}", return_code=1)


# ── Screen Vision / OCR Tools ───────────────────────────────────────────────

def _get_tesseract():
    """Get pytesseract module with auto-detected Tesseract path."""
    try:
        import pytesseract

        # Auto-detect tesseract binary on Windows
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(os.environ.get("USERNAME", "")),
            r"C:\tools\Tesseract-OCR\tesseract.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return pytesseract

        # Try if it's already in PATH
        try:
            subprocess.run(
                ["tesseract", "--version"],
                capture_output=True, timeout=5,
            )
            return pytesseract
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return None  # pytesseract installed but tesseract binary not found
    except ImportError:
        return None


# Track OCR availability to avoid repeated failures within the same session
_ocr_available = None  # None = not checked yet, True/False = cached result


def _ocr_screenshot(region=None):
    """
    Take a screenshot and run OCR, returning text with bounding boxes.
    Returns list of dicts: [{text, x, y, w, h, center_x, center_y, confidence}, ...]
    Returns None (not empty list) if OCR itself is broken/unavailable.
    """
    global _ocr_available
    import pyautogui
    from PIL import Image

    # If we already know OCR is broken, don't waste time
    if _ocr_available is False:
        return None

    # Take screenshot
    img = pyautogui.screenshot()
    screen_w, screen_h = img.size

    # Crop to region if specified
    if region and region != "full":
        regions = {
            "top": (0, 0, screen_w, screen_h // 2),
            "bottom": (0, screen_h // 2, screen_w, screen_h),
            "left": (0, 0, screen_w // 2, screen_h),
            "right": (screen_w // 2, 0, screen_w, screen_h),
            "center": (screen_w // 4, screen_h // 4, 3 * screen_w // 4, 3 * screen_h // 4),
        }
        if region in regions:
            box = regions[region]
            img = img.crop(box)
            offset_x, offset_y = box[0], box[1]
        else:
            offset_x, offset_y = 0, 0
    else:
        offset_x, offset_y = 0, 0

    # Try pytesseract first
    pytesseract = _get_tesseract()
    if pytesseract is not None:
        try:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            results = []
            n = len(data["text"])
            for i in range(n):
                text = data["text"][i].strip()
                conf = int(data["conf"][i]) if str(data["conf"][i]) != "-1" else 0
                if text and conf > 30:
                    x = data["left"][i] + offset_x
                    y = data["top"][i] + offset_y
                    w = data["width"][i]
                    h = data["height"][i]
                    results.append({
                        "text": text,
                        "x": x, "y": y, "w": w, "h": h,
                        "center_x": x + w // 2,
                        "center_y": y + h // 2,
                        "confidence": conf,
                    })
            _ocr_available = True
            return results
        except Exception as e:
            log.warning(f"Tesseract OCR failed: {e}")

    # Try PowerShell Windows.Media.Ocr fallback
    ps_results = _ocr_powershell_fallback(img, offset_x, offset_y)
    if ps_results is not None:
        _ocr_available = True
        return ps_results

    # Both OCR methods failed — mark as unavailable for this session
    _ocr_available = False
    log.error("All OCR methods failed. Screen analysis unavailable.")
    return None


def _ocr_powershell_fallback(img, offset_x=0, offset_y=0):
    """
    Fallback OCR using PowerShell + Windows built-in WinRT OCR.
    Returns list of results, or None if the method itself is broken.
    """
    import tempfile
    temp_path = os.path.join(tempfile.gettempdir(), "sharkon_ocr_temp.png")

    try:
        img.save(temp_path)
    except Exception as e:
        log.error(f"Failed to save temp OCR image: {e}")
        return None

    # Use a C# helper via PowerShell for reliable WinRT async access
    ps_script = """
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime

    # Helper to await WinRT async operations
    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]

    Function WaitAsync($WinRtTask, $ResultType) {
        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }

    # Load WinRT types
    [void][Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
    [void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
    [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime]

    # Open image file
    $file = WaitAsync ([Windows.Storage.StorageFile]::GetFileFromPathAsync('TEMP_PATH')) ([Windows.Storage.StorageFile])
    $stream = WaitAsync ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = WaitAsync ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = WaitAsync ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

    # Run OCR
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($engine -eq $null) {
        Write-Error "OCR engine unavailable"
        exit 1
    }
    $ocrResult = WaitAsync ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

    foreach ($line in $ocrResult.Lines) {
        foreach ($word in $line.Words) {
            $r = $word.BoundingRect
            Write-Output "$($word.Text)|$([int]$r.X)|$([int]$r.Y)|$([int]$r.Width)|$([int]$r.Height)"
        }
    }
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
""".replace("TEMP_PATH", temp_path.replace("\\", "\\\\"))

    try:
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True, text=True, timeout=20,
        )

        if proc.returncode != 0:
            stderr = proc.stderr.strip()[:200] if proc.stderr else "unknown error"
            log.warning(f"PowerShell OCR failed (rc={proc.returncode}): {stderr}")
            return None

        results = []
        output = proc.stdout.strip()
        if not output:
            return results  # Empty but valid — screen has no text

        for line in output.split('\n'):
            line = line.strip()
            if not line or '|' not in line:
                continue
            parts = line.split('|')
            if len(parts) < 5:
                continue
            try:
                text = parts[0]
                x = int(parts[1]) + offset_x
                y = int(parts[2]) + offset_y
                w = int(parts[3])
                h = int(parts[4])
                results.append({
                    "text": text,
                    "x": x, "y": y, "w": w, "h": h,
                    "center_x": x + w // 2,
                    "center_y": y + h // 2,
                    "confidence": 80,
                })
            except (ValueError, IndexError):
                continue

        return results

    except subprocess.TimeoutExpired:
        log.warning("PowerShell OCR timed out")
        return None
    except Exception as e:
        log.error(f"PowerShell OCR error: {e}")
        return None
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


async def analyze_screen(region: str = "full") -> ToolResult:
    """Analyze the screen using OCR — returns all visible text with positions."""
    log.info(f"Analyzing screen (region: {region})...")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot(region))

        # OCR system is broken/unavailable
        if results is None:
            return ToolResult(
                success=False, stdout="",
                stderr=(
                    "OCR is not available. DO NOT retry analyze_screen or click_text. "
                    "Instead, use keyboard shortcuts to navigate: "
                    "hotkey(['ctrl', 'l']) to focus the address bar, "
                    "type_text to type URLs, press_key('enter') to navigate, "
                    "press_key('tab') to move between elements. "
                    "Use screenshot to see what's on screen."
                ),
                return_code=1,
            )

        # No text found (but OCR is working)
        if not results:
            return ToolResult(
                success=True,
                stdout="No text detected on screen. The screen may be blank, loading, or showing only images.",
                stderr="", return_code=0,
            )

        # Group nearby words into logical lines for cleaner output
        lines = []
        current_line = []
        last_y = -999

        sorted_results = sorted(results, key=lambda r: (r["y"] // 20, r["x"]))
        for r in sorted_results:
            if abs(r["y"] - last_y) > 15 and current_line:
                line_text = " ".join(w["text"] for w in current_line)
                avg_x = sum(w["center_x"] for w in current_line) // len(current_line)
                avg_y = sum(w["center_y"] for w in current_line) // len(current_line)
                lines.append(f"  [{avg_x:4d}, {avg_y:4d}] {line_text}")
                current_line = []
            current_line.append(r)
            last_y = r["y"]

        if current_line:
            line_text = " ".join(w["text"] for w in current_line)
            avg_x = sum(w["center_x"] for w in current_line) // len(current_line)
            avg_y = sum(w["center_y"] for w in current_line) // len(current_line)
            lines.append(f"  [{avg_x:4d}, {avg_y:4d}] {line_text}")

        output = f"Screen analysis ({len(results)} words detected, {len(lines)} lines):\n"
        output += "Format: [center_x, center_y] text_content\n"
        output += "─" * 60 + "\n"
        output += "\n".join(lines[:80])  # Cap at 80 lines
        if len(lines) > 80:
            output += f"\n... and {len(lines) - 80} more lines"

        return ToolResult(success=True, stdout=output, stderr="", return_code=0)

    except Exception as e:
        log.error(f"analyze_screen error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Screen analysis error: {e}", return_code=1)


async def click_text(text: str, button: str = "left", occurrence: int = 1) -> ToolResult:
    """Find text on screen using OCR and click on it."""
    log.info(f"Clicking on text: '{text}' (occurrence {occurrence}, button {button})")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot())

        if results is None:
            return ToolResult(
                success=False, stdout="",
                stderr=(
                    f"OCR unavailable — cannot find '{text}' visually. "
                    "Use keyboard navigation instead: hotkey(['ctrl','l']) for address bar, "
                    "press_key('tab') to move between elements, type_text to type."
                ),
                return_code=1,
            )

        if not results:
            return ToolResult(
                success=False, stdout="",
                stderr=f"No text found on screen. Cannot locate '{text}'.",
                return_code=1,
            )

        # Search for the text (case-insensitive, partial match)
        text_lower = text.lower().strip()
        matches = []

        # First try exact word match
        for r in results:
            if r["text"].lower() == text_lower:
                matches.append(r)

        # If no exact match, try partial / contains match
        if not matches:
            # Try matching multi-word text by grouping nearby words
            sorted_results = sorted(results, key=lambda r: (r["y"] // 20, r["x"]))
            for i, r in enumerate(sorted_results):
                # Build a string from this word and next few words on same line
                combined = r["text"]
                combined_items = [r]
                for j in range(i + 1, min(i + 8, len(sorted_results))):
                    next_r = sorted_results[j]
                    if abs(next_r["y"] - r["y"]) < 15:  # Same line
                        combined += " " + next_r["text"]
                        combined_items.append(next_r)
                    else:
                        break
                if text_lower in combined.lower():
                    # Calculate center of the matched group
                    avg_x = sum(item["center_x"] for item in combined_items) // len(combined_items)
                    avg_y = sum(item["center_y"] for item in combined_items) // len(combined_items)
                    matches.append({
                        "text": combined,
                        "center_x": avg_x,
                        "center_y": avg_y,
                    })
                    break  # Take first match in the group search

        if not matches:
            # List what IS visible to help the AI
            visible_texts = list(set(r["text"] for r in results if len(r["text"]) > 1))[:30]
            return ToolResult(
                success=False, stdout="",
                stderr=(
                    f"Text '{text}' not found on screen. "
                    f"Visible texts include: {', '.join(visible_texts[:20])}"
                ),
                return_code=1,
            )

        # Select the requested occurrence
        idx = min(occurrence - 1, len(matches) - 1)
        match = matches[idx]
        cx, cy = match["center_x"], match["center_y"]

        # Click at the found position
        pyautogui.click(x=cx, y=cy, button=button)

        return ToolResult(
            success=True,
            stdout=f"✅ Clicked on '{text}' at position ({cx}, {cy}).",
            stderr="", return_code=0,
        )

    except Exception as e:
        log.error(f"click_text error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"click_text error: {e}", return_code=1)


async def find_text_on_screen(text: str) -> ToolResult:
    """Find text on screen and return its coordinates (without clicking)."""
    log.info(f"Finding text on screen: '{text}'")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot())

        text_lower = text.lower().strip()
        matches = []

        for r in results:
            if text_lower in r["text"].lower():
                matches.append(r)

        # Also try multi-word matching
        if not matches:
            sorted_results = sorted(results, key=lambda r: (r["y"] // 20, r["x"]))
            for i, r in enumerate(sorted_results):
                combined = r["text"]
                combined_items = [r]
                for j in range(i + 1, min(i + 8, len(sorted_results))):
                    next_r = sorted_results[j]
                    if abs(next_r["y"] - r["y"]) < 15:
                        combined += " " + next_r["text"]
                        combined_items.append(next_r)
                    else:
                        break
                if text_lower in combined.lower():
                    avg_x = sum(item["center_x"] for item in combined_items) // len(combined_items)
                    avg_y = sum(item["center_y"] for item in combined_items) // len(combined_items)
                    matches.append({
                        "text": combined,
                        "center_x": avg_x,
                        "center_y": avg_y,
                        "confidence": 80,
                    })

        if matches:
            lines = [f"Found '{text}' at {len(matches)} location(s):"]
            for i, m in enumerate(matches[:10], 1):
                lines.append(
                    f"  {i}. '{m['text']}' → center ({m['center_x']}, {m['center_y']})"
                )
            return ToolResult(success=True, stdout="\n".join(lines), stderr="", return_code=0)
        else:
            visible = list(set(r["text"] for r in results if len(r["text"]) > 1))[:25]
            return ToolResult(
                success=False, stdout="",
                stderr=f"'{text}' not found. Visible: {', '.join(visible)}",
                return_code=1,
            )

    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def get_active_window() -> ToolResult:
    """Get information about the currently focused window."""
    log.info("Getting active window info...")
    try:
        # Use PowerShell to get the foreground window info
        ps_script = (
            "Add-Type @'\n"
            "using System;\n"
            "using System.Runtime.InteropServices;\n"
            "public class WinAPI {\n"
            "    [DllImport(\"user32.dll\")]\n"
            "    public static extern IntPtr GetForegroundWindow();\n"
            "    [DllImport(\"user32.dll\")]\n"
            "    public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);\n"
            "    [DllImport(\"user32.dll\")]\n"
            "    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);\n"
            "    [DllImport(\"user32.dll\")]\n"
            "    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);\n"
            "    public struct RECT { public int Left, Top, Right, Bottom; }\n"
            "}\n"
            "'@\n"
            "$hwnd = [WinAPI]::GetForegroundWindow()\n"
            "$sb = New-Object System.Text.StringBuilder 256\n"
            "[void][WinAPI]::GetWindowText($hwnd, $sb, 256)\n"
            "$title = $sb.ToString()\n"
            "$pid = 0\n"
            "[void][WinAPI]::GetWindowThreadProcessId($hwnd, [ref]$pid)\n"
            "$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue\n"
            "$rect = New-Object WinAPI+RECT\n"
            "[void][WinAPI]::GetWindowRect($hwnd, [ref]$rect)\n"
            "Write-Output \"Title: $title\"\n"
            "Write-Output \"Process: $($proc.ProcessName)\"\n"
            "Write-Output \"PID: $pid\"\n"
            "Write-Output \"Position: ($($rect.Left), $($rect.Top))\"\n"
            "Write-Output \"Size: $($rect.Right - $rect.Left) x $($rect.Bottom - $rect.Top)\"\n"
        )
        result = await execute_cmd(f'powershell -NoProfile -Command "{ps_script}"')
        if result.success:
            return ToolResult(success=True, stdout=result.stdout, stderr="", return_code=0)
        # Simpler fallback
        result2 = await execute_cmd(
            'powershell -NoProfile -Command "(Get-Process | Where-Object {$_.MainWindowTitle -ne \"\"} | Select-Object ProcessName, MainWindowTitle, Id | Format-Table -AutoSize | Out-String).Trim()"'
        )
        return result2
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── Network Tools ───────────────────────────────────────────────────────────

async def http_request(url: str, headers: dict = None) -> ToolResult:
    """Make an HTTP GET request."""
    log.info(f"HTTP request: {url}")
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "SharkonAI/1.0")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=30)
        )
        body = response.read().decode("utf-8", errors="replace")

        max_len = 10000
        if len(body) > max_len:
            body = body[:max_len] + "\n... [response truncated]"

        result = f"Status: {response.status}\nURL: {url}\n\n{body}"
        return ToolResult(success=True, stdout=result, stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"HTTP error: {e}", return_code=1)


async def download_file(url: str, save_path: str = "") -> ToolResult:
    """Download a file from URL to disk. Saves to media/downloads by default."""
    # Default save path into media/downloads
    if not save_path:
        url_filename = url.split("/")[-1].split("?")[0] or "downloaded_file"
        save_path = os.path.join(CONFIG.DOWNLOADS_DIR, url_filename)
    elif not os.path.isabs(save_path):
        save_path = os.path.join(CONFIG.DOWNLOADS_DIR, save_path)

    log.info(f"Downloading: {url} -> {save_path}")
    try:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        loop = asyncio.get_event_loop()

        def _download():
            urllib.request.urlretrieve(url, save_path)
            return os.path.getsize(save_path)

        size = await loop.run_in_executor(None, _download)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"

        # Auto-detect if downloaded file is an image → set image_path for auto-send
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff')
        img_path = save_path if save_path.lower().endswith(image_extensions) else ""

        return ToolResult(
            success=True, stdout=f"Downloaded {size_str} to {save_path}",
            stderr="", return_code=0, image_path=img_path,
        )
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Download error: {e}", return_code=1)


# ── Clipboard Tools ─────────────────────────────────────────────────────────

async def get_clipboard() -> ToolResult:
    """Read the system clipboard."""
    try:
        import pyperclip
        content = pyperclip.paste()
        return ToolResult(success=True, stdout=content or "(clipboard is empty)", stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def set_clipboard(text: str) -> ToolResult:
    """Set the system clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return ToolResult(
            success=True, stdout=f"Copied {len(text)} characters to clipboard.", stderr="", return_code=0
        )
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── Audio Transcription Tools ───────────────────────────────────────────────

def _convert_audio_to_wav(input_path: str) -> str:
    """
    Convert any audio format (OGG, MP3, M4A, FLAC, WebM) to WAV using ffmpeg.
    Returns the path to the WAV file.
    """
    wav_path = os.path.splitext(input_path)[0] + "_converted.wav"

    # Try ffmpeg first
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000",    # 16kHz sample rate (optimal for speech)
                "-ac", "1",        # Mono
                "-sample_fmt", "s16",  # 16-bit PCM
                wav_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and os.path.exists(wav_path):
            return wav_path
        log.warning(f"ffmpeg conversion failed: {result.stderr[:200]}")
    except FileNotFoundError:
        log.warning("ffmpeg not found, trying PowerShell fallback...")
    except Exception as e:
        log.warning(f"ffmpeg error: {e}")

    # Fallback: try PowerShell with Windows Media Foundation
    try:
        ps_cmd = (
            f'$inputFile = "{input_path.replace(chr(92), chr(92)*2)}"; '
            f'$outputFile = "{wav_path.replace(chr(92), chr(92)*2)}"; '
            '$null = [Reflection.Assembly]::LoadWithPartialName("NAudio"); '
            'if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { '
            '  Write-Error "No audio converter available"; exit 1 '
            '}'
        )
        # If ffmpeg isn't available, we can try python-based conversion
        py_convert = (
            f"import subprocess, sys; "
            f"subprocess.run([sys.executable, '-m', 'pip', 'install', 'pydub'], "
            f"capture_output=True); "
            f"from pydub import AudioSegment; "
            f"audio = AudioSegment.from_file(r'{input_path}'); "
            f"audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2); "
            f"audio.export(r'{wav_path}', format='wav')"
        )
        result = subprocess.run(
            ["python", "-c", py_convert],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and os.path.exists(wav_path):
            return wav_path
        log.warning(f"Python pydub conversion failed: {result.stderr[:200]}")
    except Exception as e:
        log.warning(f"Fallback conversion error: {e}")

    return ""


def _transcribe_with_speech_recognition(wav_path: str, language: str = "en-US") -> str:
    """
    Transcribe a WAV file using the SpeechRecognition library.
    Uses Google Web Speech API (free, no API key needed).
    """
    try:
        import speech_recognition as sr
    except ImportError:
        # Auto-install
        log.info("Installing SpeechRecognition...")
        subprocess.run(
            ["pip", "install", "SpeechRecognition"],
            capture_output=True, timeout=60,
        )
        import speech_recognition as sr

    recognizer = sr.Recognizer()

    # Tune for noisy Telegram voice messages
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    with sr.AudioFile(wav_path) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio_data = recognizer.record(source)

    # Try Google Web Speech API (free)
    try:
        text = recognizer.recognize_google(audio_data, language=language)
        return text
    except sr.UnknownValueError:
        log.warning("Google Speech API could not understand the audio")
    except sr.RequestError as e:
        log.warning(f"Google Speech API error: {e}")

    return ""


def _transcribe_powershell_fallback(wav_path: str) -> str:
    """
    Fallback transcription using Windows built-in System.Speech.
    Only supports English but requires no external dependencies.
    """
    ps_script = f"""
try {{
    Add-Type -AssemblyName System.Speech
    $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    $recognizer.SetInputToWaveFile("{wav_path.replace(chr(92), chr(92)*2)}")

    # Load default grammar
    $grammar = New-Object System.Speech.Recognition.DictationGrammar
    $recognizer.LoadGrammar($grammar)

    $result = $recognizer.Recognize()
    if ($result) {{
        Write-Output $result.Text
    }} else {{
        Write-Error "No speech recognized"
        exit 1
    }}
    $recognizer.Dispose()
}} catch {{
    Write-Error $_.Exception.Message
    exit 1
}}
"""
    try:
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception as e:
        log.warning(f"PowerShell speech recognition failed: {e}")

    return ""


async def transcribe_audio(audio_path: str, language: str = "en-US") -> ToolResult:
    """
    Transcribe an audio file to text.
    Supports OGG, WAV, MP3, M4A, FLAC, WebM.
    Uses Google Web Speech API with fallback to Windows System.Speech.
    """
    log.info(f"Transcribing audio: {audio_path} (language: {language})")

    if not os.path.exists(audio_path):
        return ToolResult(
            success=False, stdout="",
            stderr=f"Audio file not found: {audio_path}",
            return_code=1,
        )

    loop = asyncio.get_event_loop()

    # Convert to WAV if needed
    ext = os.path.splitext(audio_path)[1].lower()
    if ext == ".wav":
        wav_path = audio_path
    else:
        wav_path = await loop.run_in_executor(None, _convert_audio_to_wav, audio_path)
        if not wav_path:
            return ToolResult(
                success=False, stdout="",
                stderr=(
                    f"Failed to convert {ext} to WAV. "
                    "Install ffmpeg: winget install ffmpeg / choco install ffmpeg. "
                    "Or install pydub: pip install pydub"
                ),
                return_code=1,
            )

    try:
        # Primary: SpeechRecognition + Google API
        text = await loop.run_in_executor(
            None, _transcribe_with_speech_recognition, wav_path, language
        )

        # Fallback: Windows System.Speech (English only)
        if not text and language.startswith("en"):
            log.info("Trying Windows System.Speech fallback...")
            text = await loop.run_in_executor(
                None, _transcribe_powershell_fallback, wav_path
            )

        if text:
            return ToolResult(
                success=True,
                stdout=f"🎤 Transcription:\n{text}",
                stderr="", return_code=0,
            )
        else:
            return ToolResult(
                success=False, stdout="",
                stderr=(
                    "Could not transcribe audio. Possible reasons:\n"
                    "• Audio is too noisy or unclear\n"
                    "• No speech detected in the recording\n"
                    "• Language mismatch (try specifying language parameter)\n"
                    "• Network issue (Google API requires internet)"
                ),
                return_code=1,
            )
    finally:
        # Clean up converted file
        if wav_path != audio_path:
            try:
                os.remove(wav_path)
            except OSError:
                pass


# ── Utility Tools ───────────────────────────────────────────────────────────

async def wait(seconds: float) -> ToolResult:
    """Wait for a specified duration."""
    log.info(f"Waiting {seconds}s...")
    seconds = min(seconds, 60)  # Cap at 60 seconds for safety
    await asyncio.sleep(seconds)
    return ToolResult(success=True, stdout=f"Waited {seconds} seconds.", stderr="", return_code=0)


# Placeholder implementations for memory tools — these get replaced at runtime
# by the Brain which injects the actual memory instance

_memory_ref = None


def set_memory_ref(memory):
    """Inject memory reference for remember/recall tools."""
    global _memory_ref
    _memory_ref = memory


async def remember(category: str, key: str, value: str) -> ToolResult:
    """Store a fact in permanent memory."""
    if _memory_ref is None:
        return ToolResult(success=False, stdout="", stderr="Memory not initialized.", return_code=1)
    try:
        await _memory_ref.store_knowledge(category, key, value)
        return ToolResult(
            success=True,
            stdout=f"Remembered: [{category}] {key} = {value}",
            stderr="", return_code=0,
        )
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def recall(query: str) -> ToolResult:
    """Search permanent memory for stored knowledge."""
    if _memory_ref is None:
        return ToolResult(success=False, stdout="", stderr="Memory not initialized.", return_code=1)
    try:
        results = await _memory_ref.search_knowledge(query)
        if results:
            lines = []
            for r in results:
                lines.append(f"[{r['category']}] {r['key']}: {r['value']} (confidence: {r['confidence']})")
            return ToolResult(success=True, stdout="\n".join(lines), stderr="", return_code=0)
        else:
            return ToolResult(success=True, stdout="No matching knowledge found.", stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── Send Image Tool ─────────────────────────────────────────────────────────

async def send_image(path: str, caption: str = "") -> ToolResult:
    """Send an image file to the user. Returns a ToolResult with image_path set."""
    log.info(f"Sending image: {path}")
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, stdout="", stderr=f"Image file not found: {path}", return_code=1)
        
        # Verify it's an image
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff')
        if not path.lower().endswith(valid_extensions):
            return ToolResult(
                success=False, stdout="",
                stderr=f"Not a supported image format. Supported: {', '.join(valid_extensions)}",
                return_code=1,
            )
        
        size = os.path.getsize(path)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
        
        return ToolResult(
            success=True,
            stdout=f"Sending image: {os.path.basename(path)} ({size_str})",
            stderr="",
            return_code=0,
            image_path=path,  # Signal to telegram handler to send as photo
        )
    except Exception as e:
        log.error(f"send_image error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── File Creation & Sending Tools ───────────────────────────────────────────

async def create_file(filename: str, content: str, caption: str = "") -> ToolResult:
    """
    Create a text-based file and return it for sending via Telegram.
    Supports TXT, CSV, HTML, JSON, XML, MD, PY, JS, and any text format.
    """
    log.info(f"Creating file: {filename}")
    try:
        filepath = os.path.join(CONFIG.MEDIA_DIR, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        size = os.path.getsize(filepath)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"

        return ToolResult(
            success=True,
            stdout=f"✅ File created: {filename} ({size_str})",
            stderr="", return_code=0,
            file_path=filepath,  # Signal to telegram handler to send as document
        )
    except Exception as e:
        log.error(f"create_file error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Failed to create file: {e}", return_code=1)


async def create_pdf(filename: str, title: str, content: str, caption: str = "") -> ToolResult:
    """
    Create a PDF document with title and content, then return for sending via Telegram.
    Uses fpdf2 library. Supports section headers with '## ' prefix.
    """
    log.info(f"Creating PDF: {filename}")

    # Ensure .pdf extension
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    filepath = os.path.join(CONFIG.MEDIA_DIR, filename)

    try:
        # Import or install fpdf2
        try:
            from fpdf import FPDF
        except ImportError:
            log.info("fpdf2 not found, installing...")
            install_result = await execute_cmd("pip install fpdf2")
            if not install_result.success:
                return ToolResult(
                    success=False, stdout="",
                    stderr=f"Failed to install fpdf2: {install_result.stderr}",
                    return_code=1,
                )
            from fpdf import FPDF

        # Create the PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Try to use a Unicode-capable font, fall back to built-in Helvetica
        # DejaVu is commonly available on Windows
        font_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        arial_path = os.path.join(font_dir, "arial.ttf")
        if os.path.exists(arial_path):
            pdf.add_font("ArialUni", "", arial_path, uni=True)
            pdf.add_font("ArialUni", "B", os.path.join(font_dir, "arialbd.ttf"), uni=True)
            title_font = "ArialUni"
            body_font = "ArialUni"
        else:
            title_font = "Helvetica"
            body_font = "Helvetica"

        # Title
        pdf.set_font(title_font, "B", 18)
        pdf.cell(0, 12, title, ln=True, align="C")
        pdf.ln(8)

        # Separator line
        pdf.set_draw_color(100, 100, 100)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(6)

        # Body content — process line by line
        for line in content.split("\n"):
            if line.startswith("## "):
                # Section header
                pdf.ln(4)
                pdf.set_font(title_font, "B", 14)
                pdf.cell(0, 8, line[3:].strip(), ln=True)
                pdf.ln(2)
            elif line.strip() == "":
                pdf.ln(4)
            else:
                pdf.set_font(body_font, "", 11)
                pdf.multi_cell(0, 6, line.strip())
                pdf.ln(1)

        # Footer with generation info
        pdf.ln(10)
        pdf.set_font(body_font, "", 8)
        pdf.set_text_color(150, 150, 150)
        from datetime import datetime
        pdf.cell(0, 5, f"Generated by SharkonAI — {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")

        # Save
        pdf.output(filepath)

        size = os.path.getsize(filepath)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"

        return ToolResult(
            success=True,
            stdout=f"✅ PDF created: {filename} ({size_str})",
            stderr="", return_code=0,
            file_path=filepath,  # Signal to telegram handler to send as document
        )
    except Exception as e:
        log.error(f"create_pdf error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Failed to create PDF: {e}", return_code=1)


async def send_file(path: str, caption: str = "") -> ToolResult:
    """Send any file to the user as a Telegram document."""
    log.info(f"Sending file: {path}")
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, stdout="", stderr=f"File not found: {path}", return_code=1)

        size = os.path.getsize(path)
        if size > 50 * 1024 * 1024:  # Telegram 50MB limit
            return ToolResult(
                success=False, stdout="",
                stderr=f"File too large ({size / (1024*1024):.1f} MB). Telegram limit is 50 MB.",
                return_code=1,
            )

        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"

        return ToolResult(
            success=True,
            stdout=f"Sending file: {os.path.basename(path)} ({size_str})",
            stderr="", return_code=0,
            file_path=path,  # Signal to telegram handler to send as document
        )
    except Exception as e:
        log.error(f"send_file error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── Tool Dispatcher ─────────────────────────────────────────────────────────

TOOL_MAP = {
    "execute_cmd": execute_cmd,
    "execute_powershell": execute_powershell,
    "run_python": run_python,
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file,
    "list_directory": list_directory,
    "find_files": find_files,
    "create_file": create_file,
    "create_pdf": create_pdf,
    "send_file": send_file,
    "type_text": type_text,
    "press_key": press_key,
    "hotkey": hotkey,
    "mouse_click": mouse_click,
    "mouse_move": mouse_move,
    "mouse_scroll": mouse_scroll,
    "drag_and_drop": drag_and_drop,
    "drag_text": drag_text,
    "mouse_hover": mouse_hover,
    "hover_text": hover_text,
    "select_text": select_text,
    "select_region": select_region,
    "scroll_smooth": scroll_smooth,
    "mouse_hold": mouse_hold,
    "get_mouse_position": get_mouse_position,
    "right_click_at": right_click_at,
    "screenshot": screenshot,
    "send_image": send_image,
    "take_photo": take_photo,
    "get_system_info": get_system_info,
    "get_running_processes": get_running_processes,
    "kill_process": kill_process,
    "open_application": open_application,
    "http_request": http_request,
    "download_file": download_file,
    "get_clipboard": get_clipboard,
    "set_clipboard": set_clipboard,
    "wait": wait,
    "remember": remember,
    "recall": recall,
    "transcribe_audio": transcribe_audio,
    "analyze_screen": analyze_screen,
    "click_text": click_text,
    "find_text_on_screen": find_text_on_screen,
    "get_active_window": get_active_window,
}


async def dispatch_tool(action: str, parameters: dict) -> ToolResult:
    """Dispatch a tool call by name with the given parameters."""
    if action not in TOOL_MAP:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Unknown tool: {action}. Available: {list(TOOL_MAP.keys())}",
            return_code=1,
        )

    func = TOOL_MAP[action]
    try:
        # Filter out None-valued params (AI sometimes sends null for optional args)
        clean_params = {k: v for k, v in parameters.items() if v is not None}
        result = await func(**clean_params)
        return result
    except TypeError as e:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Invalid parameters for {action}: {e}",
            return_code=1,
        )
    except Exception as e:
        return ToolResult(
            success=False, stdout="",
            stderr=f"Tool execution error: {e}",
            return_code=1,
        )
