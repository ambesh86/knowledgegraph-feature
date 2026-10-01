from dataclasses import dataclass

from foundation.model.patent.patent_search_result_row import PatentSearchResultRow


@dataclass(frozen=True, unsafe_hash=True)
class PatentSearchResult:
    search_id: str
    count: int
    results: list[PatentSearchResultRow]
