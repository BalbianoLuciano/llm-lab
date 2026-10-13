"""Lab 12: exact numpy vs hand-written HNSW vs Qdrant (local mode and server).

    uv run labs/12-base-vectorial/run.py

How much recall is traded for speed, and what filters do to it. Vectors: every chunk the
lab 03 strategies produced (bge-m3, real data, ~15k). Ground truth: exact search with numpy.
The Qdrant server binary is expected in data/interim/qdrant-bin/ (see README).
"""

import shutil
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient, models

sys.path.insert(0, str(Path(__file__).parent))
from hnsw import HNSW

from llm_lab.chunking import by_structure, fixed_size, per_block
from llm_lab.corpus import load_corpus
from llm_lab.embeddings import Embedder
from llm_lab.retrieval_eval import load_questions

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
QDRANT_BIN = ROOT / "data" / "interim" / "qdrant-bin" / "qdrant"
K = 10
EFS = [10, 20, 50, 100, 200]


def build_dataset():
    docs = load_corpus()
    chunks, seen = [], set()
    for d in docs:
        for strategy in (lambda x: fixed_size(x, 300, 0), lambda x: fixed_size(x, 500, 100),
                         lambda x: fixed_size(x, 1000, 200), lambda x: fixed_size(x, 2000, 400),
                         per_block, lambda x: by_structure(x, 500),
                         lambda x: by_structure(x, 1000), lambda x: by_structure(x, 2000)):
            for c in strategy(d):
                if c.text not in seen:
                    seen.add(c.text)
                    chunks.append(c)
    vecs = Embedder("BAAI/bge-m3").documents([c.text for c in chunks])
    return chunks, vecs


def recall(found: list[int], truth: list[int]) -> float:
    return len(set(found) & set(truth)) / len(truth) if truth else 1.0


def timed(fn, items):
    start = time.perf_counter()
    out = [fn(x) for x in items]
    return out, (time.perf_counter() - start) / len(items) * 1000


def start_server(storage: Path) -> subprocess.Popen:
    shutil.rmtree(storage, ignore_errors=True)
    env = {"QDRANT__STORAGE__STORAGE_PATH": str(storage), "QDRANT__TELEMETRY_DISABLED": "true",
           "QDRANT__LOG_LEVEL": "WARN", "PATH": "/usr/bin:/bin"}
    proc = subprocess.Popen([str(QDRANT_BIN)], cwd=storage.parent, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen("http://localhost:6333/readyz", timeout=1)
            return proc
        except Exception:  # noqa: BLE001 — not up yet
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError("Qdrant server did not start")


def load_qdrant(client: QdrantClient, vecs, chunks) -> float:
    if client.collection_exists("lab12"):
        client.delete_collection("lab12")
    client.create_collection(
        "lab12", vectors_config=models.VectorParams(size=vecs.shape[1],
                                                    distance=models.Distance.COSINE),
        hnsw_config=models.HnswConfigDiff(m=16, ef_construct=100),
        optimizers_config=models.OptimizersConfigDiff(indexing_threshold=1000))
    for field in ("jurisdiction", "doc_id"):  # lets the server filter during the HNSW walk
        client.create_payload_index("lab12", field, models.PayloadSchemaType.KEYWORD)
    start = time.perf_counter()
    for i in range(0, len(chunks), 512):
        client.upsert("lab12", points=[
            models.PointStruct(id=j, vector=vecs[j].tolist(),
                               payload={"jurisdiction": chunks[j].meta["jurisdiction"],
                                        "doc_id": chunks[j].doc_id})
            for j in range(i, min(i + 512, len(chunks)))], wait=True)
    while client.get_collection("lab12").status != models.CollectionStatus.GREEN:
        time.sleep(0.5)  # the server builds the HNSW index in the background
    return time.perf_counter() - start


def qdrant_search(client, q, ef=None, flt=None, k=K) -> list[int]:
    params = models.SearchParams(hnsw_ef=ef) if ef else None
    res = client.query_points("lab12", query=q.tolist(), limit=k, search_params=params,
                              query_filter=flt)
    return [p.id for p in res.points]


def main() -> None:
    chunks, vecs = build_dataset()
    questions = load_questions(answerable=None)
    q_vecs = Embedder("BAAI/bge-m3").queries([q["question"] for q in questions])
    n, dim = vecs.shape
    print(f"{n} vectores de {dim} dimensiones", flush=True)
    jur = np.array([c.meta["jurisdiction"] for c in chunks])
    doc_ids = np.array([c.doc_id for c in chunks])

    # 1. Exact
    truth, exact_ms = timed(lambda q: np.argsort(-(vecs @ q))[:K].tolist(), q_vecs)
    rows = [("numpy exacto", "—", 0.0, exact_ms, 1.0, n)]

    # 2. Hand-written HNSW, with the simple neighbour rule and with the paper's heuristic
    for heuristic, label in ((False, "HNSW propio, vecinos más cercanos"),
                             (True, "HNSW propio, heurística de diversidad")):
        index = HNSW(dim, capacity=n, m=16, ef_construction=100, heuristic=heuristic)
        start = time.perf_counter()
        for v in vecs:
            index.add(v)
        build_s = time.perf_counter() - start
        print(f"{label}: construido en {build_s:.0f} s", flush=True)
        for ef in EFS:
            index.distance_evals = 0
            found, ms = timed(lambda q, ef=ef, index=index: index.search(q, K, ef), q_vecs)
            rec = statistics.mean(recall(f, t) for f, t in zip(found, truth))
            rows.append((label, ef, build_s, ms, rec, index.distance_evals / len(q_vecs)))

    # 3. Qdrant local mode
    local_path = ROOT / "data" / "interim" / "qdrant-local"
    shutil.rmtree(local_path, ignore_errors=True)
    local = QdrantClient(path=str(local_path))
    local_build = load_qdrant(local, vecs, chunks)
    found, ms = timed(lambda q: qdrant_search(local, q), q_vecs)
    rows.append(("Qdrant modo local", "—", local_build, ms,
                 statistics.mean(recall(f, t) for f, t in zip(found, truth)), n))

    # 4. Qdrant server (real HNSW)
    proc = start_server(ROOT / "data" / "interim" / "qdrant-server")
    try:
        server = QdrantClient(url="http://localhost:6333")
        server_build = load_qdrant(server, vecs, chunks)
        for ef in EFS:
            found, ms = timed(lambda q, ef=ef: qdrant_search(server, q, ef), q_vecs)
            rows.append(("Qdrant servidor", ef, server_build, ms,
                         statistics.mean(recall(f, t) for f, t in zip(found, truth)), None))

        # 5. Filters: by the question's jurisdiction (broad) and by its document (selective)
        filter_rows = []
        answerable = [(i, q) for i, q in enumerate(questions) if q["evidence"]]
        for label, field, values in [("jurisdicción", "jurisdiction", jur),
                                     ("documento", "doc_id", doc_ids)]:
            stats = {k: [] for k in ("post10", "post100", "server")}
            share = []
            for i, q in answerable:
                target = (chunks_meta_value(q, field))
                mask = values == target
                share.append(mask.mean())
                scores = vecs @ q_vecs[i]
                allowed = np.where(mask)[0]
                exact_f = allowed[np.argsort(-scores[allowed])[:K]].tolist()
                post10 = [j for j in index.search(q_vecs[i], K, 100) if mask[j]]
                post100 = [j for j in index.search(q_vecs[i], 100, 200) if mask[j]][:K]
                flt = models.Filter(must=[models.FieldCondition(
                    key=field, match=models.MatchValue(value=target))])
                srv = qdrant_search(server, q_vecs[i], 100, flt)
                for key, res in (("post10", post10), ("post100", post100), ("server", srv)):
                    stats[key].append((len(res), recall(res, exact_f)))
            for key, name in (("post10", "HNSW propio (heurística), top 10 y después filtrar"),
                              ("post100", "HNSW propio (heurística), top 100 y después filtrar"),
                              ("server", "Qdrant servidor, filtro durante la búsqueda")):
                filter_rows.append((label, statistics.mean(share), name,
                                    statistics.mean(c for c, _ in stats[key]),
                                    statistics.mean(r for _, r in stats[key])))
    finally:
        proc.terminate()

    md = ["# Lab 12: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. {n} vectores reales (bge-m3, "
           f"{dim} dimensiones), {len(q_vecs)} consultas. Verdad: búsqueda exacta con numpy."),
          "", "## Velocidad contra recall", "",
          ("| Índice | ef | Construcción (s) | Consulta (ms) | Recall@10 vs exacto | "
           "Distancias calculadas por consulta |"), "|---|---|---|---|---|---|"]
    for name, ef, b, ms, rec, evals in rows:
        md.append(f"| {name} | {ef} | {b:.1f} | {ms:.2f} | {rec:.1%} | "
                  f"{'—' if evals is None else f'{evals:,.0f}'} |")
    md += ["", "## Filtros", "",
           ("| Filtro | Fracción de vectores que pasa | Estrategia | Resultados devueltos "
            "(de 10) | Recall@10 vs exacto filtrado |"), "|---|---|---|---|---|"]
    for label, share, name, count, rec in filter_rows:
        md.append(f"| {label} | {share:.1%} | {name} | {count:.1f} | {rec:.1%} |")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


def chunks_meta_value(question: dict, field: str) -> str:
    doc = question["evidence"][0]["doc"]
    return doc if field == "doc_id" else doc.split("-")[0].upper()


if __name__ == "__main__":
    main()
