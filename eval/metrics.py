"""Statistics for reporting accuracy honestly.

The harness currently reports bare proportions — "answer accuracy 78.3%" over 46
questions. That number is not wrong, but presented alone it is misleading in a
specific and consequential way: 36/46 is 78.3%, and its 95% confidence interval
runs from roughly 64% to 88%. A stakeholder who reads 78.3% as precise will draw
conclusions the sample cannot support, and a researcher who notices the missing
interval will discount everything else in the report.

So every proportion this package emits carries an interval, and every comparison
between two configurations carries a test. The point is not statistical ceremony;
it is that a 3-point difference on 46 questions is noise, and shipping a reranker
because of it wastes a week.

Nothing here depends on scipy or numpy — the harness runs in a bare container.
The implementations are standard closed forms with the exception of the bootstrap,
which is a plain resample.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Proportions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Proportion:
    """A measured rate with an interval, and the counts it came from.

    The counts travel with the estimate deliberately: "82%" invites a decision,
    "82% (37/45, 95% CI 68–91%)" invites the right decision.
    """

    successes: int
    total: int
    point: float
    low: float
    high: float
    confidence: float = 0.95

    @property
    def margin(self) -> float:
        """Half-width, for the common case of quoting ±x points."""
        return (self.high - self.low) / 2

    def format(self, places: int = 1) -> str:
        return (
            f"{self.point:.{places}%} ({self.successes}/{self.total}, "
            f"{self.confidence:.0%} CI {self.low:.{places}%}–{self.high:.{places}%})"
        )

    def as_dict(self) -> dict:
        return {
            "successes": self.successes,
            "total": self.total,
            "point": round(self.point, 4),
            "ci_low": round(self.low, 4),
            "ci_high": round(self.high, 4),
            "ci_margin": round(self.margin, 4),
            "confidence": self.confidence,
        }


# Two-sided z for the common confidence levels. A lookup rather than an inverse
# normal implementation: three values cover every report anyone asks for, and a
# hand-rolled inverse CDF is a subtle thing to get wrong for no benefit.
_Z = {0.90: 1.6448536269514722, 0.95: 1.959963984540054, 0.99: 2.5758293035489004}


def wilson(successes: int, total: int, confidence: float = 0.95) -> Proportion:
    """Wilson score interval for a binomial proportion.

    Wilson rather than the textbook normal approximation (p̂ ± z·√(p̂(1-p̂)/n)),
    because the normal approximation breaks exactly where evaluation lives: small
    n, and rates near 0 or 1. At 46/46 it produces the interval [1.0, 1.0] —
    claiming certainty of perfection from 46 examples — and at 0/46 it produces
    [0, 0]. Wilson gives [92.3%, 100%] and [0%, 7.7%], which are the defensible
    statements.
    """
    if total <= 0:
        return Proportion(0, 0, 0.0, 0.0, 1.0, confidence)
    if successes < 0 or successes > total:
        raise ValueError(f"successes={successes} out of range for total={total}")

    z = _Z.get(confidence)
    if z is None:
        raise ValueError(f"unsupported confidence {confidence}; use one of {sorted(_Z)}")

    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return Proportion(successes, total, p, max(0.0, centre - half), min(1.0, centre + half), confidence)


def sample_size_for_margin(margin: float, p: float = 0.5, confidence: float = 0.95) -> int:
    """How many test cases are needed to measure a rate to ±margin.

    Answers the question every eval eventually raises — "is 46 questions enough?"
    — with a number instead of an opinion. p=0.5 is the worst case and therefore
    the safe default for planning.
    """
    z = _Z[confidence]
    return math.ceil(z * z * p * (1 - p) / (margin * margin))


# ---------------------------------------------------------------------------
# Comparing two configurations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PairedComparison:
    """Result of comparing two systems on the SAME questions."""

    both_correct: int
    only_a: int
    only_b: int
    both_wrong: int
    p_value: float
    significant: bool
    note: str

    def as_dict(self) -> dict:
        return {
            "both_correct": self.both_correct,
            "a_only": self.only_a,
            "b_only": self.only_b,
            "both_wrong": self.both_wrong,
            "p_value": round(self.p_value, 4),
            "significant_at_0.05": self.significant,
            "note": self.note,
        }


def mcnemar(a_correct: list[bool], b_correct: list[bool], alpha: float = 0.05) -> PairedComparison:
    """Exact McNemar test for two systems scored on the same items.

    The right test here, and not the obvious one. Comparing two configurations by
    their headline accuracies with a two-proportion test throws away the pairing:
    both were run on the *same* questions, so the questions they both got right
    carry no information about which is better. Only the disagreements do.

    Concretely: two rerankers scoring 78% and 82% on 46 shared questions differ on
    perhaps 4 items. That is not evidence of an improvement, and this function
    says so with a p-value rather than leaving it to intuition.

    Uses the exact binomial test rather than the chi-square approximation, which
    is unreliable when the discordant count is small — which it always is at this
    sample size.
    """
    if len(a_correct) != len(b_correct):
        raise ValueError("paired comparison needs equal-length result vectors")

    both = sum(1 for a, b in zip(a_correct, b_correct) if a and b)
    only_a = sum(1 for a, b in zip(a_correct, b_correct) if a and not b)
    only_b = sum(1 for a, b in zip(a_correct, b_correct) if b and not a)
    neither = sum(1 for a, b in zip(a_correct, b_correct) if not a and not b)

    n = only_a + only_b
    if n == 0:
        return PairedComparison(both, 0, 0, neither, 1.0, False,
                                "the two configurations agreed on every question")

    # Exact two-sided binomial test against p=0.5 on the discordant pairs.
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    p = min(1.0, 2 * tail)

    if p < alpha:
        better = "A" if only_a > only_b else "B"
        note = f"{better} is better; the difference is unlikely to be chance (p={p:.3f})"
    else:
        note = (
            f"no significant difference (p={p:.3f}); they disagree on only {n} of "
            f"{len(a_correct)} questions, which this sample cannot resolve"
        )
    return PairedComparison(both, only_a, only_b, neither, p, p < alpha, note)


def bootstrap_ci(
    values: list[float],
    statistic=lambda xs: sum(xs) / len(xs),
    confidence: float = 0.95,
    iterations: int = 5000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Percentile bootstrap, for statistics with no closed-form interval.

    Wilson covers proportions. Anything else the report quotes — a mean rank, a
    mean score, a ratio of derived quantities — needs this. Seeded so a report is
    reproducible; an eval whose numbers move when nothing changed is an eval no
    one trusts.
    """
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    point = statistic(values)
    samples = []
    for _ in range(iterations):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(statistic(resample))
    samples.sort()
    lo_i = int((1 - confidence) / 2 * iterations)
    hi_i = int((1 + confidence) / 2 * iterations) - 1
    return point, samples[lo_i], samples[max(lo_i, hi_i)]


# ---------------------------------------------------------------------------
# Calibration — is a stated confidence worth anything?
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Calibration:
    """How well stated confidence matches observed accuracy."""

    ece: float
    max_gap: float
    bins: list[dict]
    n: int

    def as_dict(self) -> dict:
        return {
            "expected_calibration_error": round(self.ece, 4),
            "max_gap": round(self.max_gap, 4),
            "n": self.n,
            "bins": self.bins,
        }


def calibration(
    confidences: list[float], correct: list[bool], n_bins: int = 10
) -> Calibration:
    """Expected Calibration Error, plus the reliability table behind it.

    This is the metric that makes a confidence score usable rather than
    decorative. A system that says "high confidence" and is right 70% of the time
    is worse than one that says "70%" and is right 70% of the time, because the
    second can be acted on and the first quietly teaches users to ignore it.

    ECE is the average gap between stated confidence and observed accuracy,
    weighted by how many predictions fall in each bin. 0 is perfect; above ~0.1
    means the number should not be shown to users as-is.

    The per-bin table is returned alongside because ECE alone hides direction: a
    system overconfident at the top and underconfident at the bottom can post a
    respectable ECE while being wrong in the way that matters most.
    """
    if len(confidences) != len(correct):
        raise ValueError("calibration needs one confidence per outcome")
    n = len(confidences)
    if n == 0:
        return Calibration(0.0, 0.0, [], 0)

    bins: list[dict] = []
    ece = 0.0
    max_gap = 0.0
    for i in range(n_bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        # Upper edge inclusive on the last bin so confidence == 1.0 is counted.
        idx = [
            j for j, c in enumerate(confidences)
            if (lo <= c < hi) or (i == n_bins - 1 and c == 1.0)
        ]
        if not idx:
            continue
        conf = sum(confidences[j] for j in idx) / len(idx)
        acc = sum(1 for j in idx if correct[j]) / len(idx)
        gap = abs(conf - acc)
        ece += len(idx) / n * gap
        max_gap = max(max_gap, gap)
        bins.append({
            "range": f"{lo:.1f}–{hi:.1f}",
            "n": len(idx),
            "mean_confidence": round(conf, 4),
            "observed_accuracy": round(acc, 4),
            "gap": round(conf - acc, 4),  # signed: positive = overconfident
        })
    return Calibration(ece, max_gap, bins, n)


# ---------------------------------------------------------------------------
# Judge agreement
# ---------------------------------------------------------------------------


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    """Agreement between two raters, corrected for agreement by chance.

    Needed wherever an LLM grades an answer. Raw agreement flatters a judge on a
    skewed set: if 90% of answers are correct, a judge that says "correct" every
    time agrees 90% of the time and has learned nothing. Kappa exposes that as ~0.

    Conventional reading: <0.4 poor, 0.4–0.6 moderate, 0.6–0.8 substantial,
    >0.8 near-human. A judge below 0.6 against human labels should not be used to
    report an accuracy figure to stakeholders.
    """
    if len(a) != len(b):
        raise ValueError("kappa needs equal-length rating vectors")
    n = len(a)
    if n == 0:
        return 0.0
    observed = sum(1 for x, y in zip(a, b) if x == y) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected >= 1.0:
        return 1.0 if observed >= 1.0 else 0.0
    return (observed - expected) / (1 - expected)
