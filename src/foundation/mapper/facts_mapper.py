import logging

from foundation.model.graph.graph import Graph
from foundation.model.graph.node import Node
from foundation.model.graph.relationship import Relationship
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class FactsMapper:

    @log_time
    def map(self, graph: Graph) -> set[str]:
        if graph is None:
            return set()

        node_map = {node.id: node for node in graph.nodes}
        logger.debug(f"node map: {node_map}")

        all_relationships = graph.relationships
        facts = set()
        for node_id in all_relationships.keys():
            start_node_rels = all_relationships[node_id]
            start_node = node_map[node_id]
            for current_rel in start_node_rels:
                end_node = node_map[current_rel.id]
                fact = self._to_fact(start_node, current_rel, end_node)
                facts.add(fact)

        logger.info(f"generated {len(facts)} fact(s)")
        return facts

    def _to_fact(self, start_node: Node, rel: Relationship, end_node: Node) -> str:
        relationship = self._label_to_text(rel.rel)
        start_label = self._label_to_text(set(start_node.labels).pop())
        fixed_relationship = self._remove_redundant(start_label, relationship).strip()
        end_label = self._label_to_text(set(end_node.labels).pop()).strip()
        start_value = start_node.value
        end_value = end_node.value
        fixed_end_label = self._remove_redundant(relationship, end_label).strip()

        rels_clause = (
            f"has {fixed_relationship.strip()} {fixed_end_label.strip()}"
            if len(fixed_end_label) > 0
            else f"has {fixed_relationship.strip()}"
        )
        return f"{start_label.strip().capitalize()} {start_value.strip()} {rels_clause}, {end_value.strip()}"

    def _label_to_text(self, label: str) -> str:
        return label.replace("_", " ")

    def _remove_redundant(self, clause1: str, clause2: str) -> str:
        """
        remove redundant word from clause 2
        """

        splits1 = clause1.split(" ")
        splits2 = clause2.split(" ")

        if len(splits2) > 1 and splits2[0] == splits2[1]:
            # fix sentence structure for values like drug_drug
            return f"relationship to {splits2[1]}"

        fixed = splits2
        logger.info(f"checking for redundant words: {splits2}")
        if splits1[-1] == splits2[0]:
            # if last word is the same as next word, remove
            fixed = splits2[1 : len(splits2)]

        logger.info(f"fixed redundant {fixed}")
        return " ".join(fixed).strip()
