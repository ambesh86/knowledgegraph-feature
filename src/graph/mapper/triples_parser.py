import json
import logging
from typing import Any, Optional

from graph.model.entity import Entity
from graph.model.extraction import Extraction
from graph.model.relationship import Relationship

logger = logging.getLogger(__name__)


class TriplesParser:
    """
    Class will parse the response of the LLM extraction step

    See, https://arxiv.org/html/2404.16130v1
    2.2Text Chunks → Element Instances
    """

    def parse(
        self,
        json_payload: str,
    ) -> Extraction:
        json_payload = json_payload.replace("```json", "")
        json_payload = json_payload.replace("```", "")
        try:
            payload = json.loads(json_payload)
        except json.JSONDecodeError as e:
            logger.warning(f"ignoring json parse error: {e}")
            return Extraction()
        payload_entities = payload["entities"]
        payload_relationships = payload["relationships"]
        entities = self._fix_missing_entities(
            payload_relationships, self._parse_entities(payload_entities)
        )
        relationships = self._parse_relationships(payload_relationships, entities)
        logger.debug(
            f"Extracted entities: {len(entities)} relationships: {len(relationships)}"
        )
        return Extraction(entities=entities, relationships=relationships)

    def _parse_entities(self, entities: dict[str, Any]) -> set[Entity]:
        parsed_entities = set()
        for entity in entities:
            parsed_entities.add(
                Entity(
                    value=self._normalize(
                        entity.get("entity_name") or entity.get("entity")
                    ),
                    type=self._normalize(entity.get("entity_type")),
                    description=entity.get("entity_description"),
                )
            )
        return parsed_entities

    def _parse_relationships(
        self,
        relationships: set[dict[str, Any]],
        entities: set[Entity],
    ) -> set[Relationship]:
        parsed_relationships = set()
        for relationship in relationships:
            parsed_relationships.add(
                Relationship(
                    source=self._lookup_entity(
                        value=self._normalize(relationship.get("source_entity")),
                        entities=entities,
                    ),
                    target=self._lookup_entity(
                        value=self._normalize(relationship.get("target_entity")),
                        entities=entities,
                    ),
                    relation=self._normalize(relationship.get("relation")),
                    description=relationship.get("relation_description")
                    or relationship.get("relationship_description"),
                )
            )
        return parsed_relationships

    def _fix_missing_entities(
        self,
        relationships: set[dict[str, Any]],
        entities: set[Entity],
    ) -> set[Entity]:
        """
        add entities found in a relationship, but not in the entites set
        """
        fixed = set(entities)
        for relationship in relationships:
            fixed.add(
                self._find_or_make_entity(relationship["source_entity"], entities)
            )
            fixed.add(
                self._find_or_make_entity(relationship["target_entity"], entities)
            )
        return fixed

    def _find_or_make_entity(self, value: str, entities: set[Entity]) -> Entity:
        entity = self._lookup_entity(value=value, entities=entities)
        if entity is None:
            return self._missing_entity(value)
        else:
            return entity

    def _lookup_entity(self, value: str, entities: set[Entity]) -> Optional[Entity]:
        """
        warn: this method looks up the first entity by value, but does not consider the entity type
        the Entity object uses both type and value for it's uniqueness

        todo: print warnings around ambiguous entity lookups to watch for potential bugs
        """
        for entity in entities:
            if entity.value == value:
                return entity

    def _missing_entity(self, value: str) -> Entity:
        return Entity(
            value=value, type="unknown", description="generated missing entity"
        )

    def _normalize(self, value: str) -> str:
        # todo consider lowercasing and removing spaces
        return value if value is not None else value
