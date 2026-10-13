"""Lab 05: how much does re-ranking the top-k improve precision, and what does it cost?

    uv run labs/05-reranking/run.py

First stage: dense bge-m3 or hybrid with BM25 (lab 04 found hybrid hurts; checked again here,
since the re-ranker only needs the passage to be among the candidates). Second stage: a local
cross-encoder (bge-reranker-v2-m3) that reads question and chunk together. Also saves the
re-ranker scores of every question, answerable or not, for lab 07 (when to say "no sé").
"""

import json
import time
from datetime import date
from pathlib import Path

from sentence_transformers import CrossEncoder

from llm_lab.chunking import by_structure
from llm_lab.corpus import load_corpus
from llm_lab.embeddings import Embedder
from llm_lab.retrieval_eval import first_hit_rank, load_questions, metrics
from llm_lab.search import BM25, dense_search, rrf

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
CHUNK_CHARS = 1000
RERANKER = "BAAI/bge-reranker-v2-m3"
CANDIDATES = [10, 20, 50]


def main() -> None:
    chunks = [c for d in load_corpus() for c in by_structure(d, CHUNK_CHARS)]
    texts = [c.text for c in chunks]
    all_questions = load_questions(answerable=None)
    emb = Embedder("BAAI/bge-m3")
    doc_vecs = emb.documents(texts)
    q_vecs = emb.queries([q["question"] for q in all_questions])
    bm25 = BM25(texts)
    stages = {
        "densa (bge-m3)": [dense_search(v, doc_vecs, max(CANDIDATES)) for v in q_vecs],
        "híbrida (bge-m3 + BM25, RRF)": [
            rrf([dense_search(v, doc_vecs, 100), bm25.search(q["question"], 100)[0]],
                k=max(CANDIDATES)) for v, q in zip(q_vecs, all_questions)],
    }

    reranker = CrossEncoder(RERANKER, device="mps", max_length=512)
    reranker.predict([("hola", "hola")])  # warm-up: the first call loads kernels

    answerable = [i for i, q in enumerate(all_questions) if q["evidence"]]
    rows = []
    scores_dump = []
    for stage_name, first_stage in stages.items():
        base = [first_hit_rank([chunks[j] for j in first_stage[i][:10]], all_questions[i])
                for i in answerable]
        rows.append((f"{stage_name}, sin re-ranking", "—", metrics(base), 0.0))
        in_pool = [first_hit_rank([chunks[j] for j in first_stage[i][:max(CANDIDATES)]],
                                  all_questions[i]) is not None for i in answerable]
        print(f"{stage_name}: el pasaje está en los {max(CANDIDATES)} candidatos en "
              f"{sum(in_pool)}/{len(answerable)}", flush=True)
        for n in CANDIDATES:
            ranks, elapsed = [], 0.0
            for i, q in enumerate(all_questions):
                cand = first_stage[i][:n]
                start = time.perf_counter()
                scores = reranker.predict([(q["question"], texts[j]) for j in cand],
                                          batch_size=16, show_progress_bar=False)
                elapsed += time.perf_counter() - start
                order = [cand[j] for j in scores.argsort()[::-1]]
                if n == 20 and stage_name.startswith("densa"):
                    scores_dump.append({"id": q["id"], "answerable": bool(q["evidence"]),
                                        "top_score": float(scores.max())})
                if q["evidence"]:
                    ranks.append(first_hit_rank([chunks[j] for j in order[:10]], q))
            rows.append((f"{stage_name} + re-ranking", n, metrics(ranks),
                         elapsed / len(all_questions) * 1000))
            print(f"{stage_name} top {n} listo", flush=True)

    out = ROOT / "data" / "processed" / "lab05_reranker_scores.json"
    out.write_text(json.dumps(scores_dump, indent=1))

    md = ["# Lab 05: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. {len(chunks)} chunks, "
           f"{len(answerable)} preguntas con respuesta. Re-ranker: `{RERANKER}` en MPS."), "",
          ("| Recuperación | Candidatos | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR@10 | "
           "Re-ranking por consulta (ms) |"), "|" + "---|" * 8]
    for name, n, m, ms in rows:
        md.append(f"| {name} | {n} | {m['recall@1']:.0%} | {m['recall@3']:.0%} | "
                  f"{m['recall@5']:.0%} | {m['recall@10']:.0%} | {m['mrr@10']:.2f} | "
                  f"{ms:.0f} |")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
