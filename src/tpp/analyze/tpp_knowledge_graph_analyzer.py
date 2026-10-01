import logging

from tpp.model.tpp import Tpp
from tpp.analyze.tpp_graph_summary_orchestrator import TppGraphSummaryOrchestrator

logger = logging.getLogger(__name__)


class TppKnowledgeGraphAnalyzer:
    """
    Class main purpose is to extracting knowlege and collect the responses for all tpp documents
    """

    def __init__(
        self,
        summary_orchestrator: TppGraphSummaryOrchestrator,
    ):
        self.summary_orchestrator = summary_orchestrator

    def analyze(self, tpps: set[Tpp]) -> None:
        if tpps is None:
            return None

        logger.info(f"analyzing and linking {len(tpps)} tpp(s)")
        success_count = 0
        failed_count = 0
        for tpp in tpps:
            try:
                node_id = tpp.node_id
                logger.info(f"analyzing and linking tpp: {node_id}")
                self.summary_orchestrator.summarize(tpp=tpp)
                logger.info(f"finished analyzing and linking tpp: {node_id}")
                success_count += 1
            except Exception as e:
                logger.warning(e)
                failed_count += 1

        logger.info(
            f"finished extracting knowledge from ({success_count}/{success_count + failed_count}) file(s)"
        )
