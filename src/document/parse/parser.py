from abc import abstractmethod


class Parser:
    def __init__(self):
        self.extensions = {}

    @abstractmethod
    def parse(self, path: str) -> list[dict[str, str]]:
        raise NotImplementedError

    def _is_supported_extension(self, file_ext: str) -> bool:
        return file_ext in self.extensions
