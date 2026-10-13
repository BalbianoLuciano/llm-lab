"""Lab 04: dense, keyword (BM25) or hybrid: which finds the right passage most often?

    uv run labs/04-embeddings-busqueda/run.py

Chunking fixed to the lab 03 winner. Compares four local embedding models, a hand-written
BM25 and the RRF fusion of BM25 with each dense model. Writes results.md.
"""

import time
from datetime import date
from pathlib import Path

from llm_lab.chunking import by_structure
from llm_lab.corpus import load_corpus
from llm_lab.embeddings import Embedder
from llm_lab.retrieval_eval import first_hit_rank, load_questions, metrics
from llm_lab.search import BM25, dense_search, rrf

HERE = Path(__file__).parent
CHUNK_CHARS = 1000  # lab 03
MODELS = [
    "intfloat/multilingual-e5-small",
    "intfloat/multilingual-e5-large",
    "BAAI/bge-m3",
    "Qwen/Qwen3-Embedding-0.6B",
]


def main() -> None:
    chunks = [c for d in load_corpus() for c in by_structure(d, CHUNK_CHARS)]
    questions = load_questions()
    texts = [c.text for c in chunks]
    results: list[tuple[str, dict, float, float]] = []
    per_question: dict[str, list] = {}

    start = time.perf_counter()
    bm25 = BM25(texts)
    index_s = time.perf_counter() - start
    start = time.perf_counter()
    bm25_rank = [bm25.search(q["question"], 20)[0] for q in questions]
    query_ms = (time.perf_counter() - start) / len(questions) * 1000
    ranks = [first_hit_rank([chunks[i] for i in r[:10]], q) for r, q in zip(bm25_rank, questions)]
    results.append(("BM25 (a mano)", metrics(ranks), index_s, query_ms))
    per_question["BM25"] = ranks

    for name in MODELS:
        emb = Embedder(name)
        start = time.perf_counter()
        doc_vecs = emb.documents(texts)
        index_s = time.perf_counter() - start  # ~0 when cached: see README for cold times
        start = time.perf_counter()
        q_vecs = emb.queries([q["question"] for q in questions])
        dense_rank = [dense_search(v, doc_vecs, 20) for v in q_vecs]
        query_ms = (time.perf_counter() - start) / len(questions) * 1000
        short = name.split("/")[-1]
        ranks = [first_hit_rank([chunks[i] for i in r[:10]], q)
                 for r, q in zip(dense_rank, questions)]
        results.append((f"densa: {short}", metrics(ranks), index_s, query_ms))
        per_question[short] = ranks
        hybrid = [rrf([d, b], k=10) for d, b in zip(dense_rank, bm25_rank)]
        ranks = [first_hit_rank([chunks[i] for i in r], q) for r, q in zip(hybrid, questions)]
        results.append((f"híbrida: {short} + BM25", metrics(ranks), index_s, query_ms))
        per_question[f"{short}+BM25"] = ranks
        print(f"{short} listo", flush=True)

    md = ["# Lab 04: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. {len(chunks)} chunks (estructura, "
           f"{CHUNK_CHARS} caracteres), {len(questions)} preguntas."), "",
          ("| Búsqueda | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR@10 | "
           "Indexado (s) | Consulta (ms) |"), "|" + "---|" * 8]
    for name, m, index_s, query_ms in results:
        md.append(f"| {name} | {m['recall@1']:.0%} | {m['recall@3']:.0%} | "
                  f"{m['recall@5']:.0%} | {m['recall@10']:.0%} | {m['mrr@10']:.2f} | "
                  f"{index_s:.1f} | {query_ms:.1f} |")
    md += ["", "Preguntas que ninguna búsqueda encuentra en el top 10:", ""]
    never = [q["id"] for i, q in enumerate(questions)
             if all(r[i] is None for r in per_question.values())]
    md.append(", ".join(never) or "ninguna")
    md += ["", "Preguntas que BM25 encuentra y la mejor densa no (o al revés):", ""]
    best = max((k for k in per_question if "+" not in k and k != "BM25"),
               key=lambda k: sum(r is not None for r in per_question[k]))
    for i, q in enumerate(questions):
        b, d = per_question["BM25"][i], per_question[best][i]
        if (b is None) != (d is None):
            md.append(f"- {q['id']} ({q['question']}): BM25 {b or '—'}, {best} {d or '—'}")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
