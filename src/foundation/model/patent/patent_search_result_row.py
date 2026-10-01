from dataclasses import dataclass


@dataclass(frozen=True, unsafe_hash=True)
class PatentSearchResultRow:
    patent_id: str
