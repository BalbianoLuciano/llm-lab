"""Lab 07: does the system say "no tengo esa información" instead of making something up?

    uv run labs/07-cuando-no-sabe/run.py

Two abstention signals, measured on the lab 06 answers (62 answerable, 10 not):
- the model's own refusal (the prompt tells it to answer NO_INFO when the fragments don't help);
- a threshold on the re-ranker score of the best chunk: below it, nothing is generated.
The threshold is chosen with leave-one-out, so the reported numbers are not fitted on the same
question they are measured on.
"""

import json
import sys
import time
from datetime import date
from pathlib import Path

from llm_lab.models import Model, complete
from llm_lab.rag import NO_INFO, SYSTEM

HERE = Path(__file__).parent
ROWS = [json.loads(x) for x in (HERE.parent / "06-rag-completo" / "runs.jsonl").read_text()
        .splitlines()]


# Variant B: same rules, plus an explicit push against refusing when the words differ
SYSTEM_B = SYSTEM.replace(
    f'- Si los fragmentos no responden la pregunta, respondé exactamente: "{NO_INFO}"',
    "- La pregunta puede usar otras palabras, sinónimos o siglas que los fragmentos: si algún "
    "fragmento tiene el dato, respondé.\n"
    f'- Solo si ningún fragmento tiene el dato, respondé exactamente: "{NO_INFO}"')
VARIANT_RUNS = HERE / "runs_prompt_b.jsonl"
ANSWERER = [Model("groq", "qwen/qwen3.8-27b")]


def prompt_variant(rows) -> list[dict]:
    """Re-ask every question with prompt B over the same fragments lab 06 retrieved."""
    sys.path.insert(0, str(HERE.parent / "06-rag-completo"))
    from run import CORRECTNESS, judge  # lab 06 judge, same prompt
    done = {}
    if VARIANT_RUNS.exists():
        done = {r["id"]: r for r in map(json.loads, VARIANT_RUNS.read_text().splitlines())}
    for r in rows:
        if r["id"] in done:
            continue
        context = "\n\n".join(f"[{n}] {f}" for n, f in enumerate(r["fragments"], start=1))
        try:
            out = complete([{"role": "system", "content": SYSTEM_B},
                            {"role": "user", "content": f"Fragmentos:\n\n{context}\n\n"
                                                        f"Pregunta: {r['question']}"}], ANSWERER)
            row = {"id": r["id"], "answerable": r["answerable"], "answer": out.text.strip(),
                   "abstained": NO_INFO.lower()[:25] in out.text.lower()}
            if r["answerable"] and not row["abstained"]:
                row["verdict"] = judge(CORRECTNESS, f"Pregunta: {r['question']}\nRESPUESTA "
                                                    f"ESPERADA: {r['expected']}\nRESPUESTA: "
                                                    f"{row['answer']}")["veredicto"]
        except Exception as e:  # noqa: BLE001 — rate limits: next run retries
            print(f"{r['id']}: {str(e)[:80]}", flush=True)
            time.sleep(15)
            continue
        with VARIANT_RUNS.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        done[r["id"]] = row
    return list(done.values())


def decide(rows, threshold, use_model=True, use_threshold=True):
    out = []
    for r in rows:
        abstain = (use_model and r["abstained"]) or (use_threshold and r["top_score"] < threshold)
        out.append(abstain)
    return out


def score(rows, abstains) -> dict:
    ans = [a for r, a in zip(rows, abstains) if r["answerable"]]
    unans = [a for r, a in zip(rows, abstains) if not r["answerable"]]
    # an answerable question is "lost" if we abstain or the answer was judged incorrect
    wrong_answer = [r.get("correctness", {}).get("veredicto") == "incorrecta"
                    for r in rows if r["answerable"]]
    return {
        "abstain_unanswerable": sum(unans), "n_unans": len(unans),
        "abstain_answerable": sum(ans), "n_ans": len(ans),
        "answered_wrong": sum(w and not a for w, a in zip(wrong_answer, ans)),
    }


def best_threshold(rows, use_model) -> float:
    """Maximise correct decisions: abstain on unanswerable, answer the answerable ones.
    Abstaining on an answerable question costs as much as answering an unanswerable one."""
    candidates = sorted({r["top_score"] for r in rows}) + [float("inf")]
    candidates = [float("-inf")] + candidates

    def utility(t):
        d = decide(rows, t, use_model=use_model)
        return sum((not r["answerable"]) == a for r, a in zip(rows, d))
    return max(candidates, key=utility)


def main() -> None:
    rows = [r for r in ROWS if r.get("top_score") is not None]
    md = ["# Lab 07: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. {sum(r['answerable'] for r in rows)} "
           f"preguntas con respuesta y {sum(not r['answerable'] for r in rows)} sin respuesta "
           "(respuestas del lab 06)."), "",
          ("| Estrategia | Se abstiene cuando no hay respuesta | Se abstiene teniendo la "
           "respuesta | Responde mal (juez) | Umbral |"), "|---|---|---|---|---|"]

    def add(name, abstains, threshold="—"):
        s = score(rows, abstains)
        md.append(f"| {name} | {s['abstain_unanswerable']}/{s['n_unans']} | "
                  f"{s['abstain_answerable']}/{s['n_ans']} | {s['answered_wrong']} | "
                  f"{threshold} |")

    add("Solo el modelo", decide(rows, 0, use_threshold=False))
    for use_model, name in ((False, "Solo umbral del re-ranker"),
                            (True, "Modelo + umbral del re-ranker")):
        # leave-one-out: the threshold for each question is fitted on the other 71
        abstains = []
        for i, r in enumerate(rows):
            t = best_threshold(rows[:i] + rows[i + 1:], use_model)
            abstains.append(decide([r], t, use_model=use_model)[0])
        t_all = best_threshold(rows, use_model)
        add(name + " (validación dejando uno afuera)", abstains, f"{t_all:.2f}")

    b = prompt_variant(rows)
    ans_b = [x for x in b if x["answerable"]]
    md += ["", "## Variante del prompt: \"respondé aunque la pregunta use otras palabras\"", "",
           ("| Prompt | Se abstiene cuando no hay respuesta | Se abstiene teniendo la respuesta | "
           "Responde mal (juez) |"), "|---|---|---|---|",
           (f"| A (lab 06) | {sum(r['abstained'] for r in rows if not r['answerable'])}/"
           f"{sum(not r['answerable'] for r in rows)} | "
           f"{sum(r['abstained'] for r in rows if r['answerable'])}/"
           f"{sum(r['answerable'] for r in rows)} | "
           f"{sum(r.get('correctness', {}).get('veredicto') == 'incorrecta' and not r['abstained'] for r in rows)} |"),
           (f"| B | {sum(x['abstained'] for x in b if not x['answerable'])}/"
           f"{sum(not x['answerable'] for x in b)} | {sum(x['abstained'] for x in ans_b)}/"
           f"{len(ans_b)} | {sum(x.get('verdict') == 'incorrecta' for x in ans_b)} |")]
    md += ["", "Preguntas sin respuesta que el prompt B contestó igual:", ""]
    md += [f"- {x['id']}: {x['answer'][:200]}" for x in b
           if not x["answerable"] and not x["abstained"]] or ["- ninguna"]
    md += ["", "## Puntaje del mejor fragmento según el re-ranker", "",
           "| Preguntas | Mínimo | Mediana | Máximo |", "|---|---|---|---|"]
    for label, cond in (("con respuesta", True), ("sin respuesta", False)):
        s = sorted(r["top_score"] for r in rows if r["answerable"] == cond)
        md.append(f"| {label} | {s[0]:.2f} | {s[len(s) // 2]:.2f} | {s[-1]:.2f} |")
    md += ["", "## Preguntas sin respuesta: qué hizo el sistema", ""]
    for r in rows:
        if not r["answerable"]:
            md.append(f"- {r['id']} {r['question']} — puntaje {r['top_score']:.2f} — "
                      f"{'se abstuvo' if r['abstained'] else 'respondió: ' + r['answer'][:160]}")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
