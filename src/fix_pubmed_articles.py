import logging

from dotenv import load_dotenv

from graph.analyze.knowledge_graph_dir_analyzer import KnowledgeGraphDirAnalyzer

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    process pubmed articles and update missing field not fetched in the original ingest
     the ingest llms calls are expensive so this is better to update the nodes vs reingesting
    """
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Updated existing pubmed articles and related nodes. Adds keywords and embeddings"
    )
    parser.add_argument(
        "--fix-by-pmcids", action="store_true", required=False, help="pmcids to update"
    )

    args = parser.parse_args()

    load_dotenv()

    if args.fix_by_pmcids:
        pmcids = generate_pmcids()
        fix_pmcids(pmcids)
    else:
        data_dir = "./resources/data/pubmed"
        include_file_extensions = {".pdf"}
        max_documents_to_process = 9999
        build_knowledge_graph(
            data_dir, include_file_extensions, max_documents_to_process
        )


def generate_pmcids() -> list[str]:
    return ["11986404"]
    # return [
    #     "11759061",
    #     "11759780",
    #     "11765694",
    #     "11765773",
    #     "11770326",
    #     "11780712",
    #     "11781120",
    #     "11782851",
    #     "11787463",
    #     "11787516",
    #     "11787635",
    #     "11787650",
    #     "11788621",
    #     "11788778",
    #     "11788946",
    #     "11790519",
    #     "11792258",
    #     "11792665",
    #     "11794699",
    #     "11795545",
    #     "11796136",
    #     "11796191",
    #     "11796319",
    #     "11796389",
    #     "11798761",
    #     "11798763",
    #     "11800340",
    #     "11800379",
    #     "11800397",
    #     "11801364",
    #     "11801798",
    #     "11802235",
    #     "11802543",
    #     "11803641",
    #     "11803812",
    #     "11804970",
    #     "11805391",
    #     "11805675",
    #     "11805716",
    #     "11805920",
    #     "11806117",
    #     "11806235",
    #     "11806339",
    #     "11806481",
    #     "11806493",
    #     "11806600",
    #     "11806621",
    #     "11806646",
    #     "11806675",
    #     "11806677",
    #     "11806705",
    #     "11806711",
    #     "11806729",
    #     "11806736",
    #     "11806757",
    #     "11806790",
    #     "11806872",
    # ]


def fix_pmcids(pmcids: list[str]) -> None:
    orchestrator = pubmed_fix_orchestrator()
    orchestrator.update_articles(pmcids)


def build_knowledge_graph(
    data_dir: str,
    include_file_extensions: set[str],
    max_documents_to_process: int,
):
    dir_analyzer = KnowledgeGraphDirAnalyzer(
        data_dir,
        include_file_extensions,
        summary_orchestrator=pubmed_fix_orchestrator(),
        max_documents_to_process=max_documents_to_process,
    )
    dir_analyzer.analyze_dir()


if __name__ == "__main__":
    main()
