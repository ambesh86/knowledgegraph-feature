# Eugene accuracy matrix — k=20 rerank=service prompt=v2

3/5 gates demonstrated on 46 questions — **no failures**, but 2 dimension(s) are UNDERPOWERED — scored at or above their gate on too few cases to prove it

| Dimension | Result | 95% CI | Gate | Status | Fix belongs to |
|---|---|---|---|---|---|
| Evidence retrieved | 100.0% (46/46) | 92.3%–100.0% | ≥80% | PASS | ranking / recall |
| Answer correct | 100.0% (46/46) | 92.3%–100.0% | ≥70% | PASS | prompt / model |
| Answer correct (evidence present) | 100.0% (46/46) | 92.3%–100.0% | ≥70% | PASS | prompt / model |
| Statistics traceable to a source | 100.0% (50/50) | 92.9%–100.0% | ≥98% | UNDERPOWERED | prompt / retrieval |
| Claims supported by a cited passage | 100.0% (2/2) | 34.2%–100.0% | ≥75% | UNDERPOWERED | ranking / prompt |

## What each row answers

- **Evidence retrieved** — Did the passage needed to answer reach the model at all?
- **Answer correct** — Was the final answer right?
- **Answer correct (evidence present)** — When the evidence did arrive, did the model use it correctly?
- **Statistics traceable to a source** — Is every number in the answer present in a cited passage?
- **Claims supported by a cited passage** — Does each sentence correspond to something retrieved?

## How to read the status column

- **PASS** — the interval's lower bound clears the gate. Demonstrated.
- **UNDERPOWERED** — scored at or above the gate, but on too few cases to prove it. Not a defect: it needs more test cases, not more engineering.
- **FAIL** — the measured rate itself is below the gate.

Gating on the lower bound rather than the point estimate is what stops sampling noise from shipping; on a set this size that noise is larger than most improvements under discussion.

### To demonstrate the underpowered gates

- **Statistics traceable to a source**: ~0 cases (have 50) to separate 100% from the 98% gate
- **Claims supported by a cited passage**: ~0 cases (have 2) to separate 100% from the 75% gate

## Statistical power

To measure any rate to ±5 points needs ~385 questions; ±10 points needs ~97. This run used 46. Widening the gold set moves every interval more than any prompt change will.

