class Entity:
    def __init__(self, type: str, value: str, description: str = "", id: int = -1):
        self.id = id
        self.type = type
        self.value = value
        self.description = description

    def __eq__(self, other):
        # isinstance(other, self.__class__)
        return self is other or (self.type == other.type and self.value == other.value)

    def __hash__(self):
        return hash((self.type, self.value))

    def __repr__(self):
        return "{}:{}".format(self.type, self.value)

    def __str__(self):
        return repr(self)
