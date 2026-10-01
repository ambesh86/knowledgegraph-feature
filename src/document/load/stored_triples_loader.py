import csv
import logging
from pathlib import Path
from typing import Optional

from graph.mapper.entity_mapper import EntityMapper
from graph.mapper.relationship_mapper import RelationshipMapper
from graph.model.entity import Entity
from graph.model.extraction import Extraction
from graph.model.relationship import Relationship
from infra.util.file_util import list_data_files

logger = logging.getLogger(__name__)


class StoredTriplesLoader:
    def __init__(
        self,
        entities_mapper: EntityMapper = EntityMapper(),
        relationship_mapper: RelationshipMapper = RelationshipMapper(),
    ):
        self.entities_mapper = entities_mapper
        self.relationship_mapper = relationship_mapper

    def load(self, data_dirs: list[Path]) -> Extraction:
        if data_dirs is None or len(data_dirs) < 1:
            return None

        extraction = Extraction()
        for dir in data_dirs:
            logger.info(f"searching {dir}")
            entities_file = self._find_entity_file(dir)
            if entities_file is None:
                logger.warning(
                    f"No entities file found in {dir}. Moving on to next dir..."
                )
                continue
            entities = self._read_entities(entities_file)
            entities = self.entities_mapper.map_entities(entities=entities)
            relationship_file = self._find_relationship_file(dir)
            if relationship_file is None:
                logger.warning(
                    f"No relationships file found in {dir}. Moving on to next dir..."
                )
                continue
            relationships = self._read_relationships(
                relationship_file, entities=entities
            )
            relationships = self.relationship_mapper.map_relationships(
                relationships=relationships
            )
            logger.info(f"entities: {len(entities)} rels: {len(relationships)}")
            extraction.entities.update(entities)
            extraction.relationships.update(relationships)

        logger.info(
            f"total entities: {len(extraction.entities)} total relationships: {len(extraction.relationships)}"
        )
        return extraction

    def _read_entities(self, entities_file: str) -> set[Entity]:
        entities = set()
        with open(entities_file, mode="r") as csv_in:
            reader = csv.DictReader(csv_in)
            for row in reader:
                entity = Entity(
                    type=row["type"],
                    id=row["id"],
                    value=row["entity"],
                    description=row["description"],
                )
                entities.add(entity)

        return entities

    def _read_relationships(
        self, rels_file: str, entities: set[Entity]
    ) -> set[Relationship]:
        rels = set()
        with open(rels_file, mode="r") as csv_in:
            reader = csv.DictReader(csv_in)
            line = 0
            for row in reader:
                line += 1
                source = self._lookup_entity(row["source"], entities=entities)
                target = self._lookup_entity(row["target"], entities=entities)
                if source is None:
                    logger.warning(
                        f"line: {line} failed to lookup source entity {row["source"]}, dropping record..."
                    )
                    continue
                if target is None:
                    logger.warning(
                        f"line: {line} failed to lookup target entity {row["target"]}, dropping record..."
                    )
                    continue
                relationship = Relationship(
                    source=source,
                    target=target,
                    id=row["id"],
                    relation=row["relation"],
                    description=row["description"],
                )
                rels.add(relationship)

        return rels

    def _lookup_entity(self, value: str, entities: set[Entity]) -> Optional[Entity]:
        return next((e for e in entities if e.value == value), None)

    def _find_relationship_file(self, data_dir: Path) -> Optional[str]:
        logger.debug(f"reading {data_dir}")
        files = list_data_files(data_dir, {".csv"})
        fixed_rel_file = None
        rel_file = None
        for file in files:
            if file.endswith("relationships.fixed.csv"):
                fixed_rel_file = file
            if file.endswith("relationships.csv"):
                rel_file = file

        return fixed_rel_file if fixed_rel_file is not None else rel_file

    def _find_entity_file(self, data_dir: Path) -> Optional[str]:
        logger.debug(f"reading {data_dir}")
        files = list_data_files(data_dir, {".csv"})
        for file in files:
            if file.endswith("entities.csv"):
                return file

        return None
