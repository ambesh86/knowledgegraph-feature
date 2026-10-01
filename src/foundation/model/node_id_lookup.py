from typing import Tuple
from dataclasses import dataclass

from foundation.model.id_and_value import IdAndValue


@dataclass(frozen=True, unsafe_hash=True)
class NodeIdLookup:
    results: Tuple[IdAndValue, ...]
    count: int
    query: str
    fuzzy_match: bool
