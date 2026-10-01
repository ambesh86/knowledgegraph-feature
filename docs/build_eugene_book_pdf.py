"""Build docs/eugene_python_book.pdf from docs/eugene_python_book.md."""
from pathlib import Path
from markdown_pdf import MarkdownPdf, Section

ROOT = Path(__file__).parent
MD = ROOT / "eugene_python_book.md"
PDF = ROOT / "eugene_python_book.pdf"

CSS = """
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
       line-height: 1.5; color: #1a1a1a; }
h1 { color: #0b3d91; border-bottom: 2px solid #0b3d91; padding-bottom: 4px;
     page-break-before: always; }
h1:first-of-type { page-break-before: avoid; }
h2 { color: #0b3d91; margin-top: 1.4em; }
h3 { color: #1f4e8c; }
code { background: #f4f4f6; padding: 1px 4px; border-radius: 3px;
       font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: 0.92em; }
pre { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px;
      padding: 10px; overflow-x: auto; font-size: 0.85em; line-height: 1.35; }
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #d0d7de; padding: 6px 10px; }
th { background: #f6f8fa; text-align: left; }
blockquote { border-left: 3px solid #0b3d91; margin-left: 0; padding-left: 12px;
             color: #444; font-style: italic; }
hr { border: 0; border-top: 1px solid #d0d7de; margin: 2em 0; }
"""

def main():
    text = MD.read_text(encoding="utf-8")
    pdf = MarkdownPdf(toc_level=2, optimize=True)
    pdf.meta["title"] = "Eugene: A Practical Python Mastery Book"
    pdf.meta["author"] = "Eugene Team"
    pdf.add_section(Section(text, toc=True), user_css=CSS)
    pdf.save(str(PDF))
    print(f"wrote {PDF}  ({PDF.stat().st_size/1024:.1f} KB)")

if __name__ == "__main__":
    main()
