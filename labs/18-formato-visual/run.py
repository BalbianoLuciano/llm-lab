"""Lab 18: a table where the meaning is in the colour (dark background, red text). Can a System
One detect it, ask the right question and fix it?

    uv run labs/18-formato-visual/run.py --phase detect   # 8 tables, with and without styles
    uv run labs/18-formato-visual/run.py --phase demo     # the full flow on the main case
    uv run labs/18-formato-visual/run.py --phase report

The tables are synthetic PDFs drawn with PyMuPDF (cases.py), so the ground truth is known: in
half of them the formatting carries information the words don't say. Each one is read two ways:
- plain: the table as the parser gives it today (rows and cells, no style);
- styled: the same table with the style of each row or cell written next to it
  ("[fila: fondo oscuro, texto rojo]"), taken from the PDF's drawings and text spans.
A model only reads text, so whatever the parser drops, no evaluator can see.
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cases import CASES, MAIN, make_pdf
from extract import naive_text, read_table

from llm_lab.models import Model, complete
from llm_lab.rag import SYSTEM
from llm_lab.rules import load_rules

HERE = Path(__file__).parent
OUT = HERE / "runs"
PDFS = HERE.parents[1] / "data" / "interim" / "lab18-pdfs"
MODEL = os.environ.get("LAB18_MODEL", "mlx-community/Qwen3.5-4B-4bit")
ANSWERER = [Model("groq", "qwen/qwen3.8-27b"), Model("groq", "openai/gpt-oss-120b"),
            Model("nvidia", "z-ai/glm-5.3")]

VISUAL = ("En esta tabla hay filas o celdas con un formato distinto del resto (sin contar la fila "
          "de encabezado), y ese formato comunica algo que el texto de la tabla y de la página "
          "no dice con palabras.")
FORMAT = ("Mirá las filas o celdas con un formato distinto del resto, sin contar la fila de "
          "encabezado. ¿Qué comunica ese formato?")
FORMAT_OPTIONS = {
    "ninguno": "No hay filas o celdas con formato distinto, fuera del encabezado.",
    "decorativo": "Es decorativo: filas alternadas, un total o un encabezado. No marca nada.",
    "explicado": "Marca algo de esas filas, y el texto de la tabla o de la página dice qué es.",
    "oculto": "Marca algo de esas filas que el texto no dice: solo se sabe mirando el formato.",
}
USEFUL = ("Si un asistente solo pudiera leer este texto, ¿qué tan bien podría responder "
          "preguntas concretas sobre lo que dice, sin equivocarse?")
RUBRIC = ["Nada: no se entiende o induce a error",
          "Poco: hay datos pero falta algo importante para usarlos bien",
          "A medias: sirve para algunas preguntas y para otras no",
          "Bastante: sirve, aunque podría ser más claro",
          "Todo: se entiende solo y no deja nada importante afuera"]


def questions():
    from llm_lab.system_one import Choice, Noul, Score
    r1 = load_rules()["r1-color"]
    return {
        "visual": Noul(VISUAL),
        "format": Choice(FORMAT, FORMAT_OPTIONS),
        "r1": Choice(r1.question, {"green": r1.levels.green, "yellow": r1.levels.yellow,
                                   "red": r1.levels.red}),
        "useful": Score(USEFUL, RUBRIC),
    }


def state(case: dict, table: str) -> str:
    legend = f"\n\n{case['legend']}" if case.get("legend") else ""
    return f"Documento: {case['title']}\n\n{case['intro']}\n\n{table}{legend}"


def summary(a: dict) -> dict:
    return {"visual": round(a["visual"]["noul"], 3), "format": a["format"]["choice"],
            "format_conf": round(a["format"]["confidence"], 3), "r1": a["r1"]["choice"],
            "r1_probs": {k: round(v, 3) for k, v in a["r1"]["probabilities"].items()},
            "useful": round(a["useful"]["expected"], 2)}


def phase_detect() -> None:
    from llm_lab.system_one import SystemOne
    s1, qs, out = SystemOne(MODEL), questions(), []
    for case in CASES:
        pdf = make_pdf(case, PDFS)
        table = read_table(pdf)
        for view in ("plain", "styled"):
            a = s1.ask(state(case, table[view]), qs)
            out.append({"case": case["id"], "view": view, "expected": case["visual_meaning"],
                        **summary(a)})
            print(case["id"], view, out[-1], flush=True)
    OUT.mkdir(exist_ok=True)
    (OUT / f"detect-{MODEL.split('/')[-1]}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- the full flow, main case


def ask_person(table: dict) -> str:
    """The guided-review question, built from what the parser saw: no LLM needed."""
    rows = [r["cells"][0] for r in table["rows"] if r["style"] and not r["header"]]
    style = next(r["style"] for r in table["rows"] if r["style"] and not r["header"])
    listed = " y ".join(f"«{x}»" for x in rows)
    return f"Las filas {listed} tienen {style}. ¿Qué indica ese formato?"


def apply_answer(table: dict, answer: str) -> str:
    """Write the meaning as words: a new column, filled only on the marked rows."""
    lines = []
    for r in table["rows"]:
        extra = "Observación" if r["header"] else (answer if r["style"] else "")
        lines.append("| " + " | ".join(r["cells"] + [extra]) + " |")
    return "\n".join(lines)


def rag_answer(question: str, title: str, context: str) -> dict:
    r = complete([{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": f"Fragmentos:\n\n[1] ({title})\n{context}\n\n"
                                              f"Pregunta: {question}"}], ANSWERER)
    return {"answer": r.text.strip(), "model": str(r.model)}


def phase_demo() -> None:
    from llm_lab.system_one import SystemOne
    case = next(c for c in CASES if c["id"] == MAIN)
    pdf = make_pdf(case, PDFS)
    table = read_table(pdf)
    s1, qs = SystemOne(MODEL), questions()
    question = ask_person(table)
    fixed = apply_answer(table, case["person_answer"])
    steps = {"naive_text": naive_text(pdf), "plain": table["plain"], "styled": table["styled"],
             "review_question": question, "person_answer": case["person_answer"],
             "fixed": fixed, "jev": {}}
    for view in ("plain", "styled", "fixed"):
        text = fixed if view == "fixed" else table[view]
        steps["jev"][view] = summary(s1.ask(state(case, text), qs))
        print(view, steps["jev"][view], flush=True)
    steps["answers"] = {}
    for view in ("naive_text", "plain", "fixed"):
        context = state(case, steps[view] if view != "fixed" else fixed)
        steps["answers"][view] = rag_answer(case["user_question"], case["title"], context)
        print(view, steps["answers"][view], flush=True)
    OUT.mkdir(exist_ok=True)
    (OUT / "demo.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- report


def phase_report() -> None:
    demo = json.loads((OUT / "demo.json").read_text())
    case = next(c for c in CASES if c["id"] == MAIN)
    descr = {c["id"]: c["description"] for c in CASES}
    md = ["# Lab 18: resultados", "", (f"Última corrida: {date.today().isoformat()}. "
          "Qwen3.5 en 4 bits por logprobs con dos órdenes, a través de "
          "`src/llm_lab/system_one.py`."), "",
          "- `noul`: probabilidad de que sea cierto que el formato dice algo que el texto no dice.",
          "- `format`: Choice entre ninguno, decorativo, explicado y oculto, con su confianza.",
          "- `r1`: el color de la regla R1 (Choice verde, amarillo o rojo).", ""]
    for path in sorted(OUT.glob("detect-*.json")):
        detect = json.loads(path.read_text())
        md += [f"## Detección en 8 tablas: {path.stem.removeprefix('detect-')}", "",
               "| Caso | ¿El formato dice algo que el texto no? | Vista | noul | format | r1 |",
               "|---|---|---|---|---|---|"]
        for r in detect:
            md.append(f"| {r['case']}: {descr[r['case']]} | {'sí' if r['expected'] else 'no'} | "
                      f"{r['view']} | {r['visual']:.2f} | {r['format']} ({r['format_conf']:.2f}) "
                      f"| {r['r1']} |")
        md.append("")
        for view in ("plain", "styled"):
            rs = [r for r in detect if r["view"] == view]
            pos = [r for r in rs if r["expected"]]
            neg = [r for r in rs if not r["expected"]]

            def score(flag, pos=pos, neg=neg) -> str:
                return (f"detecta {sum(map(flag, pos))}/{len(pos)}, "
                        f"falsas alarmas {sum(map(flag, neg))}/{len(neg)}")
            md.append(f"- **{view}**: Noul ≥ 0,5: {score(lambda r: r['visual'] >= 0.5)}. "
                      f"format = oculto: {score(lambda r: r['format'] == 'oculto')}. "
                      f"R1 en rojo: {score(lambda r: r['r1'] == 'red')}.")
        md.append("")
    md += ["", f"## El flujo completo: {case['description']}", "",
           "### 1. Lo que extrae un pipeline ingenuo (`get_text`)", "", "```",
           demo["naive_text"], "```", "",
           "### 2. La tabla como la da el parser hoy, y con el estilo anotado", "", "```",
           demo["plain"], "```", "", "```", demo["styled"], "```", "",
           "### 3. Pregunta de la revisión guiada y respuesta de la persona", "",
           f"> {demo['review_question']}", ">", f"> {demo['person_answer']}", "",
           "### 4. La tabla corregida (sin LLM: se agrega una columna)", "", "```",
           demo["fixed"], "```", "",
           "### 5. Las tres preguntas tipo Jev en cada paso", "",
           "| Vista | visual (Noul) | r1 (Choice) | useful (Score) |", "|---|---|---|---|"]
    for view, r in demo["jev"].items():
        md.append(f"| {view} | {r['visual']:.2f} | {r['r1']} | {r['useful']:.2f} |")
    md += ["", f"### 6. Lo que responde el asistente: «{case['user_question']}»", ""]
    for view, r in demo["answers"].items():
        md.append(f"- **{view}** ({r['model']}): {r['answer']}")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["detect", "demo", "report"], required=True)
    {"detect": phase_detect, "demo": phase_demo, "report": phase_report}[p.parse_args().phase]()
