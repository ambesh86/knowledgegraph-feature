from dataclasses import dataclass


@dataclass(frozen=True, unsafe_hash=True)
class DrugResultElement:
    id: str
    name: str
    is_canonical: bool
