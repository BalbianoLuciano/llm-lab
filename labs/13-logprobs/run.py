"""Lab 13: read the probabilities of A/B/C or ask for JSON: which is more accurate, which is
better calibrated, and how much does temperature scaling help?

    uv run labs/13-logprobs/run.py                  # every evaluator, resumable
    uv run labs/13-logprobs/run.py --only qwen4b    # one evaluator

Gold: 115 (block, rule) pairs from the corpus, labelled green/yellow/red (gold.jsonl).
Results per call go to runs.jsonl; metrics to results.md.
"""

import argparse
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from llm_lab.corpus import load_document
from llm_lab.evaluator import (
    LEVELS,
    GenerativeEvaluator,
    LogprobsEvaluator,
    _softmax,
    build_state,
    expected_calibration_error,
)
from llm_lab.models import Model
from llm_lab.rules import load_rules

HERE = Path(__file__).parent
GOLD = [json.loads(line) for line in (HERE / "gold.jsonl").read_text().splitlines()]
RUNS = HERE / "runs.jsonl"
RULE_IDS = {"R2": "r2-tablas", "R3": "r3-enlaces", "R6": "r6-moneda", "R7": "r7-fechas",
            "R8": "r8-vigencia", "R14": "r14-voz-activa"}

# name -> (factory, kind). "logprobs" rows store raw letter logits for both option orders.
EVALUATORS = {
    "qwen4b": (lambda: LogprobsEvaluator("mlx-community/Qwen3.5-4B-4bit", permutations=2),
               "logprobs"),
    "qwen9b": (lambda: LogprobsEvaluator("mlx-community/Qwen3.5-9B-4bit", permutations=2),
               "logprobs"),
    # "so1-qwen4b": (lambda: LibraryEvaluator("Qwen/Qwen3.5-4B"), "probs"),
    # ^ open-alternative-jev with the Hugging Face backend on MPS: the process segfaulted twice
    #   while loading the unquantised weights (see README). Left out of the comparison.
    # Same 9B model as "qwen9b", asked for JSON instead of reading logprobs: the fair baseline
    "qwen9b-json": (lambda: GenerativeEvaluator(Model("local", "mlx-community/Qwen3.5-9B-4bit")),
                    "probs"),
    "api-qwen3.8-27b": (lambda: GenerativeEvaluator(Model("groq", "qwen/qwen3.8-27b")),
                        "probs"),
    "api-gpt-oss-120b": (lambda: GenerativeEvaluator(Model("groq", "openai/gpt-oss-120b")),
                         "probs"),
}


def run(name: str, done: dict, rules) -> None:
    factory, kind = EVALUATORS[name]
    todo = [g for g in GOLD if f"{name}|{g['doc']}|{g['block']}|{g['rule']}" not in done]
    if not todo:
        return
    ev = factory()
    for g in todo:
        key = f"{name}|{g['doc']}|{g['block']}|{g['rule']}"
        doc = load_document(g["doc"])
        assert doc.blocks[g["block"]].text[:20] in g["starts"] or doc.blocks[g["block"]].kind \
            == "table", f"block moved: {key}"
        state = build_state(doc, g["block"])
        rule = rules[RULE_IDS[g["rule"]]]
        start = time.perf_counter()
        try:
            if kind == "logprobs":
                row = {"raw": ev.raw_scores(state, rule)}
            else:
                v = ev.evaluate(state, rule)
                row = {"probs": [v.probs[lv] for lv in LEVELS]}
        except Exception as e:  # noqa: BLE001 — record and move on (rate limits, bad JSON)
            if "RateLimit" in str(e):
                print(f"{key}: 429, retry later", flush=True)
                time.sleep(20)
                continue
            row = {"error": f"{type(e).__name__}: {str(e)[:150]}"}
        row.update({"key": key, "evaluator": name, "rule": g["rule"], "gold": g["label"],
                    "latency_s": round(time.perf_counter() - start, 3)})
        with RUNS.open("a") as f:
            f.write(json.dumps(row) + "\n")
        done[key] = row
        print(f"{key} {row.get('error', 'ok')}", flush=True)


def variants(rows: list[dict]) -> dict[str, list[tuple[list[float] | None, str, str]]]:
    """Per evaluator variant: (probabilities over LEVELS or None, gold, rule) for every item."""
    out = defaultdict(list)
    for r in rows:
        name = r["evaluator"]
        if "raw" in r:
            first = _softmax(r["raw"][0])
            both = [(a + b) / 2 for a, b in zip(first, _softmax(r["raw"][1]))]
            out[f"{name}, orden dado"].append((first, r["gold"], r["rule"], r["raw"][:1]))
            out[f"{name}, dos órdenes"].append((both, r["gold"], r["rule"], r["raw"]))
        elif name.startswith("so1") and r.get("probs"):
            # log of a softmax output is a logit up to a constant: it can be re-scaled
            logs = [[math.log(max(x, 1e-12)) for x in r["probs"]]]
            out[name].append((r["probs"], r["gold"], r["rule"], logs))
        else:
            out[name].append((r.get("probs"), r["gold"], r["rule"], None))
    return out


def scaled(raw_runs: list[list[float]], t: float) -> list[float]:
    runs = [_softmax(s, t) for s in raw_runs]
    return [sum(x[i] for x in runs) / len(runs) for i in range(3)]


def cross_fit(items) -> tuple[list[list[float]], list[float]]:
    """2-fold: each half is scaled with the temperature fitted on the other half."""
    out, temps = [None] * len(items), []
    for fold in (0, 1):
        train = [it for i, it in enumerate(items) if i % 2 != fold and it[0] is not None]
        labels = [LEVELS.index(it[1]) for it in train]
        # fit on the averaged multi-order distribution by searching T directly
        grid = [0.25 + 0.05 * i for i in range(156)]
        t = min(grid, key=lambda t: -sum(math.log(max(scaled(it[3], t)[y], 1e-12))
                                          for it, y in zip(train, labels)))
        temps.append(t)
        for i, it in enumerate(items):
            if i % 2 == fold and it[0] is not None:
                out[i] = scaled(it[3], t)
    return out, temps


def summarise(items, probs) -> dict:
    valid = [(p, g) for p, (_, g, *_) in zip(probs, items) if p is not None]
    pred = [LEVELS[max(range(3), key=lambda i: p[i])] for p, _ in valid]
    gold = [g for _, g in valid]
    correct = [a == b for a, b in zip(pred, gold)]
    reds = [i for i, g in enumerate(gold) if g == "red"]
    conf = [max(p) for p, _ in valid]
    return {
        "n": len(valid), "errors": len(items) - len(valid),
        "accuracy": sum(correct) / len(valid),
        "red_recall": sum(pred[i] == "red" for i in reds) / len(reds) if reds else float("nan"),
        "red_as_green": sum(pred[i] == "green" for i in reds),
        "ece": expected_calibration_error(conf, correct),
        "mean_conf": statistics.mean(conf),
        "pred": pred, "gold": gold,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=EVALUATORS, action="append")
    args = p.parse_args()
    done = {}
    if RUNS.exists():
        for line in RUNS.read_text().splitlines():
            r = json.loads(line)
            done[r["key"]] = r
    rules = load_rules()
    for name in args.only or list(EVALUATORS):
        run(name, done, rules)

    rows = [r for r in done.values() if "error" not in r]
    errors = Counter(r["evaluator"] for r in done.values() if "error" in r)
    latency = defaultdict(list)
    for r in done.values():
        latency[r["evaluator"]].append(r["latency_s"])
    md = ["# Lab 13: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. {len(GOLD)} pares (bloque, regla) "
           f"etiquetados: {dict(Counter(g['label'] for g in GOLD))}."), "",
          ("| Evaluador | Accuracy | Recall de rojo | Rojos que pasan como verde | ECE crudo | "
           "ECE calibrado (T) | Confianza media | Latencia p50 | Errores |"),
          "|" + "---|" * 9]
    per_rule = {}
    for name, items in variants(rows).items():
        if len(items) < len(GOLD) / 2:
            continue  # evaluators cut short (the Groq daily cap): not comparable
        base = summarise(items, [it[0] for it in items])
        evaluator = name.split(",")[0]
        lat = statistics.median(latency[evaluator])
        if items[0][3] is not None:
            cal, temps = cross_fit(items)
            c = summarise(items, cal)
            ece_cal = f"{c['ece']:.3f} (T={statistics.mean(temps):.2f})"
        else:
            ece_cal = "— (sin logits)"
        md.append(f"| {name} | {base['accuracy']:.1%} | {base['red_recall']:.0%} | "
                  f"{base['red_as_green']} | {base['ece']:.3f} | {ece_cal} | "
                  f"{base['mean_conf']:.2f} | {lat:.2f} s | {errors.get(evaluator, 0)} |")
        per_rule[name] = base
    md += ["", "## Accuracy por regla", "",
           "| Evaluador | " + " | ".join(RULE_IDS) + " |", "|---|" + "---|" * len(RULE_IDS)]
    for name, base in per_rule.items():
        rules_of = [it[2] for it in variants(rows)[name]]
        cells = []
        for rule in RULE_IDS:
            idx = [i for i, r in enumerate(rules_of) if r == rule]
            ok = sum(base["pred"][i] == base["gold"][i] for i in idx)
            cells.append(f"{ok}/{len(idx)}")
        md.append(f"| {name} | " + " | ".join(cells) + " |")
    md += ["", "## Matriz de confusión del mejor evaluador (filas: oro, columnas: predicho)", ""]
    best = max(per_rule, key=lambda k: (per_rule[k]["red_recall"], per_rule[k]["accuracy"]))
    md += [f"Mejor por recall de rojo y después accuracy: **{best}**", "",
           "| | green | yellow | red |", "|---|---|---|---|"]
    cm = Counter(zip(per_rule[best]["gold"], per_rule[best]["pred"]))
    for g in LEVELS:
        md.append(f"| {g} | " + " | ".join(str(cm[(g, p)]) for p in LEVELS) + " |")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
