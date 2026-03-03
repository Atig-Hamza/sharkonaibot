"""
Skill: Network & Web
HTTP requests, file downloads.
"""

import asyncio
import os
import urllib.request

from config import CONFIG
from logger import log
from skills.system_commands import ToolResult


# ── Definitions ─────────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
    {
        "name": "http_request",
        "description": "Make an HTTP GET request to a URL and return the response body.",
        "parameters": {
            "url": {"type": "string", "description": "The URL to request."},
            "headers": {"type": "object", "description": "Optional HTTP headers as key-value pairs."},
        },
    },
    {
        "name": "download_file",
        "description": "Download a file from a URL and save it to disk.",
        "parameters": {
            "url": {"type": "string", "description": "The URL of the file to download."},
            "save_path": {"type": "string", "description": "Where to save the downloaded file."},
        },
    },
]


# ── Implementations ─────────────────────────────────────────────────────────

async def http_request(url: str, headers: dict = None) -> ToolResult:
    log.info(f"HTTP request: {url}")
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "SharkonAI/1.0")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=30))
        body = response.read().decode("utf-8", errors="replace")
        max_len = 10000
        if len(body) > max_len:
            body = body[:max_len] + "\n... [response truncated]"
        result = f"Status: {response.status}\nURL: {url}\n\n{body}"
        return ToolResult(success=True, stdout=result, stderr="", return_code=0)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"HTTP error: {e}", return_code=1)


async def download_file(url: str, save_path: str = "") -> ToolResult:
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
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff')
        img_path = save_path if save_path.lower().endswith(image_extensions) else ""
        return ToolResult(success=True, stdout=f"Downloaded {size_str} to {save_path}", stderr="", return_code=0, image_path=img_path)
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Download error: {e}", return_code=1)


# ── Skill Map ───────────────────────────────────────────────────────────────

SKILL_MAP = {
    "http_request": http_request,
    "download_file": download_file,
}
