from graph.model.entity import Entity
from graph.model.relationship import Relationship


class Extraction:
    def __init__(
        self,
        entities: set[Entity] = set(),
        relationships: set[Relationship] = set(),
    ):
        self.entities = entities
        self.relationships = relationships

    def __eq__(self, other):
        return self is other or (
            isinstance(other, self.__class__)
            and self.entities == other.entities
            and self.relationships == other.relationships
        )

    def __hash__(self):
        return hash((self.entities, self.relationships))

    def __repr__(self):
        return "<Extraction {}:{}>".format(self.entities, self.relationships)
