from dataclasses import dataclass

from foundation.model.pubmed.pubmed_search_result_row import PubmedSearchResultRow


@dataclass(frozen=True, unsafe_hash=True)
class PubmedSearchResult:
    search_id: str
    count: int
    results: list[PubmedSearchResultRow]
