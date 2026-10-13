"""Lab 14: how many rules does an LLM compile right without human help?

    uv run labs/14-reglas/run.py                # compile with every model (resumable)
    uv run labs/14-reglas/run.py --evaluate     # + check compiled rules with the lab 13 evaluator

30 rules in natural language (rules_nl.jsonl): 24 with a hand-written reference compilation
(R1–R14 in rules/reference.yaml, 10 more in extra_reference.yaml) and 6 vague ones that should
come back as "ambiguous". Writes results.md.
"""

import argparse
import json
import re
import statistics
import time
from datetime import date
from pathlib import Path

import yaml

from llm_lab.compiler import compile_rule
from llm_lab.models import Model
from llm_lab.rules import Rule, load_rules

HERE = Path(__file__).parent
NL = [json.loads(line) for line in (HERE / "rules_nl.jsonl").read_text().splitlines()]
RUNS = HERE / "runs.jsonl"
MODELS = [Model("groq", "qwen/qwen3.8-27b"), Model("groq", "openai/gpt-oss-120b"),
          Model("nvidia", "z-ai/glm-5.3")]
DELAY_S = {"groq": 2.5, "nvidia": 1.6}


def references() -> dict[str, Rule]:
    refs = load_rules()
    extra = yaml.safe_load((HERE / "extra_reference.yaml").read_text())
    refs.update({r["id"]: Rule.model_validate(r) for r in extra})
    return refs


def norm_codes(source: str) -> set[str]:
    """Numeric identifiers in a source ('1.4.1', '4217', '24495-1', '15.184'), minus the WCAG
    version '2.2', which every WCAG rule mentions. Dublin Core has no number: keyword instead."""
    codes = set(re.findall(r"\d+(?:[.\-]\d+)*", source)) - {"2.2"}
    return codes | ({"dublin"} if "dublin" in source.lower() else set())


def compare(rule: Rule, ref: Rule) -> dict[str, float]:
    a, b = set(rule.applies_to), set(ref.applies_to)
    ref_codes = norm_codes(ref.source)
    return {
        "kind": rule.kind == ref.kind,
        "scope": rule.scope == ref.scope,
        "blocking": rule.blocking == ref.blocking,
        "applies_to": len(a & b) / len(a | b),
        "source": bool(ref_codes & norm_codes(rule.source)) if ref_codes else True,
        "examples": len(rule.examples) >= 2,
    }


def compile_all(done: dict) -> None:
    last: dict[str, float] = {}
    for model in MODELS:
        for i, item in enumerate(NL):
            key = f"{model}|{i}"
            if key in done:
                continue
            wait = DELAY_S[model.provider] - (time.time() - last.get(model.provider, 0))
            if wait > 0:
                time.sleep(wait)
            last[model.provider] = time.time()
            start = time.perf_counter()
            try:
                result, attempts, error = compile_rule(item["text"], model)
            except RuntimeError as e:
                if any(x in str(e) for x in ("RateLimit", "Timeout", "Connection",
                                             "InternalServer")):
                    print(f"{key}: 429, retry later", flush=True)
                    time.sleep(20)
                    continue
                result, attempts, error = None, 0, str(e)[:200]
            row = {"key": key, "model": str(model), "item": i, "ref": item["ref"],
                   "result": result.model_dump(mode="json") if result else None,
                   "attempts": attempts, "error": error,
                   "latency_s": round(time.perf_counter() - start, 2)}
            with RUNS.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            done[key] = row
            print(f"{key} {result.status if result else 'FAIL ' + str(error)[:60]}", flush=True)


def report(done: dict, evaluation: dict | None) -> None:
    refs = references()
    md = ["# Lab 14: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. {len(NL)} reglas en lenguaje natural: "
           f"{sum(1 for x in NL if x['ref'])} compilables y {sum(1 for x in NL if not x['ref'])} "
           "vagas."), "",
          ("| Modelo | Esquema válido | Vagas detectadas | Compilables marcadas vagas | kind | "
           "scope | blocking | applies_to (Jaccard) | Norma correcta | Todo bien sin editar | "
           "Intentos medios |"), "|" + "---|" * 11]
    for model in MODELS:
        rows = [r for r in done.values() if r["model"] == str(model)]
        if not rows:
            continue
        valid = [r for r in rows if r["result"]]
        vague = [r for r in rows if r["ref"] is None]
        ok = [r for r in rows if r["ref"] is not None]
        vague_hit = sum(bool(r["result"]) and r["result"]["status"] == "ambiguous" for r in vague)
        false_vague = sum(bool(r["result"]) and r["result"]["status"] == "ambiguous" for r in ok)
        cmp = [compare(Rule.model_validate(r["result"]["rule"]), refs[r["ref"]])
               for r in ok if r["result"] and r["result"]["status"] == "ok"]
        perfect = sum(all(v is True or v == 1.0 for v in c.values()) for c in cmp)

        def mean(field, cmp=cmp):
            return statistics.mean(float(c[field]) for c in cmp) if cmp else 0

        md.append(f"| {model} | {len(valid)}/{len(rows)} | {vague_hit}/{len(vague)} | "
                  f"{false_vague}/{len(ok)} | {mean('kind'):.0%} | {mean('scope'):.0%} | "
                  f"{mean('blocking'):.0%} | {mean('applies_to'):.2f} | {mean('source'):.0%} | "
                  f"{perfect}/{len(ok)} | {statistics.mean(r['attempts'] for r in rows):.2f} |")
    md += ["", "## Diferencias con la referencia (primer modelo)", ""]
    first = str(MODELS[0])
    for r in sorted((r for r in done.values() if r["model"] == first), key=lambda r: r["item"]):
        if not r["result"]:
            md.append(f"- {NL[r['item']]['text'][:60]}…: falló ({r['error']})")
            continue
        if r["ref"] is None:
            md.append(f"- vaga «{NL[r['item']]['text']}» → {r['result']['status']}: "
                      f"{(r['result'].get('clarification') or '')[:140]}")
            continue
        if r["result"]["status"] != "ok":
            md.append(f"- {r['ref']}: marcada como vaga")
            continue
        rule = Rule.model_validate(r["result"]["rule"])
        c = compare(rule, refs[r["ref"]])
        wrong = [k for k, v in c.items() if v is not True and v != 1.0]
        if wrong:
            ref = refs[r["ref"]]
            details = "; ".join(f"{k}: {getattr(rule, k)} (ref {getattr(ref, k)})"
                                for k in wrong if k != "examples")
            md.append(f"- {r['ref']}: {details}")
    if evaluation:
        md += ["", "## ¿Las reglas compiladas sirven para evaluar?", "", *evaluation["lines"]]
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


def evaluate_compiled(done: dict) -> dict:
    """Run the lab 13 evaluator with compiled rules: on their own examples, and on the lab 13
    gold set for the rules that are in both."""
    from llm_lab.corpus import load_document
    from llm_lab.evaluator import LogprobsEvaluator, build_state

    ev = LogprobsEvaluator(EVALUATOR_MODEL, permutations=2)
    refs = references()
    gold13 = [json.loads(x) for x in (HERE.parent / "13-logprobs" / "gold.jsonl").read_text()
              .splitlines()]
    rule_ids = {"R2": "r2-tablas", "R3": "r3-enlaces", "R6": "r6-moneda", "R7": "r7-fechas",
                "R8": "r8-vigencia", "R14": "r14-voz-activa"}
    lines = [f"Evaluador: `{EVALUATOR_MODEL}`, dos órdenes de opciones (lab 13).", ""]
    first = str(MODELS[0])
    compiled = {r["ref"]: Rule.model_validate(r["result"]["rule"]) for r in done.values()
                if r["model"] == first and r["ref"] and r["result"]
                and r["result"]["status"] == "ok"}
    own_ok = own_n = 0
    for rule in compiled.values():
        if rule.kind != "semantic":
            continue
        for ex in rule.examples:
            state = f"[BLOQUE A EVALUAR]\n{ex.text}"
            own_ok += ev.evaluate(state, rule).level == ex.expected
            own_n += 1
    lines.append(f"- Ejemplos propios de cada regla compilada que el evaluador clasifica como "
                 f"dice la regla: {own_ok}/{own_n}.")
    lines += ["", "| Regla | Accuracy con la regla de referencia | Accuracy con la compilada |",
              "|---|---|---|"]
    for short, rid in rule_ids.items():
        if rid not in compiled:
            continue
        items = [g for g in gold13 if g["rule"] == short]
        hits = {"ref": 0, "comp": 0}
        for g in items:
            state = build_state(load_document(g["doc"]), g["block"])
            hits["ref"] += ev.evaluate(state, refs[rid]).level == g["label"]
            hits["comp"] += ev.evaluate(state, compiled[rid]).level == g["label"]
        lines.append(f"| {rid} | {hits['ref']}/{len(items)} | {hits['comp']}/{len(items)} |")
    return {"lines": lines}


EVALUATOR_MODEL = "mlx-community/Qwen3.5-4B-4bit"  # lab 13: same accuracy as 9B, half the memory


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--evaluate", action="store_true")
    args = p.parse_args()
    done = {}
    if RUNS.exists():
        for line in RUNS.read_text().splitlines():
            r = json.loads(line)
            done[r["key"]] = r
    compile_all(done)
    report(done, evaluate_compiled(done) if args.evaluate else None)


if __name__ == "__main__":
    main()
