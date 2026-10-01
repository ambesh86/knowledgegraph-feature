import json


class SetEncoder(json.JSONEncoder):
    """
    a set collection needs a customer encoder
    """

    def default(self, o):
        if isinstance(o, set):
            l = list(o)
            l.sort()
            return l
        return super().default(o)
