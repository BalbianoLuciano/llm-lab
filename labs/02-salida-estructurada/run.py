"""Lab 02: how many answers follow a schema, with and without validation, and what breaks.

Task (the one the quality gate needs for rules R6 and R8): from a passage of the corpus,
extract every amount of money with its concept, currency and effective date.

Usage:
    uv run labs/02-salida-estructurada/run.py            # run what's missing, write results.md

Four ways of asking for the same JSON:
    prompt       the schema described in the prompt, the answer parsed as-is
    json_object  JSON mode: the provider guarantees valid JSON, not the schema
    json_schema  structured outputs: the provider constrains decoding to the schema
    retry        prompt + Pydantic validation; on error, the error goes back to the model
                 (up to 2 retries)
"""

import argparse
import json
import re
import statistics
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from llm_lab.corpus import load_document
from llm_lab.models import Model, complete

HERE = Path(__file__).parent
GOLD = [json.loads(line) for line in (HERE / "gold.jsonl").read_text().splitlines()]
RUNS = HERE / "runs.jsonl"
MODELS = [
    Model("groq", "qwen/qwen3.8-27b"),
    Model("groq", "openai/gpt-oss-120b"),
    # Gemini was here first: its free tier allows 20 requests a day, it ran out at call 25
    Model("nvidia", "z-ai/glm-5.3"),
]
MODES = ["prompt", "json_object", "json_schema", "retry"]
DELAY_S = {"groq": 2.2, "nvidia": 1.6}
MAX_RETRIES = 2
INFRA_ERRORS = ("RateLimitError", "Timeout", "ConnectionError", "InternalServerError")


class Amount(BaseModel):
    concept: str = Field(description="qué se paga o qué representa el monto")
    amount: float = Field(description="el número, sin separadores de miles: 1234.5")
    currency: Literal["ARS", "USD", "EUR"] | None = Field(
        description="código ISO 4217; null si el texto no permite saberlo")
    effective_from: date | None = Field(
        description="fecha desde la que rige el monto (AAAA-MM-DD); null si no se dice")


class Extraction(BaseModel):
    amounts: list[Amount]


SYSTEM = (
    "Extraés montos de dinero de textos de trámites de la Argentina. Devolvés solo JSON, sin "
    "explicaciones. Reglas: incluí cada monto de dinero que aparezca (no porcentajes, ni "
    "fechas, ni teléfonos, ni cantidades que no sean dinero); el signo $ en estos textos son "
    "pesos argentinos (ARS); effective_from solo si el texto dice desde cuándo rige el monto; "
    "si no hay montos, devolvé {\"amounts\": []}."
)
SHAPE = ('{"amounts": [{"concept": str, "amount": number, "currency": "ARS"|"USD"|"EUR"|null, '
         '"effective_from": "AAAA-MM-DD"|null}]}')


def passage(item: dict) -> str:
    doc = load_document(item["doc"])
    idx = next(i for i, b in enumerate(doc.blocks)
               if item["contains"] in (b.text or " | ".join(" ; ".join(r) for r in b.rows)))
    parts = []
    for b in doc.blocks[idx - item["before"]: idx + 1]:
        parts.append(b.text if b.kind != "table"
                     else "\n".join("| " + " | ".join(r) + " |" for r in b.rows))
    path = " > ".join(doc.blocks[idx].path)
    return f"Documento: {doc.meta['title']}\nSección: {path or '(sin sección)'}\n\n" + \
        "\n".join(parts)


def strict_schema() -> dict:
    """Pydantic's schema adapted to what strict structured outputs accept."""
    schema = Extraction.model_json_schema()

    def fix(node):
        if isinstance(node, dict):
            node.pop("title", None)
            node.pop("format", None)  # "date" format is not supported in strict mode
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for v in node.values():
                fix(v)
        elif isinstance(node, list):
            for v in node:
                fix(v)
    fix(schema)
    return schema


def call(model: Model, mode: str, text: str) -> dict:
    messages = [{"role": "system", "content": SYSTEM}]
    user = f"Texto:\n{text}"
    if mode in ("prompt", "retry", "json_object"):
        user += f"\n\nRespondé con este formato JSON:\n{SHAPE}"
    messages.append({"role": "user", "content": user})
    fmt = None
    if mode == "json_object":
        fmt = {"type": "json_object"}
    elif mode == "json_schema":
        fmt = {"type": "json_schema",
               "json_schema": {"name": "extraction", "strict": True, "schema": strict_schema()}}

    attempts, start, tokens = 0, time.perf_counter(), 0
    while True:
        attempts += 1
        try:
            r = complete(messages, model, response_format=fmt)
        except Exception as e:  # noqa: BLE001 — a rejected request is a result too
            return {"raw": None, "error": f"{type(e).__name__}: {str(e)[:200]}",
                    "attempts": attempts, "latency_s": round(time.perf_counter() - start, 2)}
        tokens += r.output_tokens
        parsed, error = parse(r.text)
        if mode != "retry" or error is None or attempts > MAX_RETRIES:
            return {"raw": r.text, "parsed": parsed, "error": error, "attempts": attempts,
                    "latency_s": round(time.perf_counter() - start, 2), "output_tokens": tokens}
        messages += [{"role": "assistant", "content": r.text},
                     {"role": "user", "content": f"Esa respuesta no es válida: {error}. "
                                                 "Corregila y devolvé solo el JSON."}]


def parse(text: str) -> tuple[dict | None, str | None]:
    """Strict: the whole answer must be the JSON object and validate against the schema."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"no es JSON ({e.msg})"
    try:
        return Extraction.model_validate(data).model_dump(mode="json"), None
    except ValidationError as e:
        return None, f"no cumple el esquema: {e.errors()[0]['loc']} {e.errors()[0]['msg']}"


def lenient_json(text: str | None) -> bool:
    """Would it be valid JSON after stripping ``` fences and surrounding text?"""
    if not text:
        return False
    m = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        return m is not None and isinstance(json.loads(m.group()), dict)
    except json.JSONDecodeError:
        return False


def score(pred: dict | None, gold: list[dict]) -> dict:
    found = list(pred["amounts"]) if pred else []
    hits = cur_ok = date_ok = date_n = 0
    for g in gold:
        match = next((p for p in found if abs(p["amount"] - g["amount"]) < 0.01), None)
        if match is None:
            continue
        found.remove(match)
        hits += 1
        cur_ok += match["currency"] == g["currency"]
        if g["effective_from"] != "skip":
            date_n += 1
            date_ok += match["effective_from"] == g["effective_from"]
    return {"hits": hits, "gold": len(gold), "extra": len(found), "cur_ok": cur_ok,
            "date_ok": date_ok, "date_n": date_n}


def main() -> None:
    argparse.ArgumentParser().parse_args()
    done = {}
    if RUNS.exists():
        for line in RUNS.read_text().splitlines():
            r = json.loads(line)
            done[r["key"]] = r
    texts = {g["id"]: passage(g) for g in GOLD}
    last_call: dict[str, float] = defaultdict(float)
    for model in MODELS:
        for mode in MODES:
            for g in GOLD:
                key = f"{model}|{mode}|{g['id']}"
                if key in done:
                    continue
                wait = DELAY_S[model.provider] - (time.time() - last_call[model.provider])
                if wait > 0:
                    time.sleep(wait)
                last_call[model.provider] = time.time()
                out = call(model, mode, texts[g["id"]])
                if any(x in (out.get("error") or "") for x in INFRA_ERRORS):
                    # Quota limits and network failures are not results: the next run retries
                    print(f"{model!s:32} {mode:12} {g['id']} 429, retry later", flush=True)
                    time.sleep(20)
                    continue
                row = {"key": key, "model": str(model), "mode": mode, "item": g["id"], **out}
                with RUNS.open("a") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                done[key] = row
                print(f"{model!s:32} {mode:12} {g['id']} "
                      f"{'ok' if out.get('error') is None else out['error'][:70]}", flush=True)
    write_results(list(done.values()))


def write_results(rows: list[dict]) -> None:
    gold = {g["id"]: g for g in GOLD}
    md = ["# Lab 02: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. {len(gold)} pasajes "
           f"({sum(bool(g['amounts']) for g in GOLD)} con montos, "
           f"{sum(not g['amounts'] for g in GOLD)} sin montos), {len(rows)} llamadas."), "",
          ("| Modelo | Modo | Rechazada | JSON válido | Cumple esquema | JSON rescatable* | "
           "Montos encontrados | Montos inventados | Moneda | Vigencia | Intentos | "
           "Latencia p50 |"), "|" + "---|" * 12]
    groups = defaultdict(list)
    current = {str(m) for m in MODELS}
    for r in rows:
        if r["model"] in current:
            groups[(r["model"], r["mode"])].append(r)
    for (model, mode), rs in sorted(groups.items(), key=lambda x: (x[0][0], MODES.index(x[0][1]))):
        n = len(rs)
        rejected = sum(r["raw"] is None for r in rs)
        is_json = sum(r["raw"] is not None and _is_json(r["raw"]) for r in rs)
        valid = sum(r.get("parsed") is not None for r in rs)
        rescuable = sum(lenient_json(r["raw"]) for r in rs)
        s = defaultdict(int)
        for r in rs:
            for k, v in score(r.get("parsed"), gold[r["item"]]["amounts"]).items():
                s[k] += v
        md.append(
            f"| {model} | {mode} | {rejected}/{n} | {is_json}/{n} | {valid}/{n} | "
            f"{rescuable}/{n} | {s['hits']}/{s['gold']} | {s['extra']} | "
            f"{s['cur_ok']}/{s['hits']} | {s['date_ok']}/{s['date_n']} | "
            f"{statistics.mean(r['attempts'] for r in rs):.2f} | "
            f"{statistics.median(r['latency_s'] for r in rs):.2f} s |")
    md += ["", "\\* JSON rescatable: sería válido sacando ```json y el texto alrededor.",
           "", "## Errores de ejemplo", ""]
    seen = set()
    for r in rows:
        if r.get("error") and (r["model"], r["mode"]) not in seen:
            seen.add((r["model"], r["mode"]))
            md.append(f"- `{r['model']}` {r['mode']}: {r['error'][:160]}")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


if __name__ == "__main__":
    main()
