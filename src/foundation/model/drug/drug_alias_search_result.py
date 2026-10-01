from dataclasses import dataclass

from foundation.model.drug.drug_result_element import DrugResultElement


@dataclass(frozen=True, unsafe_hash=True)
class DrugAliasSearchResult:
    drug: str
    count: int
    results: list[DrugResultElement]
