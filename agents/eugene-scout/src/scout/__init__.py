"""Eugene Scout — real-time pipeline intelligence and partnership opportunity scanning.

Implements Use Case 1 of the CSL BD AWS Bioinformatics Agentic Workflow: a scheduled
scan across ClinicalTrials.gov, Europe PMC literature and patents, and SEC EDGAR that
scores emerging biotech signals against CSL's strategic filter and ranks them for the
BD team.

The service is deliberately boring where it matters. Collection is I/O with retries,
scoring is a pure function, and the LLM is confined to writing one paragraph of prose
about a decision that has already been made numerically. A ranked list an analyst
cannot reproduce is a ranked list they will not trust.
"""

__version__ = "1.0.0"
