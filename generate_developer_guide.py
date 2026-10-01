"""
CSL Behring — Eugene Developer Guide  (PDF + DOCX)
====================================================
Parses docs/DEVELOPER_GUIDE.md, renders every mermaid block to PNG via
@mermaid-js/mermaid-cli (mmdc), and emits two CSL-branded deliverables:

   docs/EUGENE_DEVELOPER_GUIDE.pdf
   docs/EUGENE_DEVELOPER_GUIDE.docx

Run:  python3 generate_developer_guide.py
"""
from __future__ import annotations

import os
import re
import subprocess
import shutil
import tempfile
from typing import List, Tuple

# Renderer + helpers from the existing book generator
from generate_csl_reports import (
    render_pdf, render_docx,
)

REPO_ROOT  = os.path.dirname(os.path.abspath(__file__))
SRC_MD     = os.path.join(REPO_ROOT, "docs", "DEVELOPER_GUIDE.md")
OUT_DIR    = os.path.join(REPO_ROOT, "docs")
TMP_DIR    = os.path.join(REPO_ROOT, ".dev_guide_assets")
MMDC       = "/tmp/node_modules/.bin/mmdc"

DOC_TITLE    = "Eugene Developer Guide"
DOC_SUBTITLE = ("A Complete Walk-through of the Eugene Codebase — "
                "Architecture, Data Flow, Patterns, and Operational Practice")
PDF_NAME  = "EUGENE_DEVELOPER_GUIDE.pdf"
DOCX_NAME = "EUGENE_DEVELOPER_GUIDE.docx"


# ════════════════════════════════════════════════════════════════════════
# Mermaid rendering — mmdc takes .mmd file, writes PNG
# ════════════════════════════════════════════════════════════════════════
MERMAID_CONFIG = """
{
  "theme": "default",
  "themeVariables": {
    "fontFamily": "Helvetica, Arial, sans-serif",
    "primaryColor": "#1B3A6B",
    "primaryTextColor": "#FFFFFF",
    "primaryBorderColor": "#1B3A6B",
    "lineColor": "#2E6DA4",
    "secondaryColor": "#E3F2FD",
    "tertiaryColor": "#F5F5F5",
    "noteBkgColor": "#FFF3E0",
    "noteBorderColor": "#E65100"
  }
}
"""

PUPPETEER_CONFIG = """
{
  "args": ["--no-sandbox", "--disable-setuid-sandbox"]
}
"""


def render_mermaid_block(source: str, idx: int) -> str:
    """Render a mermaid source string to a PNG file, return the PNG path."""
    os.makedirs(TMP_DIR, exist_ok=True)
    mmd_path  = os.path.join(TMP_DIR, f"diagram_{idx:02d}.mmd")
    png_path  = os.path.join(TMP_DIR, f"diagram_{idx:02d}.png")
    cfg_path  = os.path.join(TMP_DIR, "mermaid_config.json")
    pup_path  = os.path.join(TMP_DIR, "puppeteer.json")

    if not os.path.exists(cfg_path):
        with open(cfg_path, "w") as f:
            f.write(MERMAID_CONFIG)
    if not os.path.exists(pup_path):
        with open(pup_path, "w") as f:
            f.write(PUPPETEER_CONFIG)

    with open(mmd_path, "w") as f:
        f.write(source)

    cmd = [
        MMDC,
        "-i", mmd_path,
        "-o", png_path,
        "-c", cfg_path,
        "-p", pup_path,
        "-b", "white",
        "-w", "1600",
        "-s", "2",          # scale factor for crisper output
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(png_path):
        print(f"  !! mermaid render failed for diagram {idx}:")
        print("     STDOUT:", proc.stdout[-300:])
        print("     STDERR:", proc.stderr[-300:])
        return ""
    return png_path


# ════════════════════════════════════════════════════════════════════════
# Markdown parser → BOOK list
# ════════════════════════════════════════════════════════════════════════
HEADER_RE  = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TABLE_DIVIDER_RE = re.compile(r"^\s*\|?\s*[:\- ]+\|[\s:\-|]+$")
LIST_BULLET_RE = re.compile(r"^(\s*)[-*]\s+(.+)$")
LIST_NUMBER_RE = re.compile(r"^(\s*)\d+\.\s+(.+)$")
BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")


def _strip_inline(text: str) -> str:
    """Convert simple inline markdown to ReportLab Paragraph mini-language.

    **bold**     -> <b>bold</b>
    *italic*     -> <i>italic</i>
    `code`       -> <font name='Courier' color='#1B3A6B'>code</font>
    [text](url)  -> <link href='url'>text</link>
    """
    # XML-escape first
    text = (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
    # bold then italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    # avoid eating italics inside list bullets — only run if asterisks pair
    text = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\w)", r"<i>\1</i>", text)
    # inline code
    text = re.sub(r"`([^`]+)`",
                  r"<font name='Courier' color='#1B3A6B'>\1</font>", text)
    # links — drop URL, keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text


def parse_markdown_to_book(md_text: str) -> List[Tuple[str, object]]:
    """Walk the markdown line-by-line and emit a BOOK list.

    Recognised constructs:
      - # H1 → CHAPTER (and serves as the doc's natural section divider)
      - ## H2 → SECTION
      - ### H3 / #### H4 → SUBSEC
      - ```mermaid blocks → IMAGE (rendered via mmdc)
      - ``` other code blocks → CODE
      - | table | rows |   → TABLE
      - bullet (- / *) lists → BULLETS
      - numbered lists → NUMBERED
      - blockquote (>) → CALLOUT
      - paragraphs → PARA
    """
    book: List[Tuple[str, object]] = []
    lines = md_text.split("\n")

    i = 0
    para_buf: List[str] = []
    list_buf: List[str] = []
    list_kind: str = ""        # "" | "BULLETS" | "NUMBERED"
    code_buf: List[str] = []
    code_lang = ""
    in_code = False
    table_buf: List[List[str]] = []
    in_table = False
    quote_buf: List[str] = []
    diagram_idx = 0

    def flush_para():
        nonlocal para_buf
        if para_buf:
            text = " ".join(s.strip() for s in para_buf if s.strip())
            text = _strip_inline(text)
            if text:
                book.append(("PARA", text))
            para_buf = []

    def flush_list():
        nonlocal list_buf, list_kind
        if list_buf and list_kind:
            book.append((list_kind, [_strip_inline(x) for x in list_buf]))
            list_buf, list_kind = [], ""

    def flush_table():
        nonlocal table_buf, in_table
        if table_buf:
            # First row is header
            book.append(("TABLE", table_buf))
        table_buf = []
        in_table = False

    def flush_quote():
        nonlocal quote_buf
        if quote_buf:
            joined = " ".join(s.strip() for s in quote_buf)
            book.append(("CALLOUT", _strip_inline(joined)))
            quote_buf = []

    def flush_all():
        flush_para(); flush_list(); flush_table(); flush_quote()

    while i < len(lines):
        ln = lines[i]
        stripped = ln.rstrip()

        # ─── Code fence ───
        if stripped.startswith("```"):
            if not in_code:
                flush_all()
                in_code = True
                code_lang = stripped[3:].strip().lower()
                code_buf = []
            else:
                # closing fence
                in_code = False
                src = "\n".join(code_buf)
                if code_lang == "mermaid":
                    diagram_idx += 1
                    print(f"  rendering mermaid diagram #{diagram_idx} …")
                    png_path = render_mermaid_block(src, diagram_idx)
                    if png_path:
                        book.append(("IMAGE", png_path))
                        book.append(("CAPTION",
                                     f"Figure {diagram_idx}. From DEVELOPER_GUIDE.md."))
                else:
                    book.append(("CODE", src))
                code_buf = []
                code_lang = ""
            i += 1
            continue
        if in_code:
            code_buf.append(ln)
            i += 1
            continue

        # ─── Header ───
        m = HEADER_RE.match(stripped)
        if m:
            flush_all()
            level = len(m.group(1))
            title = m.group(2)
            # strip embedded markdown
            title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)
            title = re.sub(r"`([^`]+)`", r"\1", title)
            if level == 1:
                book.append(("CHAPTER", title))
            elif level == 2:
                book.append(("CHAPTER", title))
            elif level == 3:
                book.append(("SECTION", title))
            else:
                book.append(("SUBSEC", title))
            i += 1
            continue

        # ─── Horizontal rule (treat as section break, no flowable) ───
        if stripped in ("---", "***", "___"):
            flush_all()
            i += 1
            continue

        # ─── Block quote ───
        m = BLOCKQUOTE_RE.match(stripped)
        if m:
            flush_para(); flush_list(); flush_table()
            quote_buf.append(m.group(1))
            i += 1
            continue
        else:
            if quote_buf:
                flush_quote()

        # ─── Table ───
        if "|" in stripped and stripped.strip().startswith("|"):
            # peek next line for divider
            if not in_table:
                # look ahead for divider line
                if i + 1 < len(lines) and TABLE_DIVIDER_RE.match(lines[i + 1]):
                    flush_para(); flush_list()
                    in_table = True
                    table_buf = []
                    # parse header
                    cells = [c.strip() for c in stripped.strip().strip("|").split("|")]
                    table_buf.append(cells)
                    i += 2  # skip divider
                    continue
            else:
                cells = [c.strip() for c in stripped.strip().strip("|").split("|")]
                table_buf.append(cells)
                i += 1
                continue
        elif in_table and not stripped.strip():
            flush_table()
            i += 1
            continue

        if in_table:
            flush_table()

        # ─── Bullet list ───
        m = LIST_BULLET_RE.match(stripped)
        if m:
            flush_para()
            if list_kind != "BULLETS":
                flush_list()
                list_kind = "BULLETS"
            list_buf.append(m.group(2))
            i += 1
            continue
        # ─── Numbered list ───
        m = LIST_NUMBER_RE.match(stripped)
        if m:
            flush_para()
            if list_kind != "NUMBERED":
                flush_list()
                list_kind = "NUMBERED"
            list_buf.append(m.group(2))
            i += 1
            continue
        # Indented continuation of list item → append to previous bullet
        if list_buf and stripped.startswith("  ") and stripped.strip():
            list_buf[-1] += " " + stripped.strip()
            i += 1
            continue
        if list_buf:
            flush_list()

        # ─── Blank line: paragraph separator ───
        if not stripped.strip():
            flush_para()
            i += 1
            continue

        # ─── Plain paragraph line ───
        para_buf.append(stripped)
        i += 1

    flush_all()
    return book


# ════════════════════════════════════════════════════════════════════════
# Driver
# ════════════════════════════════════════════════════════════════════════
def main():
    print(f"Reading  {SRC_MD}")
    with open(SRC_MD) as f:
        md = f.read()

    print("Parsing markdown and rendering mermaid diagrams …")
    book = parse_markdown_to_book(md)

    # Front-matter additions: keep the natural H1 from the source as the
    # first chapter.  Optionally, prepend a "How to Read This Guide" note.
    pdf_path  = os.path.join(OUT_DIR, PDF_NAME)
    docx_path = os.path.join(OUT_DIR, DOCX_NAME)

    print(f"Generating PDF  -> {pdf_path}")
    render_pdf(book, DOC_TITLE, DOC_SUBTITLE, pdf_path)
    print(f"Generating DOCX -> {docx_path}")
    render_docx(book, DOC_TITLE, DOC_SUBTITLE, docx_path)

    print()
    print("Developer Guide deliverables generated:")
    print(f"   - docs/{PDF_NAME}")
    print(f"   - docs/{DOCX_NAME}")


if __name__ == "__main__":
    main()
