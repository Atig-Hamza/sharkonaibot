"""
Skill: Screen Vision & OCR
Analyze screen content, click text, find text, drag by text, hover by text.
"""

import asyncio
import os
import subprocess
import time

import pyautogui

from config import CONFIG
from logger import log
from skills.system_commands import ToolResult


# ── OCR Engine ──────────────────────────────────────────────────────────────

_ocr_available = None  # None = not checked, True/False = cached


def _get_tesseract():
    """Get pytesseract module with auto-detected Tesseract path."""
    try:
        import pytesseract
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
        try:
            subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5)
            return pytesseract
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None
    except ImportError:
        return None


def _ocr_powershell_fallback(img, offset_x=0, offset_y=0):
    """Fallback OCR using PowerShell + Windows built-in WinRT OCR."""
    import tempfile
    temp_path = os.path.join(tempfile.gettempdir(), "sharkon_ocr_temp.png")
    try:
        img.save(temp_path)
    except Exception as e:
        log.error(f"Failed to save temp OCR image: {e}")
        return None

    ps_script = """
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]
    Function WaitAsync($WinRtTask, $ResultType) {
        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }
    [void][Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
    [void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
    [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime]
    $file = WaitAsync ([Windows.Storage.StorageFile]::GetFileFromPathAsync('TEMP_PATH')) ([Windows.Storage.StorageFile])
    $stream = WaitAsync ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = WaitAsync ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = WaitAsync ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($engine -eq $null) { Write-Error "OCR engine unavailable"; exit 1 }
    $ocrResult = WaitAsync ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    foreach ($line in $ocrResult.Lines) {
        foreach ($word in $line.Words) {
            $r = $word.BoundingRect
            Write-Output "$($word.Text)|$([int]$r.X)|$([int]$r.Y)|$([int]$r.Width)|$([int]$r.Height)"
        }
    }
} catch { Write-Error $_.Exception.Message; exit 1 }
""".replace("TEMP_PATH", temp_path.replace("\\", "\\\\"))

    try:
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True, text=True, timeout=20,
        )
        if proc.returncode != 0:
            log.warning(f"PowerShell OCR failed (rc={proc.returncode})")
            return None
        results = []
        output = proc.stdout.strip()
        if not output:
            return results
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
                    "text": text, "x": x, "y": y, "w": w, "h": h,
                    "center_x": x + w // 2, "center_y": y + h // 2, "confidence": 80,
                })
            except (ValueError, IndexError):
                continue
        return results
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        log.error(f"PowerShell OCR error: {e}")
        return None
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def _ocr_screenshot(region=None):
    """Take a screenshot and run OCR. Returns list of dicts or None if unavailable."""
    global _ocr_available
    from PIL import Image

    if _ocr_available is False:
        return None

    img = pyautogui.screenshot()
    screen_w, screen_h = img.size

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
                        "text": text, "x": x, "y": y, "w": w, "h": h,
                        "center_x": x + w // 2, "center_y": y + h // 2, "confidence": conf,
                    })
            _ocr_available = True
            return results
        except Exception as e:
            log.warning(f"Tesseract OCR failed: {e}")

    ps_results = _ocr_powershell_fallback(img, offset_x, offset_y)
    if ps_results is not None:
        _ocr_available = True
        return ps_results

    _ocr_available = False
    log.error("All OCR methods failed.")
    return None


# ── Definitions ─────────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
    {
        "name": "screenshot",
        "description": (
            "Take a screenshot of the entire screen and SEND IT to the user as a photo in Telegram."
        ),
        "parameters": {
            "filename": {"type": "string", "description": "Optional filename (default: 'screenshot.png')."},
        },
    },
    {
        "name": "analyze_screen",
        "description": (
            "Read and analyze ALL text visible on the screen using OCR. "
            "Returns every piece of text with its position. "
            "ESSENTIAL: Use this BEFORE clicking to understand what's on screen."
        ),
        "parameters": {
            "region": {"type": "string", "description": "Optional region: 'full' (default), 'top', 'bottom', 'left', 'right', 'center'."},
        },
    },
    {
        "name": "click_text",
        "description": (
            "Find specific text on the screen and CLICK on it. "
            "Uses OCR to locate the text, then clicks at its position."
        ),
        "parameters": {
            "text": {"type": "string", "description": "The text to find and click on."},
            "button": {"type": "string", "description": "Mouse button: 'left' (default), 'right', or 'middle'."},
            "occurrence": {"type": "integer", "description": "Which occurrence to click if text appears multiple times (1 = first)."},
        },
    },
    {
        "name": "find_text_on_screen",
        "description": (
            "Search for specific text on the screen and return its coordinates (does NOT click)."
        ),
        "parameters": {
            "text": {"type": "string", "description": "The text to search for on screen."},
        },
    },
    {
        "name": "drag_text",
        "description": (
            "Find text on screen using OCR and DRAG it to a target position or to another text."
        ),
        "parameters": {
            "source_text": {"type": "string", "description": "The text to find and start dragging from."},
            "target_text": {"type": "string", "description": "Optional text to drag to."},
            "target_x": {"type": "integer", "description": "Optional X coordinate (if no target_text)."},
            "target_y": {"type": "integer", "description": "Optional Y coordinate (if no target_text)."},
            "duration": {"type": "number", "description": "Seconds for drag (default 0.5)."},
        },
    },
    {
        "name": "hover_text",
        "description": "Find text on screen and hover over it to trigger tooltips/menus.",
        "parameters": {
            "text": {"type": "string", "description": "The text to find and hover over."},
            "hover_time": {"type": "number", "description": "Seconds to hover (default 1.0)."},
        },
    },
    {
        "name": "get_active_window",
        "description": "Get info about the currently active/focused window: title, process, position, size.",
        "parameters": {},
    },
]


# ── Implementations ─────────────────────────────────────────────────────────

async def screenshot(filename: str = "screenshot.png") -> ToolResult:
    log.info(f"Taking screenshot: {filename}")
    try:
        filepath = os.path.join(CONFIG.MEDIA_DIR, filename)
        img = pyautogui.screenshot()
        img.save(filepath)
        return ToolResult(success=True, stdout=f"Screenshot saved to: {filepath}", stderr="", return_code=0, image_path=filepath)
    except Exception as e:
        log.error(f"screenshot error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def analyze_screen(region: str = "full") -> ToolResult:
    log.info(f"Analyzing screen (region: {region})...")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot(region))
        if results is None:
            return ToolResult(
                success=False, stdout="",
                stderr="OCR is not available. Use keyboard shortcuts to navigate instead.",
                return_code=1,
            )
        if not results:
            return ToolResult(success=True, stdout="No text detected on screen.", stderr="", return_code=0)

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

        output = f"Screen analysis ({len(results)} words, {len(lines)} lines):\n"
        output += "Format: [center_x, center_y] text_content\n"
        output += "─" * 60 + "\n"
        output += "\n".join(lines[:80])
        if len(lines) > 80:
            output += f"\n... and {len(lines) - 80} more lines"
        return ToolResult(success=True, stdout=output, stderr="", return_code=0)
    except Exception as e:
        log.error(f"analyze_screen error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Screen analysis error: {e}", return_code=1)


async def click_text(text: str, button: str = "left", occurrence: int = 1) -> ToolResult:
    log.info(f"Clicking on text: '{text}'")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot())
        if results is None:
            return ToolResult(success=False, stdout="", stderr=f"OCR unavailable — cannot find '{text}'.", return_code=1)
        if not results:
            return ToolResult(success=False, stdout="", stderr=f"No text found on screen.", return_code=1)

        text_lower = text.lower().strip()
        matches = [r for r in results if r["text"].lower() == text_lower]
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
                    matches.append({"text": combined, "center_x": avg_x, "center_y": avg_y})
                    break

        if not matches:
            visible_texts = list(set(r["text"] for r in results if len(r["text"]) > 1))[:30]
            return ToolResult(success=False, stdout="", stderr=f"Text '{text}' not found. Visible: {', '.join(visible_texts[:20])}", return_code=1)

        idx = min(occurrence - 1, len(matches) - 1)
        match = matches[idx]
        cx, cy = match["center_x"], match["center_y"]
        pyautogui.click(x=cx, y=cy, button=button)
        return ToolResult(success=True, stdout=f"✅ Clicked on '{text}' at ({cx}, {cy}).", stderr="", return_code=0)
    except Exception as e:
        log.error(f"click_text error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"click_text error: {e}", return_code=1)


async def find_text_on_screen(text: str) -> ToolResult:
    log.info(f"Finding text on screen: '{text}'")
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot())
        if results is None:
            return ToolResult(success=False, stdout="", stderr="OCR unavailable.", return_code=1)
        text_lower = text.lower().strip()
        matches = [r for r in results if text_lower in r["text"].lower()]
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
                    matches.append({"text": combined, "center_x": avg_x, "center_y": avg_y, "confidence": 80})
        if matches:
            lines = [f"Found '{text}' at {len(matches)} location(s):"]
            for i, m in enumerate(matches[:10], 1):
                lines.append(f"  {i}. '{m['text']}' → center ({m['center_x']}, {m['center_y']})")
            return ToolResult(success=True, stdout="\n".join(lines), stderr="", return_code=0)
        else:
            visible = list(set(r["text"] for r in results if len(r["text"]) > 1))[:25]
            return ToolResult(success=False, stdout="", stderr=f"'{text}' not found. Visible: {', '.join(visible)}", return_code=1)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def drag_text(source_text: str, target_text: str = None,
                    target_x: int = None, target_y: int = None, duration: float = 0.5) -> ToolResult:
    log.info(f"Drag text: '{source_text}'")
    try:
        from skills.gui_automation import drag_and_drop as _drag
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot())
        if results is None:
            return ToolResult(success=False, stdout="", stderr="OCR unavailable.", return_code=1)
        source_match = None
        for r in results:
            if source_text.lower() in r["text"].lower():
                source_match = r
                break
        if not source_match:
            return ToolResult(success=False, stdout="", stderr=f"Source text '{source_text}' not found.", return_code=1)
        sx, sy = source_match["center_x"], source_match["center_y"]
        if target_text:
            target_match = None
            for r in results:
                if target_text.lower() in r["text"].lower():
                    target_match = r
                    break
            if not target_match:
                return ToolResult(success=False, stdout="", stderr=f"Target text '{target_text}' not found.", return_code=1)
            tx, ty = target_match["center_x"], target_match["center_y"]
        elif target_x is not None and target_y is not None:
            tx, ty = target_x, target_y
        else:
            return ToolResult(success=False, stdout="", stderr="Must provide target_text or target_x/y.", return_code=1)
        return await _drag(sx, sy, tx, ty, duration=duration)
    except Exception as e:
        log.error(f"drag_text error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def hover_text(text: str, hover_time: float = 1.0) -> ToolResult:
    log.info(f"Hover over text: '{text}'")
    try:
        from skills.gui_automation import mouse_hover as _hover
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _ocr_screenshot())
        if results is None:
            return ToolResult(success=False, stdout="", stderr="OCR unavailable.", return_code=1)
        text_lower = text.lower().strip()
        for r in results:
            if text_lower in r["text"].lower():
                return await _hover(r["center_x"], r["center_y"], hover_time)
        visible = [r["text"] for r in results if len(r["text"]) > 1][:20]
        return ToolResult(success=False, stdout="", stderr=f"Text '{text}' not found. Visible: {', '.join(visible)}", return_code=1)
    except Exception as e:
        log.error(f"hover_text error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def get_active_window() -> ToolResult:
    log.info("Getting active window info...")
    try:
        from skills.system_commands import execute_cmd
        ps_script = (
            "Add-Type @'\n"
            "using System;\nusing System.Runtime.InteropServices;\n"
            "public class WinAPI {\n"
            "    [DllImport(\"user32.dll\")] public static extern IntPtr GetForegroundWindow();\n"
            "    [DllImport(\"user32.dll\")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);\n"
            "    [DllImport(\"user32.dll\")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);\n"
            "    [DllImport(\"user32.dll\")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);\n"
            "    public struct RECT { public int Left, Top, Right, Bottom; }\n"
            "}\n'@\n"
            "$hwnd = [WinAPI]::GetForegroundWindow()\n"
            "$sb = New-Object System.Text.StringBuilder 256\n"
            "[void][WinAPI]::GetWindowText($hwnd, $sb, 256)\n"
            "$title = $sb.ToString()\n"
            "$pid = 0\n[void][WinAPI]::GetWindowThreadProcessId($hwnd, [ref]$pid)\n"
            "$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue\n"
            "$rect = New-Object WinAPI+RECT\n[void][WinAPI]::GetWindowRect($hwnd, [ref]$rect)\n"
            "Write-Output \"Title: $title\"\nWrite-Output \"Process: $($proc.ProcessName)\"\n"
            "Write-Output \"PID: $pid\"\nWrite-Output \"Position: ($($rect.Left), $($rect.Top))\"\n"
            "Write-Output \"Size: $($rect.Right - $rect.Left) x $($rect.Bottom - $rect.Top)\"\n"
        )
        result = await execute_cmd(f'powershell -NoProfile -Command "{ps_script}"')
        if result.success:
            return ToolResult(success=True, stdout=result.stdout, stderr="", return_code=0)
        result2 = await execute_cmd(
            'powershell -NoProfile -Command "(Get-Process | Where-Object {$_.MainWindowTitle -ne \\\"\\\"} | Select-Object ProcessName, MainWindowTitle, Id | Format-Table -AutoSize | Out-String).Trim()"'
        )
        return result2
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── Skill Map ───────────────────────────────────────────────────────────────

SKILL_MAP = {
    "screenshot": screenshot,
    "analyze_screen": analyze_screen,
    "click_text": click_text,
    "find_text_on_screen": find_text_on_screen,
    "drag_text": drag_text,
    "hover_text": hover_text,
    "get_active_window": get_active_window,
}
