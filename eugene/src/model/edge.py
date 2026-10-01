class Edge:
    """
    relation,display_relation,x_index,y_index
    """

    def __init__(
        self, x_index: int, y_index: int, display_relation: str, relation: str
    ):
        self.x_index = x_index
        self.y_index = y_index
        self.relation = relation
        self.display_relation = display_relation

    def __eq__(self, other):
        return self is other or (
            self.relation == other.relation
            and self.display_relation == other.display_relation
            and self.x_index == other.x_index
            and self.y_index == other.y_index
        )

    def __hash__(self):
        return hash((self.relation, self.display_relation, self.x_index, self.y_index))

    def __repr__(self):
        return "{}:{} {}-{}".format(
            self.relation, self.display_relation, self.x_index, self.y_index
        )

    def __str__(self):
        return repr(self)
