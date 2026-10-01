from dataclasses import dataclass


@dataclass(frozen=True, unsafe_hash=True)
class Node:
    id: str
    value: str
    labels: set[str]
