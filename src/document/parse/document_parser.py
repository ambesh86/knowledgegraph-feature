import logging

from document.parse.parser import Parser
from document.parse.pdf_parser import PdfParser
from infra.util.file_util import parse_for_file_ext

logger = logging.getLogger(__name__)


class DocumentParser:
    def __init__(self):
        """
        initialize a list of parsers that know how to process known file extensions
        """
        self.parsers = [PdfParser()]

    def parse(self, path: str) -> list[dict[str, str]]:
        file_ext = parse_for_file_ext(path)
        parser = self._find_first_supported(file_ext)
        logger.debug(f"found parser {parser} for extension: {file_ext}")
        return parser.parse(path)

    def _find_first_supported(self, file_ext: str) -> Parser:
        for parser in self.parsers:
            if parser._is_supported_extension(file_ext):
                return parser

        raise Exception(f"No parser found for extension {file_ext}")
