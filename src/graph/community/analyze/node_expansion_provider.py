import logging

from graph.model.extraction import Extraction
from graph.mapper.id_generator import IdGenerator
from graph.model.entity import Entity
from graph.model.relationship import Relationship


logger = logging.getLogger(__name__)


class NodeExpansionProvider:
    def __init__(self):
        self._intermediate_node_type = "system_type"

    def expand_type_nodes(self, extraction: Extraction) -> Extraction:
        """
        Method to expand node properties into their own connector or intermediate nodes
        This is related to the hyperedge concept
        See, https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/
        """
        if extraction is None:
            return extraction

        intermediate_nodes = self._build_intermediate_nodes(extraction.entities)
        intermediate_links = self._build_intermediate_links(
            entities=extraction.entities, intermediate_nodes=intermediate_nodes
        )
        extraction.entities.update(intermediate_nodes)
        extraction.relationships.update(intermediate_links)
        return extraction

    def _build_intermediate_nodes(self, entities: set[Entity]) -> set[Entity]:
        unique_types = set()
        for entity in entities:
            entity_type = entity.type
            unique_types.add(entity_type)

        intermediate_nodes = self._generate_intermediate_nodes(
            unique_types=unique_types
        )
        return intermediate_nodes

    def _generate_intermediate_nodes(self, unique_types: set[str]) -> set[Entity]:
        intermediate_nodes = set()
        for entity_type in unique_types:
            id = IdGenerator.id()
            entity = Entity(
                id=id,
                type=self._intermediate_node_type,
                value=entity_type,
                description="System defined intermediate node",
            )
            intermediate_nodes.add(entity)
        return intermediate_nodes

    def _build_intermediate_links(
        self, entities: set[Entity], intermediate_nodes: set[Entity]
    ) -> set[Relationship]:
        intermediate_links = set()
        for entity in entities:
            intermediate_node = next(
                (x for x in intermediate_nodes if x.value == entity.type), None
            )
            if intermediate_node is not None:
                id = IdGenerator.id()
                rel = Relationship(
                    id=id,
                    source=entity,
                    target=intermediate_node,
                    relation="has_type",
                    description="System defined intermediate link",
                )
                intermediate_links.add(rel)
            else:
                logger.warning(f"Failed to lookup entity type {entity.type}")

        return intermediate_links
