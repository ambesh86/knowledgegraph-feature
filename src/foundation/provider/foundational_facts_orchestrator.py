import logging

from foundation.provider.foundational_n_hop_provider import FoundationalNHopProvider
from foundation.mapper.facts_mapper import FactsMapper
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class FoundationalFactsOrchestrator:
    """
    Query eugene graph for n hop subgraph and convert nodes and relationship into facts
    These facts are in sentence form, suitable to feed into an LLM
    """

    def __init__(
        self,
        foundational_n_hop_provider: FoundationalNHopProvider,
        facts_mapper: FactsMapper,
    ):
        self.foundational_n_hop_provider = foundational_n_hop_provider
        self.facts_mapper = facts_mapper

    @log_time
    def find_facts_by_start_id(
        self, start_id: str, n_hop: int, page: int, page_size: int
    ) -> set[str] | None:
        graph = self.foundational_n_hop_provider.find_subgraph_by_start_id_and_end_id(
            start_id=start_id, n_hop=n_hop, page=page, page_size=page_size
        )
        if graph is None:
            return None
        return self.facts_mapper.map(graph)
