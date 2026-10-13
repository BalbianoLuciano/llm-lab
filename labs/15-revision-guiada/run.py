"""Lab 15: how many rewrites turn green without inventing data?

    uv run labs/15-revision-guiada/run.py

30 cases on red blocks from the lab 13 gold set: 20 where the (simulated) person answers with
the missing data and 10 traps where the answer does not bring it. Each case: rewrite with an API
model, re-evaluate with the lab 13 evaluator, run the deterministic and the evaluator-based
guardrails. Writes results.md with every before/after.
"""

import json
import time
from datetime import date
from pathlib import Path

from llm_lab.chunking import block_text
from llm_lab.corpus import load_document
from llm_lab.evaluator import LogprobsEvaluator, build_state
from llm_lab.models import Model
from llm_lab.review import guardrails, new_numbers, rewrite_block
from llm_lab.rules import load_rules

HERE = Path(__file__).parent
CASES = [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines()]
RUNS = HERE / "runs.jsonl"
REWRITER = [Model("groq", "qwen/qwen3.8-27b"), Model("groq", "openai/gpt-oss-120b")]
EVALUATOR_MODEL = "mlx-community/Qwen3.5-4B-4bit"  # lab 13: same accuracy as 9B, half the memory
RULE_IDS = {"R2": "r2-tablas", "R3": "r3-enlaces", "R6": "r6-moneda", "R7": "r7-fechas",
            "R8": "r8-vigencia", "R14": "r14-voz-activa"}


def main() -> None:
    rules = load_rules()
    done = {}
    if RUNS.exists():
        for line in RUNS.read_text().splitlines():
            r = json.loads(line)
            done[r["id"]] = r
    ev = LogprobsEvaluator(EVALUATOR_MODEL, permutations=2)
    for c in CASES:
        if c["id"] in done:
            continue
        doc = load_document(c["doc"])
        rule = rules[RULE_IDS[c["rule"]]]
        state = build_state(doc, c["block"])
        original = block_text(doc.blocks[c["block"]])
        before = ev.evaluate(state, rule)
        start = time.perf_counter()
        rewrite = rewrite_block(state, original, rule, c["answer"], REWRITER)
        rewrite_s = time.perf_counter() - start
        new_state = state.replace(original, rewrite)
        after = ev.evaluate(new_state, rule)
        g = guardrails(ev, original, c["answer"], rewrite)
        row = {**c, "original": original, "rewrite": rewrite,
               "before": before.level, "after": after.level,
               "after_conf": round(after.confidence, 3),
               "new_numbers": sorted(new_numbers(original, c["answer"], rewrite)),
               "marked_missing": "[FALTA" in rewrite.upper(),
               "guard_invents": g["inventa"].level, "guard_meaning": g["sentido"].level,
               "rewrite_s": round(rewrite_s, 2)}
        with RUNS.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        done[c["id"]] = row
        print(f"{c['id']} {before.level}->{after.level} nums={row['new_numbers']} "
              f"falta={row['marked_missing']} guard={row['guard_invents']}", flush=True)
    report(list(done.values()))


METRICS = [
    ("Rojo antes de corregir (según el evaluador)", lambda r: r["before"] == "red"),
    ("Verde después de corregir", lambda r: r["after"] == "green"),
    ("Ya no es rojo", lambda r: r["after"] != "red"),
    ("Números nuevos que no estaban en ningún lado", lambda r: bool(r["new_numbers"])),
    ("Dejó la marca [FALTA]", lambda r: r["marked_missing"]),
    ("Guardrail 'inventa' en rojo", lambda r: r["guard_invents"] == "red"),
    ("Guardrail 'sentido' en rojo", lambda r: r["guard_meaning"] == "red"),
]


def report(rows: list[dict]) -> None:
    normal = [r for r in rows if not r["trap"]]
    traps = [r for r in rows if r["trap"]]

    def pct(xs, cond):
        return f"{sum(cond(x) for x in xs)}/{len(xs)}"

    # A rewrite "invents" if it has numbers that are neither in the original nor in the answer
    invented = [r for r in rows if r["new_numbers"]]
    caught = [r for r in invented if r["guard_invents"] != "green"]
    false_alarm = [r for r in rows if not r["new_numbers"] and r["guard_invents"] == "red"]
    md = ["# Lab 15: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. {len(normal)} casos con respuesta "
           f"útil y {len(traps)} trampas (la respuesta no trae el dato). Reescritura: "
           f"{REWRITER[0]}; evaluador y guardrails: `{EVALUATOR_MODEL}`."), "",
          "| | Respuesta útil | Trampa |", "|---|---|---|",
          *[f"| {label} | {pct(normal, cond)} | {pct(traps, cond)} |" for label, cond in METRICS],
          "",
          (f"Reescrituras con números inventados: {len(invented)}. El guardrail del evaluador "
           f"marcó {len(caught)} (no verde). Falsas alarmas (rojo sin números nuevos): "
           f"{len(false_alarm)}."), "", "## Antes y después", ""]
    for r in sorted(rows, key=lambda r: r["id"]):
        md += [f"### {r['id']} · {r['rule']} · {r['doc']}{' · trampa' if r['trap'] else ''}",
               "", f"Respuesta de la persona: «{r['answer']}»", "",
               (f"Evaluador: {r['before']} → **{r['after']}** · números nuevos: "
                f"{', '.join(r['new_numbers']) or 'ninguno'} · guardrails: inventa "
                f"{r['guard_invents']}, sentido {r['guard_meaning']}"), "",
               "Antes:", "", "```", r["original"][:700], "```", "", "Después:", "", "```",
               r["rewrite"][:700], "```", ""]
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:16]))


if __name__ == "__main__":
    main()
