from dataclasses import dataclass

from foundation.model.graph.node import Node
from foundation.model.graph.relationship import Relationship


@dataclass(frozen=True, unsafe_hash=True)
class Graph:
    """
    subgraph adjacency list, used to store the results of an N hop eugene graph query
    """

    node_count: int
    nodes: set[Node]
    relationships: dict[str, set[Relationship]]
