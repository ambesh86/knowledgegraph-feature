"""Use Case 2 — Accelerated Scientific Due Diligence.

On-demand, target-scoped counterpart to the Use Case 1 scanner: same collectors,
same never-raise contract, same S3 store, pointed at one company or asset instead
of a therapeutic area.
"""
from scout.duediligence.brief import build
from scout.duediligence.confidence import ConfidenceBand, assess
from scout.duediligence.orchestrator import run_due_diligence
from scout.duediligence.target import Target

__all__ = ["Target", "build", "assess", "ConfidenceBand", "run_due_diligence"]
