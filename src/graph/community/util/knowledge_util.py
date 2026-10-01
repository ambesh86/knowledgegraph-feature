from networkx import Graph

from graph.model.entity import Entity
from graph.model.relationship import Relationship


def unique_relationship_descriptions(
    entity: Entity, rels: set[Relationship]
) -> set[str]:
    """
    return unique relationship decsriptions that relate to an entity
    """
    connected_rels = connected_relationships(entity, rels)
    descriptions = set()
    for relationship in connected_rels:
        if relationship.description is not None:
            descriptions.add(relationship.description)

    return descriptions


def connected_relationships(
    entity: Entity, relationships: set[Relationship]
) -> set[Relationship]:
    """
    return relationships that relate to the given entity
    """
    found = set()
    for relationship in relationships:
        if relationship.source == entity or relationship.target == entity:
            found.add(relationship)

    return found


def connected_relationships_for_entities(
    entities: set[Entity] | Graph, relationships: set[Relationship]
) -> set[Relationship]:
    """
    return relationships that relate to any of the given entities
    """
    found = set()
    for entity in entities:
        found.update(
            connected_relationships(entity=entity, relationships=relationships)
        )

    return found
