from dataclasses import dataclass

from foundation.model.pubmed.pubmed_search_result_row import PubmedSearchResultRow


@dataclass(frozen=True, unsafe_hash=True)
class PubmedAndGeneSearchResult:
    gene_protein: str
    count: int
    results: list[PubmedSearchResultRow]
