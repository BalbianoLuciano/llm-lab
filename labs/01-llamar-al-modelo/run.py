"""Lab 01: what changes when varying model, system prompt, temperature and max length.

Usage:
    uv run labs/01-llamar-al-modelo/run.py             # run what's missing and write results.md
    uv run labs/01-llamar-al-modelo/run.py --only A    # a single experiment (A, B, C or D)

Each call is appended to runs.jsonl as soon as it finishes. If the run is interrupted (rate
limit, network), running again resumes where it left off: finished calls are not repeated.
The prompts and results.md are in Spanish, like the corpus and the docs.
"""

import argparse
import json
import statistics
import time
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

from llm_lab.models import Model, complete

HERE = Path(__file__).parent
QUESTIONS = [json.loads(line) for line in (HERE / "questions.jsonl").read_text().splitlines()]
RUNS = HERE / "runs.jsonl"

SYSTEM = (
    "Sos un asistente que responde preguntas sobre guías de trámites usando solo el texto "
    "que se te da. Respondé exactamente en el formato pedido, sin explicaciones."
)

MODELS = [
    Model("nvidia", "z-ai/glm-5.3"),
    Model("nvidia", "moonshotai/kimi-k3"),
    Model("groq", "openai/gpt-oss-120b"),
    Model("groq", "qwen/qwen3.8-27b"),
    Model("gemini", "gemini-3.5-flash"),
    Model("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
]
FAST = Model("groq", "qwen/qwen3.8-27b")          # no visible reasoning: good fit for B
REASONER = Model("groq", "openai/gpt-oss-120b")   # reasons before answering: good fit for D

# Minimum delay between calls per provider, to stay under the free-tier per-minute limit.
DELAY_S = {"groq": 2.2, "nvidia": 1.6, "gemini": 6.5, "openrouter": 3.2}

# Each experiment is a list of configs: (model, with_system, temperature, max_tokens, rep)
EXPERIMENTS = {
    "A": [(m, True, 0.0, None, 0) for m in MODELS],
    "B": [(FAST, True, t, None, rep) for t in (0.0, 0.7, 1.5) for rep in range(3)],
    "C": [(m, s, 0.0, None, 0) for m in (FAST, REASONER) for s in (False, True)],
    "D": [(REASONER, True, 0.0, mt, 0) for mt in (16, 64, 512, None)],
}

# Column headers for results.md (the report is in Spanish)
HEADERS = {"model": "modelo", "type": "tipo", "temperature": "temperatura",
           "with_system": "con_system", "max_tokens": "max_tokens"}


def normalize(text: str) -> str:
    no_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return no_accents.strip().strip(".").upper().replace(" ", "")


def run_key(experiment, model, with_system, temp, max_tokens, rep, question_id) -> str:
    return f"{experiment}|{model}|{with_system}|{temp}|{max_tokens}|{rep}|{question_id}"


def load_runs() -> dict[str, dict]:
    if not RUNS.exists():
        return {}
    rows = [json.loads(line) for line in RUNS.read_text().splitlines() if line.strip()]
    return {r["key"]: r for r in rows}


def run(experiment: str, done: dict[str, dict]) -> None:
    last_call = defaultdict(float)
    for model, with_system, temp, max_tokens, rep in EXPERIMENTS[experiment]:
        for q in QUESTIONS:
            k = run_key(experiment, model, with_system, temp, max_tokens, rep, q["id"])
            if k in done:
                continue
            wait = DELAY_S[model.provider] - (time.time() - last_call[model.provider])
            if wait > 0:
                time.sleep(wait)
            messages = [{"role": "system", "content": SYSTEM}] if with_system else []
            messages.append({"role": "user",
                             "content": f"Texto:\n{q['context']}\n\nPregunta: {q['question']}"})
            last_call[model.provider] = time.time()
            try:
                r = complete(messages, model, temperature=temp, max_tokens=max_tokens,
                             allow_empty=True)  # experiment D measures exactly that
            except Exception as e:  # noqa: BLE001 — no fallback on purpose: we measure THIS model
                print(f"  ! {model} {q['id']}: {str(e)[:120]}")
                continue
            row = {
                "key": k, "experiment": experiment, "model": str(model),
                "with_system": with_system, "temperature": temp, "max_tokens": max_tokens,
                "rep": rep, "question": q["id"], "type": q["type"], "expected": q["expected"],
                "answer": r.text, "correct": normalize(r.text) == normalize(q["expected"]),
                "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                "latency_s": r.latency_s,
            }
            with RUNS.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            done[k] = row
            print(f"  {experiment} {model!s:50} {q['id']} {'✓' if row['correct'] else '✗'}")


def summary(rows: list[dict], by: tuple[str, ...]) -> list[str]:
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[c] for c in by)].append(r)
    lines = [
        "| " + " | ".join(HEADERS[c] for c in by)
        + " | n | aciertos | latencia p50 (s) | tokens salida p50 |",
        "|" + "---|" * (len(by) + 4),
    ]
    for g, rs in sorted(groups.items(), key=lambda x: str(x[0])):
        acc = sum(r["correct"] for r in rs) / len(rs)
        lat = statistics.median(r["latency_s"] for r in rs)
        tok = statistics.median(r["output_tokens"] for r in rs)
        lines.append("| " + " | ".join(str(x) for x in g)
                     + f" | {len(rs)} | {acc:.0%} | {lat:.2f} | {tok:.0f} |")
    return lines


def consistency(rows: list[dict]) -> list[str]:
    """For B: what fraction of questions gets the same answer in all 3 repetitions?"""
    by_temp = defaultdict(lambda: defaultdict(set))
    for r in rows:
        by_temp[r["temperature"]][r["question"]].add(normalize(r["answer"]))
    lines = ["| temperatura | preguntas con la misma respuesta en las 3 repeticiones |",
             "|---|---|"]
    for t, questions in sorted(by_temp.items()):
        same = sum(len(a) == 1 for a in questions.values())
        lines.append(f"| {t} | {same}/{len(questions)} |")
    return lines


def write_results(done: dict[str, dict]) -> None:
    rows = list(done.values())

    def of(e):
        return [r for r in rows if r["experiment"] == e]

    def empty(mt):
        d = [r for r in of("D") if r["max_tokens"] == mt]
        return f"- max_tokens={mt}: {sum(not r['answer'].strip() for r in d)}/{len(d)}"

    errors_a = [r for r in of("A") if not r["correct"]]
    md = [
        "# Lab 01: resultados", "", (f"Última corrida: {date.today().isoformat()}. "
        f"{len(rows)} llamadas, costo US$ 0 (free tiers)."), "",
        "## A. Modelos (temperatura 0, con system prompt)", "", *summary(of("A"), ("model",)),
        "", "Por tipo de pregunta:", "", *summary(of("A"), ("model", "type")), "",
        "Errores:", "",
        *[f"- `{r['model']}` {r['question']}: esperado `{r['expected']}`, "
          f"respondió `{r['answer'].strip()[:80]}`" for r in errors_a],
        "", f"## B. Temperatura ({FAST}, 3 repeticiones)", "",
        *summary(of("B"), ("temperature",)), "", *consistency(of("B")), "",
        "## C. System prompt (temperatura 0)", "", *summary(of("C"), ("model", "with_system")),
        "", f"## D. Largo máximo ({REASONER})", "", *summary(of("D"), ("max_tokens",)), "",
        "Respuestas vacías por max_tokens:", "",
        *[empty(mt) for mt in (16, 64, 512, None)],
    ]
    (HERE / "results.md").write_text("\n".join(md) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=list(EXPERIMENTS))
    args = p.parse_args()
    done = load_runs()
    for e in [args.only] if args.only else list(EXPERIMENTS):
        print(f"Experiment {e}")
        run(e, done)
    write_results(done)
    print(f"\nresults: {HERE / 'results.md'}")


if __name__ == "__main__":
    main()
