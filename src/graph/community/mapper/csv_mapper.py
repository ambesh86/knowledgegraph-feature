import logging

from networkx import Graph

from graph.model.entity import Entity
from graph.model.relationship import Relationship

logger = logging.getLogger(__name__)


class CsvMapper:
    def __init__(self):
        self.entities_header = ["id,entity,type,description"]
        self.rels_header = ["id,source,target,relation,description"]

    def entities_as_csv(
        self, community: set[Entity] | Graph, with_header: bool = False
    ) -> list[str]:
        rows = []
        for entity in community:
            row = self._entity_as_row(entity)
            rows.append(row)

        logger.debug(f"built {len(rows)} row(s)")
        return self.entities_header + rows if with_header else rows

    def relationships_as_csv(
        self, rels: set[Relationship], with_header: bool = False
    ) -> list[str]:
        rows = []
        for relationships in rels:
            row = self._relationship_as_row(relationships)
            rows.append(row)

        logger.debug(f"built {len(rows)} row(s)")
        ordered_rows = self._order_relationships(rows)
        return self.rels_header + ordered_rows if with_header else ordered_rows

    def _order_relationships(self, rows: list[str]) -> list[str]:
        return sorted(rows, key=lambda el: el.split(",")[1])

    def _entity_as_row(self, entity: Entity) -> str:
        return f"{entity.id},{entity.value},{entity.type},{entity.description}"

    def _relationship_as_row(self, relationship: Relationship) -> str:
        return f"{relationship.id},{relationship.source.value},{relationship.target.value},{relationship.relation},{relationship.description}"
