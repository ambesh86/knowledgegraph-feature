"""Render docs/eugene_presentation_talking_points.md -> .pdf"""
from pathlib import Path
from markdown_pdf import MarkdownPdf, Section

ROOT = Path(__file__).parent
MD = ROOT / "eugene_presentation_talking_points.md"
PDF = ROOT / "eugene_presentation_talking_points.pdf"

CSS = """
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
       line-height: 1.4; color: #1a1a1a; font-size: 11px; }
h1 { color: #0b3d91; font-size: 20px; margin-bottom: 2px; }
h3 { color: #0b3d91; font-size: 13px; margin-top: 14px; border-bottom: 1px solid #d0d7de; padding-bottom: 2px; }
p { margin: 5px 0; }
strong { color: #0b3d91; }
blockquote { border-left: 3px solid #0b3d91; margin-left: 0; padding: 6px 12px;
             background: #f6f8fa; font-style: italic; color: #333; }
code { background: #f4f4f6; padding: 1px 4px; border-radius: 3px;
       font-family: 'SF Mono', Menlo, monospace; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 10px; }
th, td { border: 1px solid #d0d7de; padding: 4px 8px; text-align: left; }
th { background: #f6f8fa; color: #0b3d91; }
hr { border: 0; border-top: 1px solid #e1e4e8; margin: 12px 0; }
"""

def main():
    pdf = MarkdownPdf(toc_level=0, optimize=True)
    pdf.meta["title"] = "Eugene — Presentation Talking Points"
    pdf.add_section(Section(MD.read_text(encoding="utf-8")), user_css=CSS)
    pdf.save(str(PDF))
    print(f"wrote {PDF} ({PDF.stat().st_size/1024:.1f} KB)")

if __name__ == "__main__":
    main()
