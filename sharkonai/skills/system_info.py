"""
Skill: System Info & Applications
System info, processes, app launcher, webcam.
"""

import asyncio
import json
import os
import platform
import subprocess

import pyautogui

from config import CONFIG
from logger import log
from skills.system_commands import ToolResult, execute_cmd


# ── App Registry ────────────────────────────────────────────────────────────

WINDOWS_APP_REGISTRY = {
    "camera": "start microsoft.windows.camera:", "webcam": "start microsoft.windows.camera:",
    "photos": "start microsoft.photos:", "calculator": "start calculator:", "calc": "start calculator:",
    "calendar": "start outlookcal:", "clock": "start ms-clock:", "alarms": "start ms-clock:",
    "mail": "start outlookmail:", "maps": "start bingmaps:", "weather": "start bingweather:",
    "store": "start ms-windows-store:", "microsoft store": "start ms-windows-store:",
    "settings": "start ms-settings:", "sound settings": "start ms-settings:sound",
    "wifi settings": "start ms-settings:network-wifi", "bluetooth settings": "start ms-settings:bluetooth",
    "display settings": "start ms-settings:display", "snipping tool": "start snippingtool",
    "snip": "start snippingtool", "screen recorder": "start ms-screenclip:",
    "magnifier": "start magnify", "xbox": "start xbox:", "media player": "start mswindowsmusic:",
    "groove music": "start mswindowsmusic:", "movies": "start mswindowsvideo:",
    "voice recorder": "start windowssoundrecorder:", "sound recorder": "start windowssoundrecorder:",
    "feedback": "start feedback-hub:", "sticky notes": "start ms-stickynotes:",
    "tips": "start ms-get-started:", "notepad": "notepad", "paint": "mspaint",
    "wordpad": "wordpad", "task manager": "taskmgr", "taskmgr": "taskmgr",
    "control panel": "control", "cmd": "cmd", "command prompt": "cmd",
    "terminal": "wt", "windows terminal": "wt", "powershell": "powershell",
    "file explorer": "explorer", "explorer": "explorer", "regedit": "regedit",
    "device manager": "devmgmt.msc", "disk management": "diskmgmt.msc",
    "services": "services.msc", "event viewer": "eventvwr.msc", "system info": "msinfo32",
    "remote desktop": "mstsc", "performance monitor": "perfmon", "resource monitor": "resmon",
    "character map": "charmap", "on-screen keyboard": "osk",
    "chrome": "start chrome", "google chrome": "start chrome",
    "firefox": "start firefox", "edge": "start microsoft-edge:",
    "microsoft edge": "start microsoft-edge:", "brave": "start brave", "opera": "start opera",
    "vscode": "code", "visual studio code": "code", "vs code": "code",
    "word": "start winword", "excel": "start excel", "powerpoint": "start powerpnt",
    "outlook": "start outlook", "teams": "start msteams:", "spotify": "start spotify:",
    "discord": "start discord:", "telegram": "start tg:", "whatsapp": "start whatsapp:",
    "vlc": "start vlc", "obs": "start obs64", "obs studio": "start obs64",
    "steam": "start steam:", "zoom": "start zoommtg:", "skype": "start skype:",
    "7zip": "start 7zFM", "winrar": "start winrar", "git bash": "start git-bash",
}

BROWSER_PATHS = {
    "edge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")],
    "microsoft edge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")],
    "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")],
    "google chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")],
    "firefox": [r"C:\Program Files\Mozilla Firefox\firefox.exe", r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"],
}


# ── Definitions ─────────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
    {
        "name": "get_system_info",
        "description": "Get detailed system info: OS, CPU, RAM, disk space, network, hostname, uptime, etc.",
        "parameters": {},
    },
    {
        "name": "get_running_processes",
        "description": "List running processes with PID, name, and memory usage. Can filter by name.",
        "parameters": {
            "filter_name": {"type": "string", "description": "Optional: filter by name (case-insensitive)."},
        },
    },
    {
        "name": "kill_process",
        "description": "Kill/terminate a process by its PID or name.",
        "parameters": {
            "target": {"type": "string", "description": "PID (number) or process name to kill."},
        },
    },
    {
        "name": "open_application",
        "description": (
            "Open ANY Windows application by its common name. Has a built-in smart registry of 40+ apps. "
            "Examples: 'camera', 'notepad', 'chrome', 'firefox', 'edge', 'explorer', "
            "'cmd', 'terminal', 'powershell', 'calculator', 'paint', 'word', 'excel', 'vscode', "
            "'task manager', 'settings', 'spotify', 'discord', 'telegram', etc. "
            "Can also open files/folders/URLs directly."
        ),
        "parameters": {
            "target": {"type": "string", "description": "Application name, file path, or URL."},
        },
    },
    {
        "name": "take_photo",
        "description": (
            "Take a photo using the computer's webcam/camera and SEND IT to the user in Telegram."
        ),
        "parameters": {
            "filename": {"type": "string", "description": "Optional filename (default: 'camera_photo.jpg')."},
        },
    },
]


# ── Implementations ─────────────────────────────────────────────────────────

async def get_system_info() -> ToolResult:
    log.info("Getting system info...")
    try:
        info_lines = [
            f"OS: {platform.system()} {platform.release()} ({platform.version()})",
            f"Machine: {platform.machine()}", f"Processor: {platform.processor()}",
            f"Hostname: {platform.node()}", f"Python: {platform.python_version()}",
        ]
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            info_lines.append(f"Disk (C:): {used / (1024**3):.1f} GB used / {total / (1024**3):.1f} GB total ({free / (1024**3):.1f} GB free)")
        except Exception:
            pass
        try:
            proc = subprocess.run(
                ['powershell', '-Command', "(Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory | ConvertTo-Json)"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0:
                mem = json.loads(proc.stdout)
                total_mb = int(mem.get("TotalVisibleMemorySize", 0)) / 1024
                free_mb = int(mem.get("FreePhysicalMemory", 0)) / 1024
                info_lines.append(f"RAM: {total_mb - free_mb:.0f} MB used / {total_mb:.0f} MB total ({free_mb:.0f} MB free)")
        except Exception:
            pass
        try:
            w, h = pyautogui.size()
            info_lines.append(f"Screen: {w}x{h}")
        except Exception:
            pass
        return ToolResult(success=True, stdout="\n".join(info_lines), stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def get_running_processes(filter_name: str = None) -> ToolResult:
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
    log.info(f"Killing process: {target}")
    if target.isdigit():
        return await execute_cmd(f'taskkill /PID {target} /F')
    return await execute_cmd(f'taskkill /IM {target} /F')


async def open_application(target: str) -> ToolResult:
    log.info(f"Opening application: {target}")
    target_lower = target.lower().strip()
    if target_lower in WINDOWS_APP_REGISTRY:
        cmd = WINDOWS_APP_REGISTRY[target_lower]
        result = await execute_cmd(cmd)
        if result.success or result.return_code == 0:
            return ToolResult(success=True, stdout=f"✅ Opened {target}.", stderr="", return_code=0)
    try:
        os.startfile(target)
        return ToolResult(success=True, stdout=f"✅ Opened: {target}", stderr="", return_code=0)
    except Exception:
        pass
    if target_lower in BROWSER_PATHS:
        for exe_path in BROWSER_PATHS[target_lower]:
            if os.path.exists(exe_path):
                try:
                    os.startfile(exe_path)
                    return ToolResult(success=True, stdout=f"✅ Opened {target} from: {exe_path}", stderr="", return_code=0)
                except Exception:
                    pass
    result = await execute_cmd(f'start "" "{target}"')
    if result.success:
        return ToolResult(success=True, stdout=f"✅ Opened: {target}", stderr="", return_code=0)
    result = await execute_cmd(target)
    if result.success:
        return ToolResult(success=True, stdout=f"✅ Opened: {target}", stderr="", return_code=0)
    search_result = await execute_cmd(f'where {target_lower} 2>nul')
    if search_result.success and search_result.stdout.strip():
        exe_path = search_result.stdout.strip().split('\n')[0]
        try:
            os.startfile(exe_path)
            return ToolResult(success=True, stdout=f"✅ Opened: {exe_path}", stderr="", return_code=0)
        except Exception:
            pass
    return ToolResult(success=False, stdout="", stderr=f"Could not open '{target}'.", return_code=1)


async def take_photo(filename: str = "camera_photo.jpg") -> ToolResult:
    log.info(f"Taking webcam photo: {filename}")
    filepath = os.path.join(CONFIG.MEDIA_DIR, filename)
    try:
        import cv2
    except ImportError:
        install_result = await execute_cmd('pip install opencv-python')
        if not install_result.success:
            return ToolResult(success=False, stdout="", stderr="opencv-python install failed: " + install_result.stderr, return_code=1)
        import cv2
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return ToolResult(success=False, stdout="", stderr="Could not open webcam.", return_code=1)
        for _ in range(10):
            cap.read()
            await asyncio.sleep(0.05)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return ToolResult(success=False, stdout="", stderr="Failed to capture frame.", return_code=1)
        cv2.imwrite(filepath, frame)
        height, width = frame.shape[:2]
        size = os.path.getsize(filepath)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
        return ToolResult(success=True, stdout=f"📸 Photo captured! {width}x{height}, {size_str}", stderr="", return_code=0, image_path=filepath)
    except Exception as e:
        log.error(f"take_photo error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Camera error: {e}", return_code=1)


# ── Skill Map ───────────────────────────────────────────────────────────────

SKILL_MAP = {
    "get_system_info": get_system_info,
    "get_running_processes": get_running_processes,
    "kill_process": kill_process,
    "open_application": open_application,
    "take_photo": take_photo,
}
