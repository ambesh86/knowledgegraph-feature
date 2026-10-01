class ParsedFile:
    def __init__(self, path: str, pages: list[dict[str, str]]):
        self.path = path
        self.pages = pages
