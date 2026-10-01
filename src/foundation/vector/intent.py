"""Question-intent classification and per-intent ranking weights — mechanism M6.

Not every question wants the same kind of evidence. Asked for a dollar limit or a
dose, exact wording matters and structural importance barely does. Asked whether
an exclusion or contraindication applies, the answer usually turns on a bridging
definition several hops away — so centrality matters much more than surface text
overlap.

RRF was designed on the premise that retrieval sources are interchangeable. This
inverts that premise deliberately: the pre-ranking weights are conditioned on what
kind of question was asked, and the fusion weights themselves are unequal.

Keyword rules rather than a learned classifier, on purpose. A learned router is a
black box — it cannot tell an auditor why a given route was chosen, and it drifts
when the model behind it is upgraded (Jeong et al., NAACL 2024). These rules are
legible, and in a regulated workflow legibility beats a couple of points of
routing accuracy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Per-intent weights for graph-result pre-ranking. Each row sums to 1.0.
WEIGHTS: dict[str, dict[str, float]] = {
    "default":     {"quality": 0.40, "centrality": 0.22, "ontology": 0.20, "text": 0.18},
    "interpret":   {"quality": 0.36, "centrality": 0.24, "ontology": 0.22, "text": 0.18},
    "compare":     {"quality": 0.38, "centrality": 0.18, "ontology": 0.22, "text": 0.22},
    "quantify":    {"quality": 0.44, "centrality": 0.10, "ontology": 0.18, "text": 0.28},
    "diagnose":    {"quality": 0.32, "centrality": 0.26, "ontology": 0.24, "text": 0.18},
    "communicate": {"quality": 0.42, "centrality": 0.14, "ontology": 0.20, "text": 0.24},
}

# Asymmetric fusion weights. The graph gets a deliberate 12% boost: enough that a
# structurally important passage is not buried under generically similar prose,
# small enough that it cannot override strong textual evidence.
SOURCE_WEIGHT_VECTOR = 1.00
SOURCE_WEIGHT_GRAPH = 1.12

# Ordered by specificity — the first match wins, so narrow intents are tested
# before broad ones.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("quantify", re.compile(
        r"\b(how many|how much|what (?:is|was) the (?:dose|dosage|limit|rate|count|number|"
        r"n|sample size)|percentage|proportion|hazard ratio|odds ratio|confidence interval|"
        r"p[- ]value|mg|ml|mmol)\b", re.I)),
    ("compare", re.compile(
        r"\b(compare|comparison|versus|vs\.?|differ|difference between|better than|"
        r"superior|head[- ]to[- ]head|relative to)\b", re.I)),
    ("diagnose", re.compile(
        r"\b(does .* apply|is .* (?:excluded|contraindicated|indicated|eligible)|"
        r"contraindication|exclusion|eligib|should (?:i|we|the patient)|safe to|risk of)\b", re.I)),
    ("communicate", re.compile(
        r"\b(summari[sz]e|summary|brief|overview|explain to|for (?:a )?(?:client|patient|"
        r"lay|non[- ]technical)|in plain (?:english|language)|tl;?dr)\b", re.I)),
    ("interpret", re.compile(
        r"\b(what does .* mean|meaning of|interpret|why does|how does .* work|"
        r"mechanism|rationale|explain)\b", re.I)),
]


@dataclass
class Intent:
    name: str
    weights: dict[str, float]
    reason: str


def classify(query: str) -> Intent:
    """Classify a question into one of the six ranking intents."""
    q = (query or "").strip()
    if q:
        for name, pattern in _PATTERNS:
            m = pattern.search(q)
            if m:
                return Intent(name, WEIGHTS[name], f"matched {name!r} on {m.group(0)!r}")
    return Intent("default", WEIGHTS["default"], "no specific intent pattern matched")


def _overlap(query: str, text: str) -> float:
    """Fraction of the query's content words present in the text."""
    qt = {w for w in re.findall(r"[a-z0-9]{3,}", (query or "").lower())}
    if not qt:
        return 0.0
    tt = {w for w in re.findall(r"[a-z0-9]{3,}", (text or "").lower())}
    return len(qt & tt) / len(qt)


def priority_score(hit: dict, query: str, intent: Intent) -> float:
    """Blend the four pre-ranking signals for one graph hit, under `intent`.

    * quality    — the retriever's own lexical relevance, squashed to 0–1.
    * centrality — composite structural importance, written by the ingestion
                   pipeline (M5). Absent until centrality has been computed, in
                   which case this term contributes nothing rather than guessing.
    * ontology   — does the hit's label match what this intent expects?
    * text       — literal query-term overlap.
    """
    lexical = float(hit.get("lexical_score") or 0.0)
    # Lucene scores are unbounded; this maps them to 0–1 monotonically without
    # needing a corpus-wide maximum.
    quality = lexical / (lexical + 3.0) if lexical > 0 else 0.0

    centrality = float(hit.get("centrality_composite") or 0.0)

    label = str(hit.get("label") or "")
    # A passage is the citable unit, so it scores highest on ontology match;
    # entities are useful context but cannot themselves be quoted as evidence.
    ontology = 1.0 if label == "paper_chunk" else 0.6 if label == "clinical_trial" else 0.35

    text = _overlap(query, str(hit.get("text") or hit.get("name") or ""))

    w = intent.weights
    return round(
        w["quality"] * quality
        + w["centrality"] * centrality
        + w["ontology"] * ontology
        + w["text"] * text,
        6,
    )
