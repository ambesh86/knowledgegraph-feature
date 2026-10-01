from dataclasses import dataclass


@dataclass(frozen=True, unsafe_hash=True)
class IdAndValue:
    id: str
    value: str
