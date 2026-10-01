import logging

from pubmed.conf.conf import _pubmed_orchestrator

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    download pubmed pdf files for processing
    """

    pubmed_orchestrator = _pubmed_orchestrator()
    terms = ["aGVHD", 
             "Systemic Lupus Erythematosus", 
             "Rheumatoid Arthritis", 
             "Hemophilia A", 
             "Hemophilia B", 
             "von Willebrand Disease",
             "Guillain-Barré Syndrome"]
    for term in terms:
        logger.info(f"search and download for term {term}")
        pubmed_orchestrator.search_and_download(term)
    logger.info(f"pubmed refresh finished...")


if __name__ == "__main__":
    main()
