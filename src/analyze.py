import logging

from document.analyze.summarization_dir_analyzer import SummarizationDirAnalyzer
from graph.analyze.knowledge_graph_dir_analyzer import KnowledgeGraphDirAnalyzer
from graph.conf.conf import graph_summary_orchestrator

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    data_dir = "./resources/data"
    include_file_extensions = {".pdf"}
    max_workers = 3
    max_documents_to_process = 9999
    # summarize(data_dir, include_file_extensions, max_workers, max_documents_to_process)
    knowledge_graph(
        data_dir, include_file_extensions, max_workers, max_documents_to_process
    )


def knowledge_graph(
    data_dir: str,
    include_file_extensions: set[str],
    max_workers: int,
    max_documents_to_process: int,
):
    dir_analyzer = KnowledgeGraphDirAnalyzer(
        data_dir,
        include_file_extensions,
        summary_orchestrator=graph_summary_orchestrator(max_workers=max_workers),
        max_documents_to_process=max_documents_to_process,
    )
    dir_analyzer.analyze_dir()


def summarize(
    data_dir: str,
    include_file_extensions: set[str],
    max_workers: int,
    max_documents_to_process: int,
):
    dir_analyzer = SummarizationDirAnalyzer(
        data_dir,
        include_file_extensions,
        max_workers=max_workers,
        max_documents_to_process=max_documents_to_process,
    )
    dir_analyzer.analyze_dir()


if __name__ == "__main__":
    main()
