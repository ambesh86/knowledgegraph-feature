import logging

from patent.pgpub.model.pgpub import Pgpub
from patent.pgpub.analyze.pgpub_graph_summary_orchestrator import (
    PgpubGraphSummaryOrchestrator,
)

logger = logging.getLogger(__name__)


class PgPubKnowledgeGraphAnalyzer:
    """
    Class main purpose is to extracting knowlege and collect the responses for all pgpub documents
    """

    def __init__(
        self,
        summary_orchestrator: PgpubGraphSummaryOrchestrator,
    ):
        self.summary_orchestrator = summary_orchestrator

    def analyze(self, pgpubs: list[Pgpub]) -> None:
        if pgpubs is None:
            return None

        logger.info(f"analyzing and linking {len(pgpubs)} pgpub(s)")
        success_count = 0
        failed_count = 0
        for pgpub in pgpubs:
            try:
                application_number = pgpub.application_number_text
                logger.info(f"analyzing and linking pgpub: {application_number}")
                self.summary_orchestrator.summarize(pgpub=pgpub)
                logger.info(
                    f"finished analyzing and linking pgpub: {application_number}"
                )
                success_count += 1
            except Exception as e:
                logger.warning(e)
                failed_count += 1

        logger.info(
            f"finished extracting knowledge from ({success_count}/{success_count + failed_count}) file(s)"
        )
