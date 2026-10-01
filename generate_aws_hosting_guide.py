"""
Render the AWS hosting runbook into PDF + DOCX using the existing CSL
book template.
"""
import os
from generate_csl_reports import render_pdf, render_docx
from csl_book_content_aws_hosting import (
    DOC_TITLE, DOC_SUBTITLE, DOC_FILE_PDF, DOC_FILE_DOCX, BOOK,
)

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")


def main():
    pdf = os.path.join(DOCS_DIR, DOC_FILE_PDF)
    docx = os.path.join(DOCS_DIR, DOC_FILE_DOCX)
    print(f"-- {DOC_TITLE}")
    print(f"   PDF  -> {pdf}")
    render_pdf(BOOK, DOC_TITLE, DOC_SUBTITLE, pdf)
    print(f"   DOCX -> {docx}")
    render_docx(BOOK, DOC_TITLE, DOC_SUBTITLE, docx)
    print("\nDone.")


if __name__ == "__main__":
    main()
