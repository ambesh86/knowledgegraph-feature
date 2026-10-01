import logging

from document.analyze.document_analyzer import DocumentAnalyzer
from document.parse.parsed_file import ParsedFile
from infra.llm.prompt.prompt_response import PromptResponse
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


class ExtractionProvider:
    """
    Class to extract knowldge
    2.2 Text Chunks → Element Instances

    See, https://arxiv.org/html/2404.16130v1
    """

    def __init__(self, extraction_document_analyzer: DocumentAnalyzer):
        self.extraction_document_analyzer = extraction_document_analyzer

    def extract(self, parsed_file: Extraction) -> list[PromptResponse]:
        return self._extract(parsed_file=parsed_file)

    def _extract(self, parsed_file: ParsedFile) -> list[PromptResponse]:
        pages = [page["body"] for page in parsed_file.pages]
        batch_responses = self.extraction_document_analyzer.analyze_document_pages(
            pages
        )
        return batch_responses
