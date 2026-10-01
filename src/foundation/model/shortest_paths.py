from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True, unsafe_hash=True)
class ShortestPaths:
    start_id: str
    end_id: str
    max_hop: int
    count: int
    paths: Tuple[Tuple[str, ...], ...]
