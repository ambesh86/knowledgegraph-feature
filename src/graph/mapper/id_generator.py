from ksuid import KsuidMs


class IdGenerator:
    def __init__(self):
        raise RuntimeError("Call instance() instead")

    @classmethod
    def id(cls) -> str:
        ksuid = KsuidMs()
        return str(ksuid)
