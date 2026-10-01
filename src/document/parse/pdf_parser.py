import logging
from io import BytesIO

import pymupdf

from document.parse.parser import Parser
from infra.util.file_util import to_buffered_reader

logger = logging.getLogger(__name__)


class PdfParser(Parser):
    """
    Class that knows how to parse a single PDF document and its pages
    """

    def __init__(self):
        """
        define known extensions this class can support parsing
        """
        super().__init__()
        self.extensions = {".pdf"}

    def parse(self, path: str) -> list[dict[str, str]]:
        """
        Extract PDF pages into a batch document for an LLM/RAG

        Attempts to extract content in natural reading order
        https://pymupdf.readthedocs.io/en/latest/recipes-text.html#how-to-extract-text-in-natural-reading-order
        """
        extracted = []
        buffered_reader = to_buffered_reader(path)
        logger.debug(f"opened {buffered_reader}")
        pdf_doc = pymupdf.Document(stream=BytesIO(buffered_reader.read()))
        for page in pdf_doc:
            logger.debug(f"Extracting Page: {page.number}")
            page_text = page.get_text(sort=True)  # encode("utf8")  # type: ignore
            page_number = (int(page.number) + 1) if (page.number is not None) else 0
            extracted.append(
                {
                    "page_number": page_number,
                    "total_page_count": pdf_doc.page_count,
                    "document_name": path,
                    "body": page_text,
                }
            )

        return extracted
