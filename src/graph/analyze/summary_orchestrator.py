from abc import abstractmethod
import logging

from document.parse.parsed_file import ParsedFile

logger = logging.getLogger(__name__)


class SummaryOrchestrator:
    @abstractmethod
    def summarize(self, parsed_file: ParsedFile) -> None:
        raise NotImplementedError
