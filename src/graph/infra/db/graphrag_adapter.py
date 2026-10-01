from abc import abstractmethod

from graph.model.extraction import Extraction


class GraphragAdapter:
    @abstractmethod
    def ingest(self, extraction: Extraction) -> int:
        raise NotImplementedError
