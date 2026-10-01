import logging
from abc import abstractmethod

from networkx import Graph

from graph.model.entity import Entity

logger = logging.getLogger(__name__)


class CommunityProvider:
    """
    Class to build graph communities

    2.4 Element Summaries → Graph Communities
    See, https://arxiv.org/html/2404.16130v1
    """

    @abstractmethod
    def build_communities_multilevel(
        self, graph: str
    ) -> list[list[Graph]] | list[list[set[Entity]]]:
        raise NotImplementedError
