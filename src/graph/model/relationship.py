from graph.model.entity import Entity


class Relationship:
    def __init__(
        self,
        source: Entity,
        target: Entity,
        relation: str,
        description: str = "",
        id: str | int = -1,
    ):
        self.id = id
        self.source = source
        self.target = target
        self.relation = relation
        self.description = description

    def __eq__(self, other):
        return self is other or (
            isinstance(other, self.__class__)
            and self.relation == other.relation
            and self.source == other.source
            and self.target == other.target
        )

    def __hash__(self):
        return hash((self.relation, self.source, self.target))

    def __repr__(self):
        return "{}-{}-{}".format(self.source, self.relation, self.target)

    def __str__(self):
        return repr(self)
