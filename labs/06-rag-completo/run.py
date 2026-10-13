"""Lab 06: is the answer backed by what was retrieved? Correctness, faithfulness and citations.

    uv run labs/06-rag-completo/run.py

72 questions (62 answerable, 10 not). Answers from the full pipeline (src/llm_lab/rag.py),
judged by a different model than the one that answered. Citation correctness is checked
without an LLM: a cited chunk must contain the gold evidence. Every row goes to runs.jsonl,
which lab 07 (abstention) and lab 10 (judge vs human) reuse.
"""

import json
import statistics
import time
from collections import Counter
from datetime import date
from pathlib import Path

from llm_lab.models import Model, complete
from llm_lab.rag import RAG
from llm_lab.retrieval_eval import is_hit, load_questions

HERE = Path(__file__).parent
RUNS = HERE / "runs.jsonl"
ANSWERER = [Model("groq", "qwen/qwen3.8-27b"), Model("groq", "openai/gpt-oss-120b")]
JUDGE = [Model("groq", "openai/gpt-oss-120b"), Model("nvidia", "z-ai/glm-5.3")]

CORRECTNESS = """Compará la RESPUESTA de un sistema con la RESPUESTA ESPERADA a una pregunta sobre
un trámite. Respondé solo con JSON: {"veredicto": "correcta"|"parcial"|"incorrecta", "motivo": str}
- correcta: tiene el dato esperado (puede agregar detalles compatibles).
- parcial: tiene parte del dato esperado o lo da con una imprecisión menor.
- incorrecta: no tiene el dato, lo contradice, o dice que no tiene la información."""

FAITHFULNESS = """Revisá si cada afirmación de la RESPUESTA está respaldada por los FRAGMENTOS
CITADOS (los números entre corchetes). Respondé solo con JSON:
{"veredicto": "respaldada"|"parcial"|"no_respaldada", "motivo": str}
- respaldada: todo lo que afirma está en los fragmentos citados.
- parcial: algo está respaldado y algo no, o cita un fragmento equivocado.
- no_respaldada: afirma cosas que no están en los fragmentos citados, o no cita nada."""


def judge(system: str, user: str) -> dict:
    r = complete([{"role": "system", "content": system}, {"role": "user", "content": user}],
                 JUDGE, response_format={"type": "json_object"})
    return json.loads(r.text) | {"judge_model": str(r.model)}


def main() -> None:
    done = {}
    if RUNS.exists():
        for line in RUNS.read_text().splitlines():
            r = json.loads(line)
            done[r["id"]] = r
    questions = load_questions(answerable=None)
    rag = RAG.from_corpus()
    for q in questions:
        if q["id"] in done:
            continue
        start = time.perf_counter()
        try:
            ans = rag.answer(q["question"], k=5, models=ANSWERER)
        except RuntimeError as e:
            print(f"{q['id']}: {str(e)[:80]}, retry later", flush=True)
            time.sleep(20)
            continue
        latency = time.perf_counter() - start
        cited_chunks = [ans.hits[i].chunk for i in ans.cited]
        row = {"id": q["id"], "question": q["question"], "expected": q["answer"],
               "answerable": bool(q["evidence"]), "answer": ans.text, "model": ans.model,
               "abstained": ans.abstained, "top_score": ans.hits[0].score if ans.hits else None,
               "retrieved_hit": any(is_hit(h.chunk, q) for h in ans.hits) if q["evidence"]
               else None,
               "cited_hit": any(is_hit(c, q) for c in cited_chunks) if q["evidence"] else None,
               "n_cited": len(ans.cited), "latency_s": round(latency, 2),
               "fragments": [h.chunk.text[:1200] for h in ans.hits]}
        if q["evidence"]:
            row["correctness"] = judge(CORRECTNESS, f"Pregunta: {q['question']}\n"
                                                    f"RESPUESTA ESPERADA: {q['answer']}\n"
                                                    f"RESPUESTA: {ans.text}")
        cited_text = "\n\n".join(f"[{i + 1}] {ans.hits[i].chunk.text}" for i in ans.cited)
        if not ans.abstained:
            row["faithfulness"] = judge(FAITHFULNESS, f"FRAGMENTOS CITADOS:\n{cited_text or '(ninguno)'}"
                                                      f"\n\nRESPUESTA: {ans.text}")
        with RUNS.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        done[q["id"]] = row
        print(f"{q['id']} {row.get('correctness', {}).get('veredicto', '-')} "
              f"{row.get('faithfulness', {}).get('veredicto', 'abstuvo')}", flush=True)
    report(list(done.values()))


def report(rows: list[dict]) -> None:
    ans = [r for r in rows if r["answerable"]]
    unans = [r for r in rows if not r["answerable"]]
    corr = Counter(r["correctness"]["veredicto"] for r in ans)
    faith = Counter(r["faithfulness"]["veredicto"] for r in rows if "faithfulness" in r)
    n_faith = sum(faith.values())
    md = ["# Lab 06: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. Respuesta: {ANSWERER[0]}; juez: "
           f"{JUDGE[0]}. Recuperación: densa + re-ranking, top 5."), "",
          "## Preguntas con respuesta en el corpus", "",
          "| Métrica | Valor |", "|---|---|",
          (f"| El pasaje correcto está entre los 5 recuperados | "
          f"{sum(r['retrieved_hit'] for r in ans)}/{len(ans)} |"),
          f"| Respuesta correcta (juez) | {corr['correcta']}/{len(ans)} |",
          f"| Respuesta parcial (juez) | {corr['parcial']}/{len(ans)} |",
          f"| Respuesta incorrecta (juez) | {corr['incorrecta']}/{len(ans)} |",
          f"| Dijo que no sabe teniendo el dato | {sum(r['abstained'] for r in ans)}/{len(ans)} |",
          (f"| Cita el fragmento que tiene la evidencia | "
          f"{sum(bool(r['cited_hit']) for r in ans)}/{len(ans)} |"),
          (f"| Respuestas sin ninguna cita | "
          f"{sum(r['n_cited'] == 0 and not r['abstained'] for r in ans)}/{len(ans)} |"),
          "", "## Fidelidad (todas las respuestas que no se abstuvieron)", "",
          "| Veredicto del juez | Respuestas |", "|---|---|",
          *[f"| {k} | {faith[k]}/{n_faith} |" for k in ("respaldada", "parcial", "no_respaldada")],
          "", "## Preguntas sin respuesta en el corpus", "",
          f"Se abstuvo en {sum(r['abstained'] for r in unans)}/{len(unans)}.", "",
          (f"Latencia p50 por respuesta (recuperación + generación): "
          f"{statistics.median(r['latency_s'] for r in rows):.1f} s."), "",
          "## Respuestas incorrectas o no respaldadas", ""]
    for r in sorted(rows, key=lambda r: r["id"]):
        c = r.get("correctness", {}).get("veredicto")
        f = r.get("faithfulness", {}).get("veredicto")
        if c == "incorrecta" or f == "no_respaldada" or (not r["answerable"]
                                                          and not r["abstained"]):
            md.append(f"- **{r['id']}** {r['question']} — esperado: {r['expected']} — "
                      f"respondió: {r['answer'][:220]} — juez: {c or '-'} / {f or '-'}")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:30]))


if __name__ == "__main__":
    main()
