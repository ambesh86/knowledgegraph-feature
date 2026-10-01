from dataclasses import dataclass


@dataclass(frozen=True, unsafe_hash=True)
class PubmedSearchResultRow:
    pmid: str
