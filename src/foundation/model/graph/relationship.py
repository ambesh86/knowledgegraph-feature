from dataclasses import dataclass


@dataclass(frozen=True, unsafe_hash=True)
class Relationship:
    id: str
    rel: str
