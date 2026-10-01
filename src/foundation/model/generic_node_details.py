from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True, unsafe_hash=True)
class GenericNodeDetails:
    labels: Tuple[str, ...]
    id: str
    value: str
    source: str
    description: str
