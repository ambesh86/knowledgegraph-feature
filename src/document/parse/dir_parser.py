import logging

from document.parse.document_parser import DocumentParser
from document.parse.parsed_file import ParsedFile
from infra.util.file_util import list_data_files

logger = logging.getLogger(__name__)


class DirParser:
    def __init__(
        self,
        dir: str,
        include_file_extensions: set[str],
    ):
        self.document_parser = DocumentParser()
        self.dir = dir
        self.include_file_extensions = include_file_extensions
        self.loaded_data_files = False
        self.data_files = None

    def parse_next_document(self) -> ParsedFile:
        path = self.data_files.pop()
        logger.debug(f"parsing {path}")
        pages = self.document_parser.parse(path)
        logger.debug(f"found {len(pages)}")
        return ParsedFile(path, pages)

    def has_more_documents(self) -> bool:
        if not self.loaded_data_files:
            self.data_files = list_data_files(self.dir, self.include_file_extensions)
            self.loaded_data_files = True
            logger.info(f"loaded {len(self.data_files)} file(s)")

        return len(self.data_files) > 0
