import logging

from graph.mapper.label_mapper import LabelMapper
from graph.model.entity import Entity

logger = logging.getLogger(__name__)


class EntityMapper(LabelMapper):
    def __init__(self):
        super().__init__()

    def map(self, values: set) -> set:
        return self.map_entities(values)

    def map_entities(self, entities: set[Entity]) -> set[Entity]:
        mapped = set()
        for entity in entities:
            mapped.add(self.map_entity(entity))
        return mapped

    def map_entity(self, entity: Entity) -> Entity:
        entity.type = self.map_label(entity.type)
        return entity

    def map_label(self, val: str) -> str:
        val = self._strip(val)
        val = self._title_case(val)
        return val

    def _title_case(self, val: str) -> str:
        return self._replace_whitespace(val.title(), delim="")
