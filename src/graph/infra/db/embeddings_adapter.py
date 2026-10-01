from abc import abstractmethod
from warnings import deprecated


# remove if unused
@deprecated
class EmbeddingsAdapter:
    def __init__(self):
        self.extensions = {}

    @abstractmethod
    def ingest(self, node_label: str) -> int:
        raise NotImplementedError()
