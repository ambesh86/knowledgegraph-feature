"""Score the fused-retrieval + answer pipeline against the table-cell gold set.

Two numbers, measured separately on purpose:

  * **retrieval@k** — did the evidence needed to answer reach the model at all?
    Either the gold cell itself or its parent table chunk counts: both carry the
    value, and the table chunk is usually the more useful of the two because it
    carries the row and column context the question asks about.
  * **answer accuracy** — given whatever retrieval returned, did the model emit
    the right cell contents?

Reported apart because they fail for different reasons and are fixed by
different things. A low retrieval number is a reranking problem; a high
retrieval number with a low answer number is a prompt problem. Collapsing them
into one score hides which lever to pull.

Usage:
    python eval/harness.py --k 20 --answer            # full pipeline
    python eval/harness.py --k 20                     # retrieval only, no LLM
    python eval/harness.py --k 20 --rerank cohere --answer
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import faithfulness
import matrix as matrix_mod
import prompts
import rerank

FUSION_URL = os.environ.get("EVAL_FUSION_URL", "http://localhost:18000/vector/fusion")


def _load_env(path: str = "docker.env") -> None:
    """Read the stack's own credentials so the eval talks to the same providers."""
    if not os.path.exists(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def retrieve(
    question: str, top_k: int, candidates: int | None = None, rerank_in_service: bool = False
) -> list[dict]:
    params: dict = {"q": question, "top_k": top_k}
    if candidates:
        params["candidates"] = candidates
    if rerank_in_service:
        params["rerank"] = "true"
    url = f"{FUSION_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=180) as resp:
        return json.load(resp).get("results", [])


def _hit_rank(results: list[dict], q: dict) -> int | None:
    """1-based rank of the first result that carries the answer, else None."""
    wanted = {q["gold_chunk_id"], q["table_chunk_id"]}
    for i, r in enumerate(results, start=1):
        if r.get("chunk_id") in wanted or r.get("node_index") in wanted:
            return i
    return None


# Grading normalizes only formatting the PDF itself is inconsistent about —
# whitespace, unicode minus/dash variants, wrapping quotes. It does NOT round or
# reinterpret numbers: "0.0398" and "0.04" are different answers.
_DASHES = str.maketrans({"–": "-", "—": "-", "−": "-", " ": " ", " ": " "})


def _norm(s: str) -> str:
    s = (s or "").translate(_DASHES).strip().strip("\"'`*.")
    return re.sub(r"\s+", " ", s).lower()


def grade(answer: str, q: dict) -> bool:
    got, want = _norm(answer), _norm(q["expected_text"])
    if got == want:
        return True
    # A model that answers "0.0398 (p Value)" has read the right cell. Accept a
    # response that contains the exact expected string as a whole token run, but
    # never one that merely contains its digits inside a longer number.
    return bool(re.search(rf"(?<![\d.]){re.escape(want)}(?![\d.])", got))


def run(
    gold: list[dict],
    top_k: int,
    reranker: str,
    prompt_version: str,
    do_answer: bool,
    pool_depth: int = 200,
    phrasing: str = "quoted",
    workers: int = 8,
    check_faithfulness: bool = False,
) -> dict:
    # "service" is the cross-encoder that ships in eugene_ws — it reranks inside
    # the retrieval call rather than in the harness, so the eval measures the
    # deployed path instead of a reimplementation of it.
    in_service = reranker == "service"
    rerank_fn = None if in_service else rerank.get(reranker)
    answer_fn = prompts.get(prompt_version) if do_answer else None
    field = "question" if phrasing == "quoted" else "question_natural"

    def one(q: dict) -> dict:
        question = q[field]
        # Over-fetch before reranking: a reranker can only reorder what it is
        # given, so retrieving exactly top_k would make it a no-op.
        pool_size = pool_depth if (rerank_fn is not None) else top_k
        results = retrieve(
            question,
            top_k if in_service else pool_size,
            candidates=pool_depth,
            rerank_in_service=in_service,
        )
        if rerank_fn is not None:
            results = rerank_fn(question, results, top_k)
        results = results[:top_k]
        rank = _hit_rank(results, q)
        row = {
            "id": q["id"],
            "retrieved": rank is not None,
            "rank": rank,
            "expected": q["expected_text"],
        }
        if answer_fn is not None:
            ans = answer_fn(question, results)
            row["answer"] = ans
            row["correct"] = grade(ans, q)
            if check_faithfulness:
                # Scored against what THIS question actually retrieved — the
                # model's permitted universe. A claim traceable to nothing in
                # that list is unsupported even if it happens to be true.
                passages = [str(r.get("text") or r.get("name") or "") for r in results]
                row["faithfulness"] = faithfulness.evaluate(ans, passages).as_dict()
        row["question"] = question
        return row

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(one, gold))

    n = len(rows)
    out = {
        "n": n,
        "top_k": top_k,
        "pool_depth": pool_depth,
        "phrasing": phrasing,
        "reranker": reranker,
        "prompt": prompt_version if do_answer else None,
        "retrieval_at_k": round(sum(r["retrieved"] for r in rows) / max(1, n), 4),
        "mean_rank": round(
            sum(r["rank"] for r in rows if r["rank"]) / max(1, sum(1 for r in rows if r["rank"])), 2
        ),
        "rows": rows,
    }
    if do_answer:
        out["answer_accuracy"] = round(sum(r["correct"] for r in rows) / max(1, n), 4)
        # The ceiling the prompt is working against: questions whose evidence
        # never arrived cannot be answered no matter how the prompt is worded.
        answerable = [r for r in rows if r["retrieved"]]
        out["accuracy_given_retrieval"] = round(
            sum(r["correct"] for r in answerable) / max(1, len(answerable)), 4
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="eval/gold.json")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--rerank", default="none", choices=list(rerank.REGISTRY))
    ap.add_argument(
        "--pool", type=int, default=200, help="candidate depth per retriever before reranking"
    )
    ap.add_argument("--prompt", default="v1", choices=list(prompts.REGISTRY))
    ap.add_argument("--answer", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--phrasing", default="quoted", choices=("quoted", "natural"))
    ap.add_argument("--workers", type=int, default=8,
        help="parallel questions; keep low with --rerank service, which is CPU-bound")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--matrix", action="store_true",
        help="also score evidence faithfulness and print the accuracy matrix")
    ap.add_argument("--matrix-out", default="",
        help="write the matrix as markdown to this path")
    args = ap.parse_args()

    _load_env()
    with open(args.gold) as fh:
        gold = json.load(fh)
    if args.limit:
        gold = gold[: args.limit]

    if args.matrix and not args.answer:
        # The matrix scores what the model wrote; without --answer there is
        # nothing to score, and a matrix of empty rows would read as a pass.
        ap.error("--matrix requires --answer")

    res = run(gold, args.k, args.rerank, args.prompt, args.answer, pool_depth=args.pool,
              phrasing=args.phrasing, workers=args.workers, check_faithfulness=args.matrix)
    print(
        f"n={res['n']} k={res['top_k']} pool={res['pool_depth']} "
        f"rerank={res['reranker']} prompt={res['prompt']} phrasing={res['phrasing']}\n"
        f"  retrieval@k          {res['retrieval_at_k']:.1%}  (mean rank {res['mean_rank']})"
    )
    if args.answer:
        print(f"  answer accuracy      {res['answer_accuracy']:.1%}")
        print(f"  given retrieval      {res['accuracy_given_retrieval']:.1%}")
    if args.matrix:
        mx = matrix_mod.build(res["rows"])
        res["matrix"] = mx
        report = matrix_mod.to_markdown(
            mx,
            f"Eugene accuracy matrix — k={args.k} rerank={args.rerank} prompt={args.prompt}",
        )
        print()
        print(report)
        if args.matrix_out:
            with open(args.matrix_out, "w") as fh:
                fh.write(report + "\n")
            print(f"  -> {args.matrix_out}")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump(res, fh, indent=1)
        print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
