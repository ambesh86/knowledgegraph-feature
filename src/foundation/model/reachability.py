from dataclasses import dataclass


@dataclass(frozen=True, unsafe_hash=True)
class Reachability:
    start_id: str
    end_id: str
    max_hop: int
    is_reachable: bool
