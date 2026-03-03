"""
Skill: GUI Automation
Keyboard, mouse, drag & drop, hover, select, scroll operations.
"""

import asyncio
import time
import os

import pyautogui

from logger import log
from skills.system_commands import ToolResult

# PyAutoGUI safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


# ── Definitions ─────────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
    {
        "name": "type_text",
        "description": (
            "Type text using the keyboard, as if a human is typing. "
            "Simulates real keystrokes. The text is typed wherever the cursor is. "
            "Handles both ASCII and Unicode (Arabic, emoji, etc.) text."
        ),
        "parameters": {
            "text": {"type": "string", "description": "The text to type."},
            "interval": {"type": "number", "description": "Seconds between each keystroke (default 0.03). Use 0 for instant."},
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
            "key": {"type": "string", "description": "The key to press (e.g. 'enter', 'tab', 'escape', 'a', 'f5')."},
            "presses": {"type": "integer", "description": "Number of times to press the key (default 1)."},
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
            "keys": {"type": "array", "description": "List of keys to press simultaneously, e.g. ['ctrl', 'c']."},
        },
    },
    {
        "name": "mouse_click",
        "description": (
            "Click the mouse at a specific screen position (x, y pixels). "
            "Supports left, right, and middle click, single/double/triple click."
        ),
        "parameters": {
            "x": {"type": "integer", "description": "X coordinate (pixels from left edge of screen)."},
            "y": {"type": "integer", "description": "Y coordinate (pixels from top edge of screen)."},
            "button": {"type": "string", "description": "Mouse button: 'left' (default), 'right', or 'middle'."},
            "clicks": {"type": "integer", "description": "Number of clicks (1=single, 2=double). Default 1."},
        },
    },
    {
        "name": "mouse_move",
        "description": "Move the mouse cursor to a specific screen position.",
        "parameters": {
            "x": {"type": "integer", "description": "X coordinate."},
            "y": {"type": "integer", "description": "Y coordinate."},
            "duration": {"type": "number", "description": "Seconds for movement animation (0 = instant). Default 0.3."},
        },
    },
    {
        "name": "mouse_scroll",
        "description": "Scroll the mouse wheel. Positive = up, negative = down.",
        "parameters": {
            "clicks": {"type": "integer", "description": "Scroll clicks. Positive = up, negative = down."},
            "x": {"type": "integer", "description": "Optional X position."},
            "y": {"type": "integer", "description": "Optional Y position."},
        },
    },
    {
        "name": "drag_and_drop",
        "description": (
            "Drag from one screen position and drop at another with pixel-perfect precision. "
            "Use this to move files, rearrange items, resize windows, drag sliders, etc."
        ),
        "parameters": {
            "start_x": {"type": "integer", "description": "X coordinate to start dragging from."},
            "start_y": {"type": "integer", "description": "Y coordinate to start dragging from."},
            "end_x": {"type": "integer", "description": "X coordinate to drop at."},
            "end_y": {"type": "integer", "description": "Y coordinate to drop at."},
            "duration": {"type": "number", "description": "Seconds for the drag movement (default 0.5)."},
            "button": {"type": "string", "description": "Mouse button to use: 'left' (default), 'right', 'middle'."},
        },
    },
    {
        "name": "mouse_hover",
        "description": (
            "Move the mouse to a position and HOLD it there (hover). "
            "Triggers hover effects like tooltips, dropdown menus, preview popups, etc."
        ),
        "parameters": {
            "x": {"type": "integer", "description": "X coordinate to hover at."},
            "y": {"type": "integer", "description": "Y coordinate to hover at."},
            "hover_time": {"type": "number", "description": "Seconds to hold the hover position (default 1.0)."},
        },
    },
    {
        "name": "select_text",
        "description": (
            "Select text on screen precisely. Modes: 'all' (Ctrl+A), 'word' (double-click), "
            "'line' (triple-click), 'range' (click+shift+click)."
        ),
        "parameters": {
            "mode": {"type": "string", "description": "Selection mode: 'range', 'line', 'all', 'word'."},
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
        "description": "Select a rectangular region on screen by click-dragging.",
        "parameters": {
            "start_x": {"type": "integer", "description": "Top-left X coordinate."},
            "start_y": {"type": "integer", "description": "Top-left Y coordinate."},
            "end_x": {"type": "integer", "description": "Bottom-right X coordinate."},
            "end_y": {"type": "integer", "description": "Bottom-right Y coordinate."},
            "duration": {"type": "number", "description": "Seconds for the drag (default 0.3)."},
        },
    },
    {
        "name": "scroll_smooth",
        "description": (
            "Scroll smoothly with fine-grained control. Supports 'up', 'down', 'left', 'right'. "
            "Good for navigating long documents."
        ),
        "parameters": {
            "direction": {"type": "string", "description": "Scroll direction: 'up', 'down', 'left', 'right'."},
            "amount": {"type": "integer", "description": "Total scroll distance in clicks (default 5)."},
            "steps": {"type": "integer", "description": "Number of incremental steps (default 10)."},
            "x": {"type": "integer", "description": "Optional X position."},
            "y": {"type": "integer", "description": "Optional Y position."},
        },
    },
    {
        "name": "mouse_hold",
        "description": "Press and HOLD a mouse button down, or RELEASE a held button.",
        "parameters": {
            "action": {"type": "string", "description": "'press' to hold button down, 'release' to let go."},
            "button": {"type": "string", "description": "Mouse button: 'left' (default), 'right', 'middle'."},
            "x": {"type": "integer", "description": "Optional X position."},
            "y": {"type": "integer", "description": "Optional Y position."},
        },
    },
    {
        "name": "get_mouse_position",
        "description": "Get the current mouse cursor position (X, Y coordinates) and the pixel color under it.",
        "parameters": {},
    },
    {
        "name": "right_click_at",
        "description": "Right-click at a specific position to open a context menu.",
        "parameters": {
            "x": {"type": "integer", "description": "X coordinate."},
            "y": {"type": "integer", "description": "Y coordinate."},
        },
    },
]


# ── Implementations ─────────────────────────────────────────────────────────

async def type_text(text: str, interval: float = 0.03) -> ToolResult:
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
    log.info(f"Pressing key: {key} (x{presses})")
    try:
        pyautogui.press(key, presses=presses, interval=0.05)
        return ToolResult(success=True, stdout=f"Pressed '{key}' {presses} time(s).", stderr="", return_code=0)
    except Exception as e:
        log.error(f"press_key error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def hotkey(keys: list) -> ToolResult:
    log.info(f"Pressing hotkey: {'+'.join(keys)}")
    try:
        pyautogui.hotkey(*keys)
        return ToolResult(success=True, stdout=f"Pressed hotkey: {'+'.join(keys)}", stderr="", return_code=0)
    except Exception as e:
        log.error(f"hotkey error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_click(x: int, y: int, button: str = "left", clicks: int = 1) -> ToolResult:
    log.info(f"Mouse click: ({x}, {y}) button={button} clicks={clicks}")
    try:
        pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=0.1)
        return ToolResult(success=True, stdout=f"Clicked ({x}, {y}) with {button} ({clicks}x).", stderr="", return_code=0)
    except Exception as e:
        log.error(f"mouse_click error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_move(x: int, y: int, duration: float = 0.3) -> ToolResult:
    log.info(f"Mouse move to: ({x}, {y})")
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return ToolResult(success=True, stdout=f"Moved mouse to ({x}, {y}).", stderr="", return_code=0)
    except Exception as e:
        log.error(f"mouse_move error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_scroll(clicks: int, x: int = None, y: int = None) -> ToolResult:
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


async def drag_and_drop(start_x: int, start_y: int, end_x: int, end_y: int,
                        duration: float = 0.5, button: str = "left") -> ToolResult:
    log.info(f"Drag & drop: ({start_x},{start_y}) → ({end_x},{end_y})")
    try:
        pyautogui.moveTo(start_x, start_y, duration=0.15)
        time.sleep(0.1)
        rel_x = end_x - start_x
        rel_y = end_y - start_y
        pyautogui.mouseDown(button=button)
        time.sleep(0.05)
        steps = max(int(duration * 60), 10)
        for i in range(1, steps + 1):
            t = i / steps
            t_smooth = t * t * (3 - 2 * t)
            ix = int(start_x + rel_x * t_smooth)
            iy = int(start_y + rel_y * t_smooth)
            pyautogui.moveTo(ix, iy, _pause=False)
            time.sleep(duration / steps)
        time.sleep(0.05)
        pyautogui.mouseUp(button=button)
        return ToolResult(success=True, stdout=f"✅ Dragged from ({start_x},{start_y}) to ({end_x},{end_y}).", stderr="", return_code=0)
    except Exception as e:
        try:
            pyautogui.mouseUp(button=button)
        except Exception:
            pass
        log.error(f"drag_and_drop error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_hover(x: int, y: int, hover_time: float = 1.0) -> ToolResult:
    log.info(f"Hovering at ({x}, {y}) for {hover_time}s")
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        await asyncio.sleep(hover_time)
        return ToolResult(success=True, stdout=f"✅ Hovered at ({x}, {y}) for {hover_time}s.", stderr="", return_code=0)
    except Exception as e:
        log.error(f"mouse_hover error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def select_text(mode: str = "all", start_x: int = None, start_y: int = None,
                      end_x: int = None, end_y: int = None, x: int = None, y: int = None) -> ToolResult:
    log.info(f"Selecting text: mode={mode}")
    try:
        if mode == "all":
            pyautogui.hotkey('ctrl', 'a')
            return ToolResult(success=True, stdout="✅ Selected all text (Ctrl+A).", stderr="", return_code=0)
        elif mode == "word":
            if x is None or y is None:
                return ToolResult(success=False, stdout="", stderr="'word' mode requires x, y.", return_code=1)
            pyautogui.click(x=x, y=y, clicks=2, interval=0.05)
            return ToolResult(success=True, stdout=f"✅ Selected word at ({x}, {y}).", stderr="", return_code=0)
        elif mode == "line":
            if x is None or y is None:
                return ToolResult(success=False, stdout="", stderr="'line' mode requires x, y.", return_code=1)
            pyautogui.click(x=x, y=y, clicks=3, interval=0.05)
            return ToolResult(success=True, stdout=f"✅ Selected line at ({x}, {y}).", stderr="", return_code=0)
        elif mode == "range":
            if None in (start_x, start_y, end_x, end_y):
                return ToolResult(success=False, stdout="", stderr="'range' mode requires start_x/y, end_x/y.", return_code=1)
            pyautogui.click(x=start_x, y=start_y)
            time.sleep(0.1)
            pyautogui.keyDown('shift')
            time.sleep(0.05)
            pyautogui.click(x=end_x, y=end_y)
            time.sleep(0.05)
            pyautogui.keyUp('shift')
            return ToolResult(success=True, stdout=f"✅ Selected range ({start_x},{start_y}) to ({end_x},{end_y}).", stderr="", return_code=0)
        else:
            return ToolResult(success=False, stdout="", stderr=f"Unknown mode '{mode}'.", return_code=1)
    except Exception as e:
        try:
            pyautogui.keyUp('shift')
        except Exception:
            pass
        log.error(f"select_text error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def select_region(start_x: int, start_y: int, end_x: int, end_y: int,
                        duration: float = 0.3) -> ToolResult:
    log.info(f"Selecting region: ({start_x},{start_y}) → ({end_x},{end_y})")
    return await drag_and_drop(start_x, start_y, end_x, end_y, duration=duration)


async def scroll_smooth(direction: str = "down", amount: int = 5, steps: int = 10,
                        x: int = None, y: int = None) -> ToolResult:
    log.info(f"Smooth scroll: {direction} amount={amount} steps={steps}")
    try:
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
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                WM_HSCROLL = 0x0114
                scroll_cmd = 1 if direction == "right" else 0
                for _ in range(amount):
                    user32.PostMessageW(hwnd, WM_HSCROLL, scroll_cmd, 0)
                    await asyncio.sleep(0.03)
            except Exception:
                pyautogui.keyDown('shift')
                time.sleep(0.05)
                pyautogui.scroll(-amount if direction == "left" else amount)
                pyautogui.keyUp('shift')
        else:
            return ToolResult(success=False, stdout="", stderr=f"Invalid direction '{direction}'.", return_code=1)
        pos_str = f" at ({x},{y})" if x is not None and y is not None else ""
        return ToolResult(success=True, stdout=f"✅ Scrolled {direction} by {amount}{pos_str}.", stderr="", return_code=0)
    except Exception as e:
        try:
            pyautogui.keyUp('shift')
        except Exception:
            pass
        log.error(f"scroll_smooth error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def mouse_hold(action: str = "press", button: str = "left",
                     x: int = None, y: int = None) -> ToolResult:
    log.info(f"Mouse hold: {action} {button}")
    try:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.1)
        if action == "press":
            pyautogui.mouseDown(button=button)
            pos = pyautogui.position()
            return ToolResult(success=True, stdout=f"✅ {button} held DOWN at ({pos.x}, {pos.y}).", stderr="", return_code=0)
        elif action == "release":
            pyautogui.mouseUp(button=button)
            pos = pyautogui.position()
            return ToolResult(success=True, stdout=f"✅ {button} RELEASED at ({pos.x}, {pos.y}).", stderr="", return_code=0)
        else:
            return ToolResult(success=False, stdout="", stderr=f"Unknown action '{action}'.", return_code=1)
    except Exception as e:
        log.error(f"mouse_hold error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def get_mouse_position() -> ToolResult:
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
                f"Relative: ({pos.x / screen_w * 100:.1f}%, {pos.y / screen_h * 100:.1f}%)"
            ),
            stderr="", return_code=0,
        )
    except Exception as e:
        log.error(f"get_mouse_position error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def right_click_at(x: int, y: int) -> ToolResult:
    log.info(f"Right-clicking at ({x}, {y})")
    try:
        pyautogui.click(x=x, y=y, button='right')
        return ToolResult(success=True, stdout=f"✅ Right-clicked at ({x}, {y}).", stderr="", return_code=0)
    except Exception as e:
        log.error(f"right_click_at error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── Skill Map ───────────────────────────────────────────────────────────────

SKILL_MAP = {
    "type_text": type_text,
    "press_key": press_key,
    "hotkey": hotkey,
    "mouse_click": mouse_click,
    "mouse_move": mouse_move,
    "mouse_scroll": mouse_scroll,
    "drag_and_drop": drag_and_drop,
    "mouse_hover": mouse_hover,
    "select_text": select_text,
    "select_region": select_region,
    "scroll_smooth": scroll_smooth,
    "mouse_hold": mouse_hold,
    "get_mouse_position": get_mouse_position,
    "right_click_at": right_click_at,
}
