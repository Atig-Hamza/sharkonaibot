"""
Skill: Web Browser
Playwright-powered web browsing — search, browse, screenshot, fill forms.
Fast path: uses aiohttp for static pages; Playwright for JS-heavy pages & screenshots.
"""

import asyncio
import os
import re
import html
from typing import Optional
from urllib.parse import quote_plus, urljoin, urlparse

import aiohttp

from config import CONFIG
from logger import log
from skills.system_commands import ToolResult

# ── Shared Playwright state (lazy-init) ─────────────────────────────────────

_playwright = None
_browser = None
_playwright_lock = asyncio.Lock()


async def _get_browser():
    """Lazily start Playwright browser (Chromium, headless)."""
    global _playwright, _browser
    async with _playwright_lock:
        if _browser is None:
            try:
                from playwright.async_api import async_playwright
                _playwright = await async_playwright().start()
                _browser = await _playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
                log.info("Playwright browser started (headless Chromium).")
            except ImportError:
                raise RuntimeError(
                    "Playwright not installed. Run: pip install playwright && playwright install chromium"
                )
        return _browser


# ── HTML helpers ─────────────────────────────────────────────────────────────

def _strip_html(html_text: str, max_len: int = 8000) -> str:
    """Strip HTML tags and collapse whitespace, return clean text."""
    # Remove script/style blocks
    html_text = re.sub(r"<(script|style|head|noscript)[^>]*>.*?</\1>", " ", html_text, flags=re.S | re.I)
    # Remove HTML comments
    html_text = re.sub(r"<!--.*?-->", " ", html_text, flags=re.S)
    # Remove all remaining tags
    html_text = re.sub(r"<[^>]+>", " ", html_text)
    # Decode HTML entities
    html_text = html.unescape(html_text)
    # Collapse whitespace
    html_text = re.sub(r"\s+", " ", html_text).strip()
    if len(html_text) > max_len:
        html_text = html_text[:max_len] + "\n... [content truncated]"
    return html_text


def _extract_links(html_text: str, base_url: str = "") -> list[str]:
    """Extract all <a href> links from HTML."""
    links = re.findall(r'<a[^>]+href=["\']([^"\'#][^"\']*)["\']', html_text, re.I)
    result = []
    for link in links[:30]:
        if link.startswith("http"):
            result.append(link)
        elif base_url and link.startswith("/"):
            parsed = urlparse(base_url)
            result.append(f"{parsed.scheme}://{parsed.netloc}{link}")
    return list(dict.fromkeys(result))  # deduplicate, preserve order


async def _fetch_html(url: str, timeout: int = 15) -> tuple[str, int]:
    """Fast HTTP fetch via aiohttp. Returns (html_body, status_code)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout),
                               allow_redirects=True, ssl=False) as resp:
            body = await resp.text(errors="replace")
            return body, resp.status


# ── Skill Implementations ────────────────────────────────────────────────────

async def web_search(query: str, num_results: int = 8) -> ToolResult:
    """
    Search the web using DuckDuckGo and return top results with titles, URLs, and snippets.
    Fast — no JS required.
    """
    log.info(f"Web search: {query!r}")
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        body, status = await _fetch_html(url)

        # Extract result blocks from DDG HTML
        results = []
        blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            body, re.S
        )
        for href, title, snippet in blocks[:num_results]:
            clean_title = _strip_html(title, 200)
            clean_snippet = _strip_html(snippet, 300)
            # DDG wraps URLs — extract the actual URL
            real_url = re.search(r'uddg=([^&"]+)', href)
            if real_url:
                from urllib.parse import unquote
                href = unquote(real_url.group(1))
            results.append(f"• {clean_title}\n  URL: {href}\n  {clean_snippet}")

        if not results:
            # Fallback: extract any result links
            fallback = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', body)
            results = [f"• {u}" for u in fallback[:num_results]]

        if not results:
            return ToolResult(success=False, stdout="", stderr="No results found.", return_code=1)

        output = f"Search results for: {query!r}\n\n" + "\n\n".join(results)
        return ToolResult(success=True, stdout=output, stderr="", return_code=0)

    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Search error: {e}", return_code=1)


async def web_browse(url: str, use_js: bool = False) -> ToolResult:
    """
    Browse a URL and return the clean text content.
    Fast path: static HTTP fetch (default). Set use_js=True for JavaScript-heavy pages.
    """
    log.info(f"Web browse: {url} (js={use_js})")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # ── Fast path: plain HTTP ────────────────────────────────────────────────
    if not use_js:
        try:
            body, status = await _fetch_html(url)
            text = _strip_html(body)
            links = _extract_links(body, url)
            link_section = ""
            if links:
                link_section = "\n\nLinks found:\n" + "\n".join(f"  {l}" for l in links[:10])
            output = f"URL: {url}\nStatus: {status}\n\n{text}{link_section}"
            return ToolResult(success=True, stdout=output, stderr="", return_code=0)
        except Exception as e:
            # If static fetch fails, fall through to Playwright
            log.warning(f"Static fetch failed for {url}: {e} — trying Playwright")

    # ── Playwright path ──────────────────────────────────────────────────────
    try:
        browser = await _get_browser()
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(1)  # brief wait for dynamic content
            content = await page.content()
            text = _strip_html(content)
            title = await page.title()
            links = _extract_links(content, url)
            link_section = ""
            if links:
                link_section = "\n\nLinks found:\n" + "\n".join(f"  {l}" for l in links[:10])
            output = f"URL: {url}\nTitle: {title}\n\n{text}{link_section}"
            return ToolResult(success=True, stdout=output, stderr="", return_code=0)
        finally:
            await page.close()
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Browse error: {e}", return_code=1)


async def web_screenshot(url: str, full_page: bool = False) -> ToolResult:
    """
    Take a screenshot of a web page using Playwright and save it to media/.
    Returns the image path so it gets sent to Telegram automatically.
    """
    log.info(f"Web screenshot: {url}")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        browser = await _get_browser()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            await page.goto(url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(0.5)

            os.makedirs(CONFIG.MEDIA_DIR, exist_ok=True)
            safe_name = re.sub(r"[^\w]", "_", urlparse(url).netloc)[:30]
            shot_path = os.path.join(CONFIG.MEDIA_DIR, f"screenshot_{safe_name}.png")

            await page.screenshot(path=shot_path, full_page=full_page)
            title = await page.title()
            return ToolResult(
                success=True,
                stdout=f"Screenshot saved: {shot_path}\nTitle: {title}\nURL: {url}",
                stderr="",
                return_code=0,
                image_path=shot_path,
            )
        finally:
            await page.close()
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Screenshot error: {e}", return_code=1)


async def web_interact(url: str, actions: str) -> ToolResult:
    """
    Automate a web page: fill forms, click buttons, extract data.
    'actions' is a JSON list of steps, each with: type (goto/click/fill/select/submit/extract/wait),
    selector (CSS selector), value (text to fill), and optional extract_as (label for extraction).

    Example actions JSON:
    [
      {"type":"goto","value":"https://example.com/login"},
      {"type":"fill","selector":"#username","value":"alice"},
      {"type":"fill","selector":"#password","value":"secret"},
      {"type":"click","selector":"button[type=submit]"},
      {"type":"extract","selector":".dashboard-title","extract_as":"dashboard"}
    ]
    """
    import json as _json
    log.info(f"Web interact: {url}")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        steps = _json.loads(actions) if isinstance(actions, str) else actions
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Invalid actions JSON: {e}", return_code=1)

    try:
        browser = await _get_browser()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        extracted = {}
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")

            for step in steps:
                t = step.get("type", "")
                sel = step.get("selector", "")
                val = step.get("value", "")
                label = step.get("extract_as", sel)

                if t == "goto":
                    await page.goto(val or url, timeout=30000, wait_until="domcontentloaded")
                elif t == "click":
                    await page.click(sel, timeout=10000)
                elif t == "fill":
                    await page.fill(sel, val, timeout=10000)
                elif t == "select":
                    await page.select_option(sel, val, timeout=10000)
                elif t == "submit":
                    locator = page.locator(sel) if sel else page.locator("form")
                    await locator.evaluate("el => el.submit()")
                elif t == "press":
                    await page.keyboard.press(val or "Enter")
                elif t == "wait":
                    ms = int(val) if val else 1000
                    await asyncio.sleep(ms / 1000)
                elif t == "extract":
                    try:
                        el_text = await page.inner_text(sel, timeout=8000)
                        extracted[label] = el_text.strip()
                    except Exception:
                        extracted[label] = "(not found)"
                elif t == "extract_all":
                    try:
                        els = await page.locator(sel).all_inner_texts()
                        extracted[label] = els
                    except Exception:
                        extracted[label] = []

            # Final page state
            final_url = page.url
            title = await page.title()
            body_text = _strip_html(await page.content(), max_len=4000)

            output_parts = [
                f"Final URL: {final_url}",
                f"Title: {title}",
            ]
            if extracted:
                output_parts.append("Extracted data:")
                for k, v in extracted.items():
                    output_parts.append(f"  {k}: {v}")
            output_parts.append(f"\nPage content:\n{body_text}")

            return ToolResult(
                success=True,
                stdout="\n".join(output_parts),
                stderr="",
                return_code=0,
            )
        finally:
            await page.close()
    except Exception as e:
        return ToolResult(success=False, stdout="", stderr=f"Web interact error: {e}", return_code=1)


async def web_extract_data(url: str, target: str) -> ToolResult:
    """
    Smart data extraction from a web page. Describe what you want in 'target'
    (e.g. 'all product prices', 'the main article text', 'all email addresses').
    Uses fast HTTP fetch + regex pattern matching.
    """
    log.info(f"Web extract: {url} — target={target!r}")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        body, status = await _fetch_html(url)
    except Exception:
        try:
            browser = await _get_browser()
            page = await browser.new_page()
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            body = await page.content()
            await page.close()
        except Exception as e:
            return ToolResult(success=False, stdout="", stderr=f"Fetch error: {e}", return_code=1)

    text = _strip_html(body, max_len=20000)
    t = target.lower()

    # Smart pattern extraction
    results = []

    if "email" in t:
        emails = list(set(re.findall(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", body)))
        results = emails[:50]
    elif "price" in t or "cost" in t:
        prices = re.findall(r"[\$€£¥]\s*[\d,]+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*(?:USD|EUR|GBP|MAD)", body)
        results = list(set(prices))[:50]
    elif "phone" in t or "number" in t:
        phones = re.findall(r"(?:\+?\d[\d\s\-\(\)]{7,}\d)", body)
        results = [p.strip() for p in phones[:30]]
    elif "link" in t or "url" in t:
        results = _extract_links(body, url)[:30]
    elif "image" in t or "photo" in t or "img" in t:
        imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', body, re.I)
        results = [urljoin(url, i) for i in imgs[:30]]
    elif "title" in t or "heading" in t:
        headings = re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", body, re.I | re.S)
        results = [_strip_html(h, 200) for h in headings[:20]]
    else:
        # General: return clean page text
        results = [text]

    if not results:
        return ToolResult(success=False, stdout="", stderr=f"No data found for: {target}", return_code=1)

    if isinstance(results, list) and len(results) > 1:
        output = f"Extracted '{target}' from {url}:\n\n" + "\n".join(f"  {i+1}. {r}" for i, r in enumerate(results))
    else:
        output = f"Extracted '{target}' from {url}:\n\n{results[0] if results else ''}"

    return ToolResult(success=True, stdout=output, stderr="", return_code=0)


# ── Skill Definitions ────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": (
            "Search the web using DuckDuckGo. Returns top results with titles, URLs, and snippets. "
            "USE THIS FIRST whenever you need current information, facts, prices, news, or any online data. "
            "Fast, no JS required. Always pick this over manual browsing when searching."
        ),
        "parameters": {
            "query": {"type": "string", "description": "The search query."},
            "num_results": {"type": "integer", "description": "Number of results to return (default 8, max 15)."},
        },
    },
    {
        "name": "web_browse",
        "description": (
            "Browse a URL and return its clean text content and links. "
            "Fast by default (plain HTTP). Set use_js=true only for sites that require JavaScript. "
            "Use after web_search to read a specific page."
        ),
        "parameters": {
            "url": {"type": "string", "description": "The URL to browse."},
            "use_js": {"type": "boolean", "description": "Set true for JS-heavy pages (slower). Default: false."},
        },
    },
    {
        "name": "web_screenshot",
        "description": (
            "Take a full screenshot of a web page using a headless browser and send it to Telegram. "
            "Use when the user wants to see a page visually."
        ),
        "parameters": {
            "url": {"type": "string", "description": "The URL to screenshot."},
            "full_page": {"type": "boolean", "description": "Capture the full scrollable page. Default: false."},
        },
    },
    {
        "name": "web_interact",
        "description": (
            "Automate a web page: fill forms, click buttons, extract data after interaction. "
            "Pass a JSON array of action steps (type: goto/fill/click/select/press/wait/extract/extract_all). "
            "Use for login flows, form submission, multi-step navigation."
        ),
        "parameters": {
            "url": {"type": "string", "description": "Starting URL for the automation."},
            "actions": {
                "type": "string",
                "description": (
                    "JSON array of action steps. Each step: "
                    "{type, selector (CSS), value, extract_as}. "
                    'Types: goto, fill, click, select, press, wait, extract, extract_all.'
                ),
            },
        },
    },
    {
        "name": "web_extract_data",
        "description": (
            "Smart data extractor: describe what to extract in plain English "
            "(e.g. 'all email addresses', 'product prices', 'all links', 'article titles', 'phone numbers'). "
            "Automatically applies the right regex/DOM pattern. Fast — uses HTTP, not JS."
        ),
        "parameters": {
            "url": {"type": "string", "description": "The URL to extract data from."},
            "target": {"type": "string", "description": "What to extract, e.g. 'all email addresses', 'prices', 'links', 'images', 'headings'."},
        },
    },
]

SKILL_MAP = {
    "web_search": web_search,
    "web_browse": web_browse,
    "web_screenshot": web_screenshot,
    "web_interact": web_interact,
    "web_extract_data": web_extract_data,
}
