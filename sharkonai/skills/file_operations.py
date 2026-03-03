"""
Skill: File Operations
Read, write, append, list, find, create, and send files.
"""

import os

from config import CONFIG
from logger import log
from skills.system_commands import ToolResult, execute_cmd


# ── Definitions ─────────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
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
]


# ── Implementations ─────────────────────────────────────────────────────────

async def read_file_tool(path: str, start_line: int = None, end_line: int = None) -> ToolResult:
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


# Directories where write_file is blocked (use develop_skill for skills)
_BLOCKED_WRITE_DIRS = {
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)))),              # skills/
    os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills_by_Sharkon")),  # skills_by_Sharkon/
}


async def write_file_tool(path: str, content: str) -> ToolResult:
    """Write content to a file."""
    log.info(f"Writing file: {path}")
    try:
        abs_path = os.path.abspath(path)
        # Block writing into protected skill directories
        for blocked in _BLOCKED_WRITE_DIRS:
            if os.path.normpath(os.path.dirname(abs_path)) == blocked:
                return ToolResult(
                    success=False, stdout="",
                    stderr=(
                        f"Cannot write directly to '{os.path.basename(os.path.dirname(abs_path))}/'. "
                        "Use the develop_skill tool to create or update_skill to modify skills."
                    ),
                    return_code=1,
                )
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


async def create_file_tool(filename: str, content: str, caption: str = "") -> ToolResult:
    """Create a text-based file and return it for sending via Telegram."""
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
            file_path=filepath,
        )
    except Exception as e:
        log.error(f"create_file error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Failed to create file: {e}", return_code=1)


async def create_pdf(filename: str, title: str, content: str, caption: str = "") -> ToolResult:
    """Create a PDF document with title and content."""
    log.info(f"Creating PDF: {filename}")
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    filepath = os.path.join(CONFIG.MEDIA_DIR, filename)
    try:
        try:
            from fpdf import FPDF
        except ImportError:
            log.info("fpdf2 not found, installing...")
            install_result = await execute_cmd("pip install fpdf2")
            if not install_result.success:
                return ToolResult(success=False, stdout="", stderr=f"Failed to install fpdf2: {install_result.stderr}", return_code=1)
            from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

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

        pdf.set_font(title_font, "B", 18)
        pdf.cell(0, 12, title, ln=True, align="C")
        pdf.ln(8)
        pdf.set_draw_color(100, 100, 100)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(6)

        for line in content.split("\n"):
            if line.startswith("## "):
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

        pdf.ln(10)
        pdf.set_font(body_font, "", 8)
        pdf.set_text_color(150, 150, 150)
        from datetime import datetime
        pdf.cell(0, 5, f"Generated by SharkonAI — {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
        pdf.output(filepath)

        size = os.path.getsize(filepath)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
        return ToolResult(success=True, stdout=f"✅ PDF created: {filename} ({size_str})", stderr="", return_code=0, file_path=filepath)
    except Exception as e:
        log.error(f"create_pdf error: {e}")
        return ToolResult(success=False, stdout="", stderr=f"Failed to create PDF: {e}", return_code=1)


async def send_file_tool(path: str, caption: str = "") -> ToolResult:
    """Send any file to the user as a Telegram document."""
    log.info(f"Sending file: {path}")
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, stdout="", stderr=f"File not found: {path}", return_code=1)
        size = os.path.getsize(path)
        if size > 50 * 1024 * 1024:
            return ToolResult(success=False, stdout="", stderr=f"File too large ({size / (1024*1024):.1f} MB). Telegram limit is 50 MB.", return_code=1)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
        return ToolResult(success=True, stdout=f"Sending file: {os.path.basename(path)} ({size_str})", stderr="", return_code=0, file_path=path)
    except Exception as e:
        log.error(f"send_file error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


async def send_image(path: str, caption: str = "") -> ToolResult:
    """Send an image file to the user."""
    log.info(f"Sending image: {path}")
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, stdout="", stderr=f"Image file not found: {path}", return_code=1)
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff')
        if not path.lower().endswith(valid_extensions):
            return ToolResult(success=False, stdout="", stderr=f"Not a supported image format. Supported: {', '.join(valid_extensions)}", return_code=1)
        size = os.path.getsize(path)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
        return ToolResult(success=True, stdout=f"Sending image: {os.path.basename(path)} ({size_str})", stderr="", return_code=0, image_path=path)
    except Exception as e:
        log.error(f"send_image error: {e}")
        return ToolResult(success=False, stdout="", stderr=str(e), return_code=1)


# ── Skill Map ───────────────────────────────────────────────────────────────

SKILL_MAP = {
    "read_file": read_file_tool,
    "write_file": write_file_tool,
    "append_file": append_file,
    "list_directory": list_directory,
    "find_files": find_files,
    "create_file": create_file_tool,
    "create_pdf": create_pdf,
    "send_file": send_file_tool,
    "send_image": send_image,
}
