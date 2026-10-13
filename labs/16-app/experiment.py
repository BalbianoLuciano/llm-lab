"""Lab 16, final experiment: does correcting documents before indexing improve the answers?

    uv run labs/16-app/experiment.py --phase gate     # evaluate R6/R8 on blocks with amounts
    uv run labs/16-app/experiment.py --phase review   # guided review of the red blocks
    uv run labs/16-app/experiment.py --phase rag      # answer every question on A and B
    uv run labs/16-app/experiment.py --phase report

Each phase loads one local model at most (lab 13 lesson: two big models at once crashed the
process), and every step is saved as it finishes, so a phase can be resumed.

Corpus A: as parsed. Corpus B: the same, with the red blocks rewritten through the guided
review. The person answering the review questions is simulated by an LLM that can only use
the date-bearing sentences of its own document: it plays the author, who knows the document
but nothing else. Rewrites with numbers that are not in the document are rejected
(deterministic guardrail, lab 15).
"""

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

from llm_lab.blocks import Block
from llm_lab.chunking import block_text
from llm_lab.corpus import load_document
from llm_lab.models import Model, complete
from llm_lab.retrieval_eval import load_questions
from llm_lab.rules import load_rules

HERE = Path(__file__).parent
OUT = HERE / "experiment"
GATE = OUT / "gate.jsonl"
REVIEW = OUT / "review.jsonl"
RAG_RUNS = OUT / "rag.jsonl"
EVALUATOR_MODEL = "mlx-community/Qwen3.5-4B-4bit"
RULES = ["r6-moneda", "r8-vigencia"]
MONEY = re.compile(r"\$\s?\d|\d\s?\$|\bpesos\b|\bUT\b")
DATES = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}°? de \w+ de \d{4}|vigencia|a partir del|"
                   r"desde el|rige|vigente", re.IGNORECASE)
LLM = [Model("groq", "qwen/qwen3.8-27b"), Model("groq", "openai/gpt-oss-120b")]


def questions() -> list[dict]:
    base = load_questions(answerable=None)
    extra = [json.loads(x) for x in (HERE / "vigencia_questions.jsonl").read_text().splitlines()]
    return base + [{"id": q["id"], "question": q["question"], "answer": q["answer"],
                    "evidence": [{"doc": q["doc"], "text": q["amount"]}]} for q in extra]


def scope_docs() -> list[str]:
    return sorted({e["doc"] for q in questions() for e in q["evidence"]})


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return {r["key"]: r for r in map(json.loads, path.read_text().splitlines())}


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- phase 1: quality gate


def phase_gate() -> None:
    from llm_lab.evaluator import LogprobsEvaluator, build_state
    rules = load_rules()
    done = load(GATE)
    ev = None
    for doc_id in scope_docs():
        doc = load_document(doc_id)
        for i, b in enumerate(doc.blocks):
            text = block_text(b)
            if b.kind == "heading" or not MONEY.search(text) or len(text) > 3000:
                continue
            for rid in RULES:
                key = f"{doc_id}|{i}|{rid}"
                if key in done:
                    continue
                ev = ev or LogprobsEvaluator(EVALUATOR_MODEL, permutations=2)
                v = ev.evaluate(build_state(doc, i), rules[rid])
                append(GATE, {"key": key, "doc": doc_id, "block": i, "rule": rid,
                              "level": v.level, "probs": v.probs})
                print(key, v.level, flush=True)


# ---------------------------------------------------------------- phase 2: guided review

AUTHOR = """Sos quien escribió este documento. Te hacen una pregunta para corregir un bloque.
Contestá en una oración usando SOLO lo que dicen los fragmentos de tu documento que se te dan.
Si el dato no está, contestá exactamente: No sé."""


def phase_review() -> None:
    from llm_lab.evaluator import LogprobsEvaluator, build_state
    from llm_lab.review import new_numbers, rewrite_block
    rules = load_rules()
    gate = load(GATE)
    done = load(REVIEW)
    ev = None
    reds: dict[tuple[str, int], list[str]] = {}
    for r in gate.values():
        if r["level"] == "red":
            reds.setdefault((r["doc"], r["block"]), []).append(r["rule"])
    for (doc_id, i), rule_ids in sorted(reds.items()):
        key = f"{doc_id}|{i}"
        if key in done:
            continue
        doc = load_document(doc_id)
        original = block_text(doc.blocks[i])
        facts = "\n".join(block_text(b) for b in doc.blocks
                          if b.kind != "table" and DATES.search(block_text(b)))[:4000]
        current, answers, accepted = original, [], True
        try:
            for rid in rule_ids:
                rule = rules[rid]
                question = (f"En el documento «{doc.meta['title']}», el bloque\n{current}\n"
                            f"no cumple: {rule.levels.red} ¿Qué falta? ({rule.question})")
                answer = complete([{"role": "system", "content": AUTHOR},
                                   {"role": "user", "content": f"Fragmentos de tu documento:\n"
                                                               f"{facts}\n\n{question}"}],
                                  LLM).text.strip()
                answers.append(answer)
                if answer.lower().startswith("no sé"):
                    continue
                rewrite = rewrite_block(build_state(doc, i), current, rule, answer, LLM)
                invented = new_numbers(original, answer + "\n" + doc.text(), rewrite)
                if invented:
                    accepted = False
                    answers.append(f"[rechazada: números nuevos {sorted(invented)}]")
                    continue
                current = rewrite
        except RuntimeError as e:
            print(f"{key}: {str(e)[:80]}, retry later", flush=True)
            time.sleep(15)
            continue
        ev = ev or LogprobsEvaluator(EVALUATOR_MODEL, permutations=2)
        state = build_state(doc, i).replace(original, current)
        after = {rid: ev.evaluate(state, rules[rid]).level for rid in rule_ids}
        append(REVIEW, {"key": key, "doc": doc_id, "block": i, "rules": rule_ids,
                        "answers": answers, "original": original, "rewrite": current,
                        "changed": current != original, "accepted": accepted,
                        "after": after})
        print(key, after, "changed" if current != original else "unchanged", flush=True)


def modified_docs() -> set[str]:
    return {r["doc"] for r in load(REVIEW).values()
            if r["changed"] and "[FALTA" not in r["rewrite"].upper()}


def compared_questions() -> list[dict]:
    """Questions where A and B can differ: evidence in a modified document, the vigencia
    questions on those documents, and every unanswerable question. Elsewhere the evidence
    document is identical in both corpora (the local model takes ~1 min per question)."""
    mod = modified_docs()
    return [q for q in questions()
            if not q["evidence"] or any(e["doc"] in mod for e in q["evidence"])]


def corpus_b(doc_id: str):
    """The document with every changed, guardrail-clean rewrite applied."""
    doc = load_document(doc_id)
    for r in load(REVIEW).values():
        # a rewrite that only adds a [FALTA: ...] marker is not a fix: the block stays as it was
        if r["doc"] == doc_id and r["changed"] and "[FALTA" not in r["rewrite"].upper():
            old = doc.blocks[r["block"]]
            doc.blocks[r["block"]] = Block("paragraph", r["rewrite"], page=old.page,
                                           links=old.links, path=old.path)
    return doc


# ---------------------------------------------------------------- phase 3: RAG on A and B


LOCAL = [Model("local", "mlx-community/Qwen3.5-9B-4bit")]


def local_judge(system: str, user: str) -> dict:
    """The lab 06 judge prompt, answered by the local model (Groq's daily token cap ran out)."""
    text = complete([{"role": "system", "content": system}, {"role": "user", "content": user}],
                    LOCAL, max_tokens=200).text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group()) if match else {"veredicto": "sin_veredicto"}


def phase_rag() -> None:
    sys.path.insert(0, str(HERE.parent / "06-rag-completo"))
    from run import CORRECTNESS  # lab 06 judge prompt

    from llm_lab.corpus import load_corpus
    from llm_lab.rag import RAG
    done = load(RAG_RUNS)
    all_ids = [d.id for d in load_corpus()]
    corpora = {"A": [load_document(x) for x in all_ids],
               "B": [corpus_b(x) for x in all_ids]}
    for name, docs in corpora.items():
        rag = RAG.from_corpus(docs)
        for q in compared_questions():
            key = f"{name}|{q['id']}"
            if key in done:
                continue
            try:
                ans = rag.answer(q["question"], k=5, models=LOCAL)
                verdict = (local_judge(CORRECTNESS, f"Pregunta: {q['question']}\nRESPUESTA ESPERADA: "
                                              f"{q['answer']}\nRESPUESTA: {ans.text}")["veredicto"]
                           if q["evidence"] else None)
            except RuntimeError as e:
                print(f"{key}: {str(e)[:80]}, retry later", flush=True)
                time.sleep(15)
                continue
            append(RAG_RUNS, {"key": key, "corpus": name, "id": q["id"],
                              "answerable": bool(q["evidence"]), "answer": ans.text,
                              "abstained": ans.abstained, "verdict": verdict})
            print(key, verdict or ("abstuvo" if ans.abstained else "respondió"), flush=True)
        del rag


# ---------------------------------------------------------------- report


def phase_report() -> None:
    gate, review, rag = load(GATE), load(REVIEW), load(RAG_RUNS)
    compared = {q["id"] for q in compared_questions()}
    rag = {k: r for k, r in rag.items() if r["id"] in compared}
    md = ["# Lab 16: experimento final", "",
          (f"Última corrida: {date.today().isoformat()}. Documentos en juego: {len(scope_docs())}. "
           f"Evaluador: `{EVALUATOR_MODEL}`; respuestas y juez: `{LOCAL[0].id}` local, con "
           "los prompts del lab 06."), "",
          "## 1. Semáforo (R6 moneda, R8 vigencia) sobre bloques con montos", "",
          "| Regla | Verde | Amarillo | Rojo |", "|---|---|---|---|"]
    for rid in RULES:
        c = Counter(r["level"] for r in gate.values() if r["rule"] == rid)
        md.append(f"| {rid} | {c['green']} | {c['yellow']} | {c['red']} |")
    changed = [r for r in review.values()
               if r["changed"] and "[FALTA" not in r["rewrite"].upper()]
    marked = [r for r in review.values() if "[FALTA" in r["rewrite"].upper()]
    still_red = [r for r in changed if "red" in r["after"].values()]
    no_answer = [r for r in review.values() if not r["changed"]]
    md += ["", "## 2. Revisión guiada automática", "",
           f"- Bloques rojos revisados: {len(review)}",
           f"- Reescritos: {len(changed)} (siguen en rojo después: {len(still_red)})",
           f"- Solo marcados con [FALTA] (el documento no tiene el dato): {len(marked)}",
           (f"- Sin cambios (el autor no tenía el dato o se rechazó por números nuevos): "
           f"{len(no_answer)}"),
           (f"- Rechazos del guardrail determinista: "
           f"{sum(any('rechazada' in a for a in r['answers']) for r in review.values())}"), "",
           "## 3. RAG sobre el corpus original (A) y el corregido (B)", "",
           "| Preguntas | Corpus | Correctas | Parciales | Incorrectas | Se abstuvo |",
           "|---|---|---|---|---|---|"]
    n_q = sum(i.startswith("q") for i in compared)
    n_v = sum(i.startswith("v") for i in compared)
    groups = {f"{n_q} del set general (evidencia en un documento corregido)":
              lambda i: i.startswith("q"),
              f"{n_v} de vigencia": lambda i: i.startswith("v")}
    for label, sel in groups.items():
        for corpus in ("A", "B"):
            rows = [r for r in rag.values() if r["corpus"] == corpus and sel(r["id"])]
            c = Counter(r["verdict"] for r in rows)
            md.append(f"| {label} | {corpus} | {c['correcta']} | {c['parcial']} | "
                      f"{c['incorrecta']} | {sum(r['abstained'] for r in rows)} |")
    unans = {c: [r for r in rag.values() if r["corpus"] == c and not r["answerable"]]
             for c in ("A", "B")}
    md += ["", ("Preguntas sin respuesta en el corpus: se abstuvo en "
           f"{sum(r['abstained'] for r in unans['A'])}/{len(unans['A'])} (A) y "
           f"{sum(r['abstained'] for r in unans['B'])}/{len(unans['B'])} (B)."), "",
           "## Preguntas cuyo veredicto cambió de A a B", ""]
    by_id = {}
    for r in rag.values():
        by_id.setdefault(r["id"], {})[r["corpus"]] = r
    for qid, pair in sorted(by_id.items()):
        if len(pair) == 2 and pair["A"]["verdict"] != pair["B"]["verdict"]:
            md.append(f"- {qid}: {pair['A']['verdict']} → **{pair['B']['verdict']}** — "
                      f"B respondió: {pair['B']['answer'][:200]}")
    md += ["", "## Ejemplos de reescritura", ""]
    for r in changed[:6]:
        md += [f"**{r['key']}** ({', '.join(r['rules'])}) → {r['after']}", "", "Antes:", "",
               "```", r["original"][:500], "```", "", "Después:", "", "```",
               r["rewrite"][:500], "```", ""]
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:40]))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["gate", "review", "rag", "report"], required=True)
    args = p.parse_args()
    {"gate": phase_gate, "review": phase_review, "rag": phase_rag,
     "report": phase_report}[args.phase]()


if __name__ == "__main__":
    main()
