"""Lab 17: how much does a badly built index hurt the RAG? And can a System One score see it?

    uv run labs/17-base-sucia/run.py --phase retrieval   # 4 bases, dense + re-ranking, no LLM
    uv run labs/17-base-sucia/run.py --phase rag         # answers on limpia and sucia, judged
    uv run labs/17-base-sucia/run.py --phase score       # Jev-style Score on sampled chunks
    uv run labs/17-base-sucia/run.py --phase report

Lab 16 compared a clean index with the same index after rewording; both had already been
through the parsing and chunking of labs 03 and 11, so it said nothing about a dirty index.
Here the same 72 questions, the same retrieval (bge-m3 + bge-reranker-v2-m3) and the same
answering model run over four indexes (bases.py). Every step is appended as it finishes, so a
phase can be resumed after a quota cut.
"""

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from bases import BASES, build, is_hit

from llm_lab.models import Model, complete
from llm_lab.retrieval_eval import load_questions

HERE = Path(__file__).parent
OUT = HERE / "runs"
RETRIEVAL = OUT / "retrieval.json"
RAG_RUNS = OUT / "rag.jsonl"
SCORES = OUT / "score.jsonl"
ANSWERER = [Model("groq", "qwen/qwen3.8-27b"), Model("groq", "openai/gpt-oss-120b"),
            Model("local", "mlx-community/Qwen3.5-9B-4bit")]
JUDGE = [Model("groq", "openai/gpt-oss-120b"), Model("nvidia", "z-ai/glm-5.3"),
         Model("openrouter", "nvidia/nemotron-3-super-120b-a12b:free")]
COMPARED = ["limpia", "sucia"]
SAMPLE = 100  # chunks per base for the Score phase

CORRECTNESS = """Compará la RESPUESTA de un sistema con la RESPUESTA ESPERADA a una pregunta sobre
un trámite. Respondé solo con JSON: {"veredicto": "correcta"|"parcial"|"incorrecta", "motivo": str}
- correcta: tiene el dato esperado (puede agregar detalles compatibles).
- parcial: tiene parte del dato esperado o lo da con una imprecisión menor.
- incorrecta: no tiene el dato, lo contradice, o dice que no tiene la información."""

USEFUL = ("Este fragmento fue recortado de un documento para indexarlo en un buscador. Si un "
          "asistente solo pudiera leer este fragmento, ¿qué tan bien podría responder preguntas "
          "concretas sobre su contenido (montos, requisitos, plazos, lugares)?")
RUBRIC = ["Nada: es ruido (menús, pie de página, texto cortado) o no se entiende",
          "Poco: hay datos sueltos pero sin saber a qué se refieren",
          "A medias: se entiende el tema pero faltan partes para responder",
          "Bastante: responde preguntas concretas aunque le falte algo de contexto",
          "Todo: se entiende solo y tiene los datos con su contexto"]


def rows(path: Path) -> dict:
    if not path.exists():
        return {}
    return {r["key"]: r for r in map(json.loads, path.read_text().splitlines())}


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- phase 1: retrieval only


def phase_retrieval() -> None:
    from llm_lab.rag import RAG
    questions = load_questions()
    out = {}
    rag = None
    for base in BASES:
        chunks = build(base)
        rag = RAG(chunks) if rag is None else rag  # reuse the loaded models
        rag.chunks, rag.vecs = chunks, rag.emb.documents([c.text for c in chunks])
        q_vecs = rag.emb.queries([q["question"] for q in questions])
        dense, reranked = [], []
        for qi, q in enumerate(questions):
            top = np.argsort(-(rag.vecs @ q_vecs[qi]))[:10]
            dense.append(next((r for r, i in enumerate(top, 1) if is_hit(chunks[i], q)), None))
            hits = rag.retrieve(q["question"], k=5)
            reranked.append(next((r for r, h in enumerate(hits, 1) if is_hit(h.chunk, q)), None))
        out[base] = {"chunks": len(chunks), "dense": dense, "reranked": reranked,
                     "ids": [q["id"] for q in questions]}
        print(base, f"dense@10={sum(r is not None for r in dense)}/{len(dense)}",
              f"rerank@1={sum(r == 1 for r in reranked)}",
              f"rerank@5={sum(r is not None for r in reranked)}", flush=True)
    RETRIEVAL.parent.mkdir(parents=True, exist_ok=True)
    RETRIEVAL.write_text(json.dumps(out, indent=1))


# ---------------------------------------------------------------- phase 2: answers


def judge(q: dict, answer: str) -> dict:
    r = complete([{"role": "system", "content": CORRECTNESS},
                  {"role": "user", "content": f"Pregunta: {q['question']}\nRESPUESTA ESPERADA: "
                                              f"{q['answer']}\nRESPUESTA: {answer}"}],
                 JUDGE, response_format={"type": "json_object"})
    text = r.text[r.text.find("{"):r.text.rfind("}") + 1]
    return json.loads(text) | {"judge_model": str(r.model)}


def phase_rag() -> None:
    from llm_lab.rag import RAG
    questions = load_questions(answerable=None)
    done = rows(RAG_RUNS)
    rag = RAG(build(COMPARED[0]))
    vecs = {b: rag.emb.documents([c.text for c in build(b)]) for b in COMPARED}
    # interleaved, so a quota cut affects both bases alike instead of only the second one
    for q in questions:
        for base in COMPARED:
            rag.chunks, rag.vecs = build(base), vecs[base]
            key = f"{base}|{q['id']}"
            if key in done:
                continue
            ans = rag.answer(q["question"], k=5, models=ANSWERER)
            row = {"key": key, "base": base, "id": q["id"], "answerable": bool(q["evidence"]),
                   "question": q["question"], "expected": q["answer"], "answer": ans.text,
                   "model": ans.model, "abstained": ans.abstained,
                   "retrieved_hit": any(is_hit(h.chunk, q) for h in ans.hits)
                   if q["evidence"] else None}
            if q["evidence"]:
                row["correctness"] = judge(q, ans.text)
            append(RAG_RUNS, row)
            print(key, row.get("correctness", {}).get("veredicto", "abstuvo" if ans.abstained
                                                      else "respondió"), ans.model, flush=True)


# ---------------------------------------------------------------- phase 3: System One Score


def phase_score() -> None:
    from llm_lab.system_one import Score, SystemOne
    done = rows(SCORES)
    s1 = None
    for base in COMPARED:
        chunks = build(base)
        for c in random.Random(17).sample(chunks, SAMPLE):
            key = f"{base}|{c.id}"
            if key in done:
                continue
            s1 = s1 or SystemOne()
            a = s1.ask(c.text[:2500], {"useful": Score(USEFUL, RUBRIC)})["useful"]
            append(SCORES, {"key": key, "base": base, "chunk": c.id, "doc": c.doc_id,
                            "score": a["score"], "expected": a["expected"],
                            "confidence": a["confidence"], "text": c.text[:400]})
            print(key, a["score"], f"{a['expected']:.2f}", flush=True)


# ---------------------------------------------------------------- report


def phase_report() -> None:
    ret = json.loads(RETRIEVAL.read_text())
    rag = list(rows(RAG_RUNS).values())
    scores = list(rows(SCORES).values())
    n = len(ret["limpia"]["dense"])
    names = {"limpia": "Limpia (producción)", "sin_ruta": "Limpia sin ruta de títulos",
             "fijo": "Bloques limpios, cortes fijos", "sucia": "Sucia (texto crudo, cortes fijos)"}
    md = ["# Lab 17: resultados", "",
          f"Última corrida: {date.today().isoformat()}. {n} preguntas con respuesta en el corpus.",
          "", "## Recuperación", "",
          "| Base | Chunks | Denso: en el top 10 | Re-ranking: primero | Re-ranking: en el top 5 |",
          "|---|---|---|---|---|"]
    for b in BASES:
        r = ret[b]
        md.append(f"| {names[b]} | {r['chunks']} | {sum(x is not None for x in r['dense'])}/{n} "
                  f"| {sum(x == 1 for x in r['reranked'])}/{n} "
                  f"| {sum(x is not None for x in r['reranked'])}/{n} |")
    if rag:
        md += ["", "## Respuestas (mismo modelo y mismo juez en las dos bases)", "",
               ("| Base | Correctas | Parciales | Incorrectas | Dijo que no sabe teniendo el dato "
                "| Se abstuvo sin respuesta en el corpus |"), "|---|---|---|---|---|---|"]
        by = defaultdict(dict)
        for r in rag:
            by[r["base"]][r["id"]] = r
        for b in COMPARED:
            ans = [r for r in by[b].values() if r["answerable"]]
            una = [r for r in by[b].values() if not r["answerable"]]
            c = Counter(r["correctness"]["veredicto"] for r in ans)
            md.append(f"| {names[b]} | {c['correcta']}/{len(ans)} | {c['parcial']}/{len(ans)} | "
                      f"{c['incorrecta']}/{len(ans)} | {sum(r['abstained'] for r in ans)} | "
                      f"{sum(r['abstained'] for r in una)}/{len(una)} |")
        models = Counter(r["model"] for r in rag)
        md += ["", "Modelos que respondieron: " + ", ".join(f"{m} ({k})"
                                                           for m, k in models.items()), "",
               "### Preguntas que cambian de una base a la otra", ""]
        for qid in sorted(set(by["limpia"]) & set(by["sucia"])):
            a, b = by["limpia"][qid], by["sucia"][qid]
            if not a["answerable"]:
                continue
            va, vb = a["correctness"]["veredicto"], b["correctness"]["veredicto"]
            if va != vb:
                md.append(f"- **{qid}** {a['question']} — esperado: {a['expected']} — limpia: "
                          f"{va} — sucia: {vb}: {b['answer'][:200]}")
    if scores:
        md += ["", "## Score tipo Jev sobre chunks al azar", "",
               f"{SAMPLE} chunks por base, Qwen3.5-4B por logprobs, dos órdenes. Rúbrica de 1 a 5:",
               "", *[f"{i}. {t}" for i, t in enumerate(RUBRIC, 1)], "",
               "| Base | Media | 1 | 2 | 3 | 4 | 5 |", "|---|---|---|---|---|---|---|"]
        for b in COMPARED:
            s = [r for r in scores if r["base"] == b]
            if not s:
                continue
            dist = Counter(r["score"] for r in s)
            md.append(f"| {names[b]} | {np.mean([r['expected'] for r in s]):.2f} | "
                      + " | ".join(str(dist[i]) for i in range(1, 6)) + " |")
        low = sorted((r for r in scores if r["base"] == "sucia"), key=lambda r: r["expected"])[:3]
        md += ["", "Los tres chunks de la base sucia con menor puntaje:", ""]
        md += [f"- `{r['chunk']}` ({r['expected']:.2f}): "
               f"{' '.join(r['text'].split())[:180]}" for r in low]
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["retrieval", "rag", "score", "report"], required=True)
    {"retrieval": phase_retrieval, "rag": phase_rag, "score": phase_score,
     "report": phase_report}[p.parse_args().phase]()
