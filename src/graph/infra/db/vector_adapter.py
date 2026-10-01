from abc import abstractmethod

from graph.model.summary import Summary


class VectorAdapter:
    def __init__(self):
        self.extensions = {}

    @abstractmethod
    def ingest(self, summaries: list[Summary], embedding_dim: int) -> dict:
        raise NotImplementedError()
