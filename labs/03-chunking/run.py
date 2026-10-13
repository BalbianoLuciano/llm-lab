"""Lab 03: which chunking retrieves the right passage most often?

    uv run labs/03-chunking/run.py

Same corpus, same embedding model (bge-m3, dense, cosine), same 62 questions. Only the way
documents are cut changes. Writes results.md.
"""

import statistics
from datetime import date
from pathlib import Path

import numpy as np

from llm_lab.chunking import by_structure, fixed_size, per_block
from llm_lab.corpus import load_corpus
from llm_lab.embeddings import Embedder
from llm_lab.retrieval_eval import first_hit_rank, load_questions, metrics

HERE = Path(__file__).parent
MODEL = "BAAI/bge-m3"

STRATEGIES = {
    "fijo 300 / 0": lambda d: fixed_size(d, 300, 0),
    "fijo 500 / 100": lambda d: fixed_size(d, 500, 100),
    "fijo 1000 / 200": lambda d: fixed_size(d, 1000, 200),
    "fijo 2000 / 400": lambda d: fixed_size(d, 2000, 400),
    "un bloque por chunk": lambda d: per_block(d),
    "estructura 500": lambda d: by_structure(d, 500),
    "estructura 1000": lambda d: by_structure(d, 1000),
    "estructura 2000": lambda d: by_structure(d, 2000),
    "estructura 1000 sin ruta": lambda d: by_structure(d, 1000, with_path=False),
}


def main() -> None:
    docs = load_corpus()
    questions = load_questions()
    emb = Embedder(MODEL)
    q_vecs = emb.queries([q["question"] for q in questions])

    rows, misses = [], {}
    for name, strategy in STRATEGIES.items():
        chunks = [c for d in docs for c in strategy(d)]
        vecs = emb.documents([c.text for c in chunks])
        scores = q_vecs @ vecs.T
        ranks = []
        for qi, q in enumerate(questions):
            top = np.argsort(-scores[qi])[:10]
            ranks.append(first_hit_rank([chunks[i] for i in top], q))
        m = metrics(ranks)
        sizes = [len(c.text) for c in chunks]
        rows.append((name, len(chunks), statistics.mean(sizes), m))
        misses[name] = [q["id"] for q, r in zip(questions, ranks) if r is None]
        print(f"{name:28} {len(chunks):6} chunks  " +
              "  ".join(f"{k}={v:.2f}" for k, v in m.items()), flush=True)

    md = ["# Lab 03: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. Modelo de embeddings: `{MODEL}` "
           f"(denso, coseno). {len(questions)} preguntas con respuesta en el corpus."), "",
          ("| Estrategia | Chunks | Largo medio (caracteres) | Recall@1 | Recall@3 | Recall@5 | "
           "Recall@10 | MRR@10 | Caracteres leídos en el top 5 |"), "|" + "---|" * 9]
    for name, n, mean_len, m in rows:
        md.append(f"| {name} | {n} | {mean_len:.0f} | {m['recall@1']:.0%} | "
                  f"{m['recall@3']:.0%} | {m['recall@5']:.0%} | {m['recall@10']:.0%} | "
                  f"{m['mrr@10']:.2f} | {5 * mean_len:,.0f} |")
    md += ["", "Preguntas sin acierto en el top 10:", ""]
    md += [f"- {name}: {', '.join(ids) or '—'}" for name, ids in misses.items()]
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
