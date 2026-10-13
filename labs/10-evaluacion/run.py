"""Lab 10: does an automatic judge agree with a hand-labelled set?

    uv run labs/10-evaluacion/run.py

The lab 06 answers to the 62 answerable questions, labelled by hand as correcta / parcial /
incorrecta (labels.jsonl, with who labelled them). Three automatic judges are compared against
those labels: the API judge lab 06 used, a second API model, and the local logprobs evaluator
from lab 13 (no text generated). Metrics: raw agreement and Cohen's kappa.
"""

import argparse
import json
import time
from collections import Counter
from datetime import date
from pathlib import Path

from llm_lab.evaluator import LogprobsEvaluator
from llm_lab.models import Model, complete
from llm_lab.rules import Levels, Rule

HERE = Path(__file__).parent
LAB06 = {r["id"]: r for r in map(json.loads, (HERE.parent / "06-rag-completo" / "runs.jsonl")
                                 .read_text().splitlines())}
LABELS = {r["id"]: r for r in map(json.loads, (HERE / "labels.jsonl").read_text().splitlines())}
RUNS = HERE / "runs.jsonl"
CLASSES = ["correcta", "parcial", "incorrecta"]
EVALUATOR_MODEL = "mlx-community/Qwen3.5-4B-4bit"  # lab 13

CORRECTNESS_RULE = Rule(
    id="respuesta-correcta", source="lab 10", kind="semantic", scope="block",
    applies_to=["paragraph"],
    question="¿La RESPUESTA tiene el dato de la RESPUESTA ESPERADA?",
    levels=Levels(green="Sí: tiene el dato esperado (puede agregar detalles compatibles).",
                  yellow="En parte: tiene parte del dato o una imprecisión menor.",
                  red="No: no tiene el dato, lo contradice o dice que no tiene la información."),
    blocking=False)
LEVEL_TO_CLASS = {"green": "correcta", "yellow": "parcial", "red": "incorrecta"}


def kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[c] * cb[c] for c in CLASSES) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def api_judge(model: Model, row: dict) -> str:
    system = (HERE.parent / "06-rag-completo" / "run.py").read_text().split(
        'CORRECTNESS = """')[1].split('"""')[0]
    r = complete([{"role": "system", "content": system},
                  {"role": "user", "content": f"Pregunta: {row['question']}\nRESPUESTA ESPERADA: "
                                              f"{row['expected']}\nRESPUESTA: {row['answer']}"}],
                 model, response_format={"type": "json_object"})
    return json.loads(r.text)["veredicto"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report-only", action="store_true", help="no new judge calls")
    args = p.parse_args()
    ids = sorted(i for i in LABELS if i in LAB06)
    done = {}
    if RUNS.exists():
        for line in RUNS.read_text().splitlines():
            r = json.loads(line)
            done[(r["judge"], r["id"])] = r["label"]
    for i in ids:
        done[("gpt-oss-120b (lab 06)", i)] = LAB06[i]["correctness"]["veredicto"]

    second = Model("groq", "qwen/qwen3.8-27b")
    local = None
    for i in [] if args.report_only else ids:
        for name in (str(second), f"local logprobs {EVALUATOR_MODEL.split('/')[-1]}"):
            if (name, i) in done:
                continue
            row = LAB06[i]
            try:
                if name.startswith("local"):
                    local = local or LogprobsEvaluator(EVALUATOR_MODEL, permutations=2)
                    state = (f"Pregunta: {row['question']}\nRESPUESTA ESPERADA: "
                             f"{row['expected']}\n\n[BLOQUE A EVALUAR: RESPUESTA]\n{row['answer']}")
                    label = LEVEL_TO_CLASS[local.evaluate(state, CORRECTNESS_RULE).level]
                else:
                    label = api_judge(second, row)
            except Exception as e:  # noqa: BLE001
                print(f"{name} {i}: {str(e)[:80]}", flush=True)
                time.sleep(15)
                continue
            done[(name, i)] = label
            with RUNS.open("a") as f:
                f.write(json.dumps({"judge": name, "id": i, "label": label}) + "\n")

    human = [LABELS[i]["label"] for i in ids]
    who = Counter(LABELS[i]["labeller"] for i in ids)
    md = ["# Lab 10: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. {len(ids)} respuestas del lab 06. "
           f"Etiquetas de referencia: {dict(who)}; distribución {dict(Counter(human))}."), "",
          "| Juez | Acuerdo | Kappa de Cohen | Correctas según el juez |", "|---|---|---|---|"]
    judges = sorted({j for j, _ in done})
    for j in judges:
        pred = [done.get((j, i)) for i in ids]
        pairs = [(h, p) for h, p in zip(human, pred) if p]
        if not pairs:
            continue
        a, b = zip(*pairs)
        md.append(f"| {j} ({len(pairs)} respuestas) | {sum(x == y for x, y in pairs) / len(pairs):.0%} | "
                  f"{kappa(list(a), list(b)):.2f} | {Counter(b)['correcta']}/{len(pairs)} |")
    md += ["", "## Desacuerdos con las etiquetas a mano", ""]
    for i, h in zip(ids, human):
        votes = {j: done.get((j, i)) for j in judges}
        if any(v and v != h for v in votes.values()):
            md.append(f"- {i} (a mano: {h}) " + ", ".join(f"{j}: {v}" for j, v in votes.items())
                      + f" — «{LAB06[i]['answer'][:150]}»")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:12]))


if __name__ == "__main__":
    main()
