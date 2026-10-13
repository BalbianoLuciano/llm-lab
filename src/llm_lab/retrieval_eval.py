"""Shared question set and retrieval metrics (labs 03, 04, 05, 12).

A retrieved chunk is a hit when it comes from the expected document and contains the evidence
text verbatim. Containment is strict on purpose: a chunk that cuts the evidence in half did
not retrieve the answer.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "evals" / "questions.jsonl"


def load_questions(answerable: bool | None = True) -> list[dict]:
    qs = [json.loads(line) for line in QUESTIONS.read_text().splitlines() if line.strip()]
    if answerable is None:
        return qs
    return [q for q in qs if bool(q["evidence"]) == answerable]


def is_hit(chunk, question: dict) -> bool:
    return any(chunk.doc_id == e["doc"] and e["text"] in chunk.text
               for e in question["evidence"])


def first_hit_rank(ranked_chunks: list, question: dict) -> int | None:
    """1-based rank of the first chunk that answers the question, or None."""
    for rank, c in enumerate(ranked_chunks, start=1):
        if is_hit(c, question):
            return rank
    return None


def metrics(ranks: list[int | None], ks=(1, 3, 5, 10)) -> dict[str, float]:
    n = len(ranks)
    out = {f"recall@{k}": sum(r is not None and r <= k for r in ranks) / n for k in ks}
    out["mrr@10"] = sum(1 / r for r in ranks if r is not None and r <= 10) / n
    return out
