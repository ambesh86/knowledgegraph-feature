from argparse import Namespace
import logging

from dotenv import load_dotenv

from pubmed.conf.conf import pubmed_orchestrator
from pubmed.provider.pubmed_orchestrator import PubmedOrchestrator

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    download pubmed pdf files for processing
    """
    args = build_args_parser()

    load_dotenv(verbose=True)

    orchestrator = pubmed_orchestrator()
    if args.download_by_pmcids:
        download(pmcids=args.download_by_pmcids, orchestrator=orchestrator)

    if args.search_terms:
        search_and_download(args.search_terms, orchestrator=orchestrator)

    logger.info(f"pubmed download finished.")


def search_and_download(terms: list[str], orchestrator: PubmedOrchestrator) -> None:
    logger.info(f"searching {len(terms)} term(s)")
    for term in terms:
        logger.info(f"search and download for term {term}")
        orchestrator.search_and_download(term)


def download(pmcids: list[str], orchestrator: PubmedOrchestrator) -> None:
    orchestrator.fetch_and_download(pmcids=pmcids)
    logger.info(f"pubmed refresh finished...")


def build_args_parser() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Updated existing pubmed articles and related nodes. Adds keywords and embeddings"
    )
    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--download-by-pmcids",
        nargs="+",
        type=str,
        required=False,
        help="list of pmcids to download",
    )
    # terms = [
    #     "aGVHD",
    #     "Systemic Lupus Erythematosus",
    #     "Rheumatoid Arthritis",
    #     "Hemophilia A",
    #     "Hemophilia B",
    #     "von Willebrand Disease",
    #     "Guillain-Barré Syndrome"
    # ]
    group.add_argument(
        "--search-terms",
        nargs="+",
        type=str,
        required=False,
        help="search terms to query before downloading pubmed files. Pass a list of drugs or diseases e.g. 'von Willebrand Disease' 'aGVHD'",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
