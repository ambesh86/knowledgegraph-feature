"""The accuracy matrix — one page a stakeholder can act on.

Design constraints, all learned from evaluation reports that failed to persuade:

**Every rate carries an interval.** "78.3%" from 46 questions invites a decision
the sample cannot support. "78.3% (36/46, CI 64–88%)" invites the right one, and
signals that the next thing to buy is more test cases, not more prompt tuning.

**Dimensions stay separate.** A single blended "accuracy" score is unactionable:
retrieval failures are fixed by ranking, groundedness failures by prompting,
citation failures by plumbing. Collapsing them hides which lever to pull, and the
resulting number is not comparable across releases anyway.

**Failures are listed, not just counted.** A researcher's first question about a
92% is "show me the 8%". A report that cannot is treated as marketing.

**Verdicts are stated in the report, not left to the reader.** Each row carries
an explicit threshold and a pass/fail, so "is this good enough to ship" has an
answer that was decided before the numbers were seen rather than after.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

import metrics as M


@dataclass
class Dimension:
    """One measured property of the system."""

    key: str
    label: str
    question: str          # what a reader is actually asking
    successes: int
    total: int
    threshold: float       # ship gate, set before the run
    owner: str             # which lever fixes this row
    failures: list = field(default_factory=list)

    @property
    def prop(self) -> M.Proportion:
        return M.wilson(self.successes, self.total)

    @property
    def passed(self) -> bool:
        """Judged on the LOWER bound, not the point estimate.

        A system measured at 82% with a CI of 64–92% has not demonstrated 80%
        performance; it has demonstrated that it might be anywhere in a wide band.
        Gating on the point estimate lets noise ship, and on a 46-question set the
        noise is larger than most of the improvements being argued about.
        """
        return self.prop.low >= self.threshold

    @property
    def status(self) -> str:
        """PASS / UNDERPOWERED / FAIL.

        The middle case earns its own name because conflating it with FAIL is
        actively misleading. A row reading "100% (12/12) FAIL" looks like a broken
        report and gets the whole matrix dismissed; what it means is "scored
        perfectly, but twelve questions cannot demonstrate an 80% floor". The two
        have completely different remedies — one needs engineering, the other
        needs more test cases — so they must not share a label.
        """
        if self.prop.low >= self.threshold:
            return "PASS"
        if self.prop.point >= self.threshold:
            return "UNDERPOWERED"
        return "FAIL"

    @property
    def n_needed(self) -> int:
        """Roughly how many cases would be needed to demonstrate this gate.

        Answers the "so how many do we need?" question per row, using the
        observed rate rather than the worst case, so the number is achievable
        rather than discouraging.
        """
        p = max(self.prop.point, self.threshold + 1e-6)
        margin = max(p - self.threshold, 0.01)
        return M.sample_size_for_margin(margin, p=p)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "question": self.question,
            "owner": self.owner,
            "threshold": self.threshold,
            "passed": self.passed,
            "status": self.status,
            "n_needed_to_demonstrate": self.n_needed,
            **self.prop.as_dict(),
            "example_failures": self.failures[:5],
        }


DEFAULT_THRESHOLDS = {
    # Evidence must be reachable before anything else can be right.
    "retrieval": 0.80,
    # The deterministic one. A fabricated statistic is the failure that ends
    # trust, so this gate is the strictest in the matrix.
    "numeric_groundedness": 0.98,
    # Plumbing: a citation pointing at a passage that does not exist is a bug,
    # not a quality issue, and should essentially never happen.
    "citation_validity": 1.00,
    "answer_accuracy": 0.70,
    "claim_support": 0.75,
    # Answering from nothing is worse than declining, so declining when evidence
    # is absent is scored as a success, not a miss.
    "abstention": 0.90,
}


def build(rows: list[dict], thresholds: dict | None = None) -> dict:
    """Assemble the matrix from per-question results.

    Each row is one evaluated question:
        {retrieved: bool, correct: bool, faithfulness: FaithfulnessReport|dict,
         answerable: bool, question: str}
    """
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    n = len(rows)
    dims: list[Dimension] = []

    def failures_of(pred: Callable[[dict], object], describe: Callable[[dict], str]) -> list:
        return [describe(r) for r in rows if not pred(r)]

    # --- retrieval ---------------------------------------------------------
    dims.append(Dimension(
        key="retrieval",
        label="Evidence retrieved",
        question="Did the passage needed to answer reach the model at all?",
        successes=sum(1 for r in rows if r.get("retrieved")),
        total=n,
        threshold=th["retrieval"],
        owner="ranking / recall",
        failures=failures_of(lambda r: r.get("retrieved"),
                             lambda r: r.get("question", "")[:110]),
    ))

    # --- answer correctness ------------------------------------------------
    if any("correct" in r for r in rows):
        dims.append(Dimension(
            key="answer_accuracy",
            label="Answer correct",
            question="Was the final answer right?",
            successes=sum(1 for r in rows if r.get("correct")),
            total=n,
            threshold=th["answer_accuracy"],
            owner="prompt / model",
            failures=failures_of(lambda r: r.get("correct"),
                                 lambda r: r.get("question", "")[:110]),
        ))

        # Conditional accuracy separates a ranking problem from a reasoning one.
        answerable = [r for r in rows if r.get("retrieved")]
        if answerable:
            dims.append(Dimension(
                key="answer_given_retrieval",
                label="Answer correct (evidence present)",
                question="When the evidence did arrive, did the model use it correctly?",
                successes=sum(1 for r in answerable if r.get("correct")),
                total=len(answerable),
                threshold=th["answer_accuracy"],
                owner="prompt / model",
            ))

    # --- faithfulness ------------------------------------------------------
    faith = [r["faithfulness"] for r in rows if r.get("faithfulness")]
    if faith:
        f = [x if isinstance(x, dict) else x.as_dict() for x in faith]

        num_total = sum(x["numeric_total"] for x in f)
        num_ok = sum(x["numeric_supported"] for x in f)
        ungrounded = [
            u for x in f for u in x.get("ungrounded_numbers", [])
        ]
        dims.append(Dimension(
            key="numeric_groundedness",
            label="Statistics traceable to a source",
            question="Is every number in the answer present in a cited passage?",
            successes=num_ok,
            total=num_total,
            threshold=th["numeric_groundedness"],
            owner="prompt / retrieval",
            failures=[f"{u['value']} — …{u['context'].strip()}…" for u in ungrounded],
        ))

        cite_total = sum(x.get("citations_total", 0) for x in f)
        cite_ok = sum(x.get("citations_valid", 0) for x in f)
        if cite_total:
            dims.append(Dimension(
                key="citation_validity",
                label="Citations resolve",
                question="Does every [Evidence N] point at a passage that exists?",
                successes=cite_ok,
                total=cite_total,
                threshold=th["citation_validity"],
                owner="plumbing (UI / prompt contract)",
                failures=[c for x in f for c in x.get("invalid_citations", [])],
            ))

        sent_total = sum(x["sentences_total"] for x in f)
        sent_ok = sum(x["sentences_supported"] for x in f)
        if sent_total:
            dims.append(Dimension(
                key="claim_support",
                label="Claims supported by a cited passage",
                question="Does each sentence correspond to something retrieved?",
                successes=sent_ok,
                total=sent_total,
                threshold=th["claim_support"],
                owner="ranking / prompt",
                failures=[s for x in f for s in x.get("unsupported_sentences", [])],
            ))

    # --- abstention --------------------------------------------------------
    unanswerable = [r for r in rows if r.get("retrieved") is False]
    if unanswerable:
        def abstained(r: dict) -> bool:
            fr = r.get("faithfulness")
            if fr is None:
                return False
            return (fr if isinstance(fr, dict) else fr.as_dict()).get("abstained", False)

        dims.append(Dimension(
            key="abstention",
            label="Declined when evidence was missing",
            question="With nothing retrieved, did it say so instead of inventing an answer?",
            successes=sum(1 for r in unanswerable if abstained(r)),
            total=len(unanswerable),
            threshold=th["abstention"],
            owner="prompt",
            failures=[r.get("question", "")[:110] for r in unanswerable if not abstained(r)],
        ))

    passed = [d for d in dims if d.status == "PASS"]
    failing = [d for d in dims if d.status == "FAIL"]
    underpowered = [d for d in dims if d.status == "UNDERPOWERED"]
    return {
        "n_questions": n,
        "dimensions": [d.as_dict() for d in dims],
        "gates_passed": len(passed),
        "gates_failing": len(failing),
        "gates_underpowered": len(underpowered),
        "gates_total": len(dims),
        # Only a real failure blocks. An underpowered row is a measurement
        # problem, and calling it a defect sends people to fix working code.
        "ship": len(failing) == 0,
        "ship_qualified": len(underpowered) > 0,
        # Answers "is the test set big enough" with a number rather than a shrug.
        "n_for_plus_minus_5pp": M.sample_size_for_margin(0.05),
        "n_for_plus_minus_10pp": M.sample_size_for_margin(0.10),
    }


def to_markdown(matrix: dict, title: str = "Accuracy matrix") -> str:
    """Render for humans. Markdown so it pastes into a ticket, a PR or a deck."""
    out = [f"# {title}", ""]
    if not matrix["ship"]:
        verdict = f"**do not ship** — {matrix['gates_failing']} dimension(s) below gate"
    elif matrix.get("ship_qualified"):
        verdict = (
            f"**no failures**, but {matrix['gates_underpowered']} dimension(s) are "
            f"UNDERPOWERED — scored at or above their gate on too few cases to prove it"
        )
    else:
        verdict = "**ship** — every gate demonstrated"
    out.append(
        f"{matrix['gates_passed']}/{matrix['gates_total']} gates demonstrated on "
        f"{matrix['n_questions']} questions — {verdict}"
    )
    out += ["", "| Dimension | Result | 95% CI | Gate | Status | Fix belongs to |",
            "|---|---|---|---|---|---|"]
    for d in matrix["dimensions"]:
        out.append(
            f"| {d['label']} | {d['point']:.1%} ({d['successes']}/{d['total']}) "
            f"| {d['ci_low']:.1%}–{d['ci_high']:.1%} | ≥{d['threshold']:.0%} "
            f"| {d['status']} | {d['owner']} |"
        )

    out += ["", "## What each row answers", ""]
    for d in matrix["dimensions"]:
        out.append(f"- **{d['label']}** — {d['question']}")

    out += ["", "## How to read the status column", "",
            "- **PASS** — the interval's lower bound clears the gate. Demonstrated.",
            "- **UNDERPOWERED** — scored at or above the gate, but on too few cases to "
            "prove it. Not a defect: it needs more test cases, not more engineering.",
            "- **FAIL** — the measured rate itself is below the gate.", "",
            "Gating on the lower bound rather than the point estimate is what stops "
            "sampling noise from shipping; on a set this size that noise is larger than "
            "most improvements under discussion.", ""]
    under = [d for d in matrix["dimensions"] if d["status"] == "UNDERPOWERED"]
    if under:
        out += ["### To demonstrate the underpowered gates", ""]
        for d in under:
            out.append(
                f"- **{d['label']}**: ~{d['n_needed_to_demonstrate']} cases "
                f"(have {d['total']}) to separate {d['point']:.0%} from the "
                f"{d['threshold']:.0%} gate"
            )
        out.append("")

    fails = [d for d in matrix["dimensions"] if d["example_failures"]]
    if fails:
        out += ["## Failures, so the numbers can be audited", ""]
        for d in fails:
            out.append(f"**{d['label']}** — {d['total'] - d['successes']} failing:")
            for ex in d["example_failures"]:
                out.append(f"  - {ex}")
            out.append("")

    out += ["## Statistical power", "",
            f"To measure any rate to ±5 points needs ~{matrix['n_for_plus_minus_5pp']} questions; "
            f"±10 points needs ~{matrix['n_for_plus_minus_10pp']}. "
            f"This run used {matrix['n_questions']}. "
            "Widening the gold set moves every interval more than any prompt change will.", ""]
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "eval/results.json"
    with open(src) as fh:
        data = json.load(fh)
    rows = data["rows"] if isinstance(data, dict) else data
    print(to_markdown(build(rows)))
