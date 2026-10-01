import logging

from document.parse.dir_parser import DirParser
from document.analyze.document_analyzer import DocumentAnalyzer
from infra.llm.llm_factory import LlmFactory
from infra.llm.prompt.generate import (
    generate_business_value_input_params,
    generate_enrich_suggestions_input_params,
    generate_industry_input_params,
    generate_monetary_value_input_params,
    generate_questions_input_params,
)
from infra.llm.prompt.prompt_response import PromptResponse
from infra.util.file_util import write_report

logger = logging.getLogger(__name__)


class SummarizationDirAnalyzer:
    """
    Class main purpose is to traverse a directory of files for parsing, analyzing, and collecting the responses for all documents
    """

    def __init__(
        self,
        data_dir: str,
        include_file_extensions: set[str],
        max_workers: int,
        max_documents_to_process: int = None,
    ):
        # model_name = "mistral"
        # model_name = "llama3.1"
        # model_name = "llama3.1:70b"
        # self.model = LlmFactory.local_instance(model=model_name)
        self.model_name = "meta.llama3-70b-instruct-v1:0"
        self.model = LlmFactory.bedrock_instance(
            provider="meta", model_id=self.model_name
        )
        input_params = [
            generate_industry_input_params(""),
            generate_business_value_input_params(""),
            generate_monetary_value_input_params(""),
            generate_questions_input_params(""),
            generate_enrich_suggestions_input_params(""),
        ]
        self.document_analyzer = DocumentAnalyzer(
            self.model, input_params=input_params, max_workers=max_workers
        )
        self.data_dir = data_dir
        self.include_file_extensions = include_file_extensions
        self.max_documents_to_process = max_documents_to_process

    def analyze_dir(self) -> None:
        dir_parser = DirParser(self.data_dir, self.include_file_extensions)
        all_responses = []
        iterations = 0
        while dir_parser.has_more_documents():
            if (
                self.max_documents_to_process is not None
                and iterations >= self.max_documents_to_process
            ):
                break
            iterations += 1
            parsed_file = dir_parser.parse_next_document()
            page_count = len(parsed_file.pages)
            logger.info(f"page count = {page_count}")
            contents = [page["body"] for page in parsed_file.pages]
            batch_responses = self.document_analyzer.analyze_document_tasks(contents)
            for response in batch_responses:
                logger.info(
                    f"finished with analyzing path: {parsed_file.path} section: {response.title}"
                )
            all_responses.extend(batch_responses)
            report = [
                PromptResponse("Model", "What model was used?", self.model_name),
                PromptResponse("File", "What file was analyzed?", parsed_file.path),
            ] + all_responses
            write_report(f"report-{iterations}", report)

        logger.info(f"finished analyzing {iterations} file(s)")
