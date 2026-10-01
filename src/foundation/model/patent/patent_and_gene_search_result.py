from dataclasses import dataclass

from foundation.model.patent.patent_search_result_row import PatentSearchResultRow


@dataclass(frozen=True, unsafe_hash=True)
class PatentAndGeneSearchResult:
    gene_protein: str
    count: int
    results: list[PatentSearchResultRow]
