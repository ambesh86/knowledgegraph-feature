import logging
from pathlib import Path
import time

from document.parse.dir_parser import DirParser
from graph.conf.conf import graph_renderer, graph_summary_orchestrator
from graph.analyze.summary_orchestrator import SummaryOrchestrator
from infra.util.file_util import move_failed, move_succeeded

logger = logging.getLogger(__name__)


class KnowledgeGraphDirAnalyzer:
    """
    Class main purpose is to traverse a directory of files for extracting knowlege and collecting the responses for all documents
    """

    def __init__(
        self,
        data_dir: str,
        include_file_extensions: set[str],
        summary_orchestrator: SummaryOrchestrator,
        max_documents_to_process: int = 999_999,
    ):
        self.graph_render = graph_renderer()
        self.data_dir = data_dir
        self.include_file_extensions = include_file_extensions
        self.max_documents_to_process = max_documents_to_process
        self.summary_orchestrator = summary_orchestrator

    def analyze_dir(self) -> None:
        dir_parser = DirParser(self.data_dir, self.include_file_extensions)
        iterations = 0
        while dir_parser.has_more_documents():
            if (
                self.max_documents_to_process is not None
                and iterations >= self.max_documents_to_process
            ):
                break

            iterations += 1
            parsed_file = dir_parser.parse_next_document()
            try:
                # warning: for testing, slice a few pages, do not check this in
                # parsed_file.pages = parsed_file.pages[0:1]
                page_count = len(parsed_file.pages)
                logger.info(f"file = {parsed_file.path} with page count = {page_count}")
                self.summary_orchestrator.summarize(parsed_file=parsed_file)
                logger.info(
                    f"finished processing file = {parsed_file.path} with page count = {page_count}"
                )
                time.sleep(5)
                move_succeeded(Path(parsed_file.path))
            except Exception as e:
                logger.warning(e)
                move_failed(Path(parsed_file.path))

        logger.info(f"finished extracting knowledge from {iterations} file(s)")
        # self.graph_render.render_extraction(all_extractions)
