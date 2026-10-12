"""Lab 11: compare the parsers against the hand-labelled gold set and write results.md.

    uv run labs/11-parseo/evaluate.py

Matching is lenient on purpose: case, accents, punctuation and spacing are ignored, because
what matters here is whether the structure was recovered, not the exact characters.
"""

import json
import statistics
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

from llm_lab.blocks import Block, Document

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
BLOCKS = ROOT / "data" / "processed" / "blocks"
GOLD = {k: v for k, v in json.loads((HERE / "gold.json").read_text()).items()
        if not k.startswith("_")}
PARSERS = ["manual", "docling"]


def norm(text: str) -> str:
    no_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(c for c in no_accents.lower() if c.isalnum())


def same(a: str, b: str) -> bool:
    """Equal, or one contains the other and the shorter is at least half the longer."""
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    short, long_ = sorted((a, b), key=len)
    return short in long_ and len(short) >= len(long_) / 2


def score(doc: Document, gold: dict) -> dict[str, tuple[int, int]]:
    """Each metric is (hits, total), so it can be summed across documents."""
    heads = [b for b in doc.blocks if b.kind == "heading"]
    items = [b for b in doc.blocks if b.kind == "list_item"]
    tables = [b for b in doc.blocks if b.kind == "table"]
    full_text = norm(doc.text())
    urls = [link.url for b in doc.blocks for link in b.links]

    out = {
        "heading_recall": (sum(any(same(g, h.text) for h in heads) for g in gold["headings"]),
                           len(gold["headings"])),
        "list_recall": (sum(any(norm(g) in norm(i.text) for i in items)
                            for g in gold["list_items"]), len(gold["list_items"])),
        "link_recall": (sum(any(u.startswith(g) for u in urls) for g in gold["links"]),
                        len(gold["links"])),
        "fact_recall": (sum(norm(f) in full_text for f in gold["facts"]), len(gold["facts"])),
    }
    scored = [h for h in heads if not any(same(n, h.text) for n in gold["neutral"])]
    out["heading_precision"] = (sum(any(same(g, h.text) for g in gold["headings"])
                                    for h in scored), len(scored))
    if gold["tables"] is not None:
        found = exact = 0
        for g in gold["tables"]:
            match = next((t for t in tables if _header_matches(t, g["header"])), None)
            found += match is not None
            exact += match is not None and len(match.rows) - 1 == g["rows"]
        out["tables_found"] = (found, len(gold["tables"]))
        out["tables_exact_rows"] = (exact, len(gold["tables"]))
        out["tables_extra"] = (len(tables) - found, len(tables))
    out["noise_leaked"] = (sum(norm(n) in full_text for n in gold["noise"]), len(gold["noise"]))
    extra = sum(max(0, sum(same(r, b.text) for b in doc.blocks) - 1) for r in gold["repeated"])
    out["furniture_repeats"] = (extra, 0)
    return out


def _header_matches(table: Block, header: list[str]) -> bool:
    first = norm(" ".join(table.rows[0])) if table.rows else ""
    return all(norm(h) in first for h in header)


def pct(hits: int, total: int) -> str:
    return f"{hits / total:.0%} ({hits}/{total})" if total else "—"


def main() -> None:
    docs = {p: {f.stem: Document.load(f) for f in sorted((BLOCKS / p).glob("*.json"))}
            for p in PARSERS}

    md = ["# Lab 11: resultados", "",
          (f"Última corrida: {date.today().isoformat()}. Set de oro: {len(GOLD)} documentos "
           "etiquetados a mano (`gold.json`)."), ""]

    # 1. Gold set, aggregated
    labels = {
        "heading_recall": "Títulos encontrados (recall)",
        "heading_precision": "Títulos correctos (precisión)",
        "list_recall": "Ítems de lista como ítem",
        "tables_found": "Tablas encontradas",
        "tables_exact_rows": "Tablas con todas sus filas",
        "tables_extra": "Tablas de más (falsos positivos)",
        "link_recall": "Enlaces con su URL",
        "fact_recall": "Datos clave presentes en el texto",
        "noise_leaked": "Ruido de la web que se coló (menos es mejor)",
        "furniture_repeats": "Encabezados/pies repetidos (menos es mejor)",
    }
    totals = {p: Counter() for p in PARSERS}
    per_doc = {p: {} for p in PARSERS}
    for p in PARSERS:
        for doc_id, gold in GOLD.items():
            if doc_id not in docs[p]:
                continue
            s = score(docs[p][doc_id], gold)
            per_doc[p][doc_id] = s
            for k, (h, t) in s.items():
                totals[p][k + ".h"] += h
                totals[p][k + ".t"] += t

    md += ["## 1. Contra el set de oro", "", "| Métrica | " + " | ".join(PARSERS) + " |",
           "|---|" + "---|" * len(PARSERS)]
    for k, label in labels.items():
        cells = []
        for p in PARSERS:
            h, t = totals[p][k + ".h"], totals[p][k + ".t"]
            cells.append(str(h) if k == "furniture_repeats" else pct(h, t))
        md.append(f"| {label} | " + " | ".join(cells) + " |")

    md += ["", "Por documento (títulos recall / precisión · ítems · tablas · enlaces · datos):", "",
           "| Documento | " + " | ".join(PARSERS) + " |", "|---|" + "---|" * len(PARSERS)]
    for doc_id in GOLD:
        cells = []
        for p in PARSERS:
            s = per_doc[p].get(doc_id)
            if not s:
                cells.append("—")
                continue
            parts = [f"{s['heading_recall'][0]}/{s['heading_recall'][1]}",
                     f"{s['heading_precision'][0]}/{s['heading_precision'][1]}",
                     f"{s['list_recall'][0]}/{s['list_recall'][1]}",
                     (f"{s['tables_found'][0]}/{s['tables_found'][1]}"
                      if "tables_found" in s else "—"),
                     f"{s['link_recall'][0]}/{s['link_recall'][1]}",
                     f"{s['fact_recall'][0]}/{s['fact_recall'][1]}"]
            cells.append(" · ".join(parts))
        md.append(f"| {doc_id} | " + " | ".join(cells) + " |")

    # 2. Whole corpus
    md += ["", "## 2. Todo el corpus", "",
           "| | " + " | ".join(PARSERS) + " |", "|---|" + "---|" * len(PARSERS)]
    rows = {
        "Documentos parseados": lambda ds: str(len(ds)),
        "Bloques": lambda ds: str(sum(len(d.blocks) for d in ds)),
        "Títulos": lambda ds: str(sum(b.kind == "heading" for d in ds for b in d.blocks)),
        "Ítems de lista": lambda ds: str(sum(b.kind == "list_item" for d in ds for b in d.blocks)),
        "Tablas": lambda ds: str(sum(b.kind == "table" for d in ds for b in d.blocks)),
        "Enlaces": lambda ds: str(sum(len(b.links) for d in ds for b in d.blocks)),
        "Docs sin ningún título": lambda ds: str(sum(
            not any(b.kind == "heading" for b in d.blocks) for d in ds)),
        "Tiempo total (s)": lambda ds: f"{sum(d.seconds for d in ds):.0f}",
        "Segundos por página PDF (mediana)": lambda ds: f"{statistics.median(
            d.seconds / d.pages for d in ds if d.format == 'pdf' and d.pages):.2f}",
        "Segundos por documento no PDF (mediana)": lambda ds: f"{statistics.median(
            d.seconds for d in ds if d.format != 'pdf'):.2f}",
    }
    for label, fn in rows.items():
        md.append(f"| {label} | " + " | ".join(fn(list(docs[p].values())) if docs[p] else "—"
                                               for p in PARSERS) + " |")

    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
