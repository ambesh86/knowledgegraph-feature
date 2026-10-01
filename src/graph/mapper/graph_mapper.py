from graph.model.extraction import Extraction
from networkx import Graph


class GraphMapper:
    """
    Class to map extracted knowledge into a graph

    See, https://arxiv.org/html/2404.16130v1
    2.4 Element Summaries → Graph Communities
    """

    def map(self, extraction: Extraction, directed=False) -> Graph:
        graph = Graph(directed=directed)
        for entity in extraction.entities:
            graph.add_node(
                entity,
                value=entity.value,
                type=entity.type,
                description=entity.description,
                id=entity.id,
            )

        for relationship in extraction.relationships:
            graph.add_edge(
                relationship.source,
                relationship.target,
                relation=relationship.relation,
                description=relationship.description,
            )

        return graph
