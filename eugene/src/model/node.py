class Node:
    def __init__(self, index: int, id: int, label: str, name: str, source: str):
        self.index = index
        self.id = id
        self.label = label
        self.name = name
        self.source = source

    def __eq__(self, other):
        return self is other or (self.label == other.label 
                                 and self.name == other.name
                                 and self.source == other.source)

    def __hash__(self):
        return hash((self.label, self.label))

    def __repr__(self):
        return "{}:{}".format(self.label, self.name)

    def __str__(self):
        return repr(self)
