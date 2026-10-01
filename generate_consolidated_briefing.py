"""
CSL Behring — Eugene Consolidated Programme Briefing
=====================================================
Single client-presentation document combining:
   1. Overview of Eugene
   2. Scope and Capabilities
   3. Detailed Current-State Architecture
   4. Gaps Identified
   5. Technical Recommendations

Run:  python3 generate_consolidated_briefing.py
"""
import os

from generate_csl_reports import render_pdf, render_docx
from csl_book_content_consolidated import (
    DOC_TITLE, DOC_SUBTITLE, DOC_FILE_PDF, DOC_FILE_DOCX, CONSOLIDATED_BOOK,
)

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")


def main():
    pdf_path  = os.path.join(DOCS_DIR, DOC_FILE_PDF)
    docx_path = os.path.join(DOCS_DIR, DOC_FILE_DOCX)

    print(f"-- {DOC_TITLE}")
    print(f"   PDF  -> {pdf_path}")
    render_pdf(CONSOLIDATED_BOOK, DOC_TITLE, DOC_SUBTITLE, pdf_path)
    print(f"   DOCX -> {docx_path}")
    render_docx(CONSOLIDATED_BOOK, DOC_TITLE, DOC_SUBTITLE, docx_path)
    print()
    print("Consolidated briefing generated:")
    print(f"   - docs/{DOC_FILE_PDF}")
    print(f"   - docs/{DOC_FILE_DOCX}")


if __name__ == "__main__":
    main()
