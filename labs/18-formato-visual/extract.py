"""Read a table from a PDF keeping what the eye sees: background fills and text colour.

    table = read_table(Path("c2.pdf"))
    table["plain"]    # | Renovación | $35.000 | Con turno previo |
    table["styled"]   # | Renovación | $35.000 | Con turno previo |  [fila: fondo oscuro, texto rojo]

PyMuPDF gives the text spans (with colour and font flags) and the vector drawings (with their
fill). A span's background is the filled rectangle under its centre. Rows are spans that share
a baseline and have more than one cell, which is enough for these synthetic tables; on real
documents the cell boxes would come from Docling's table structure and the style lookup is
the same.
"""

from pathlib import Path

import pymupdf


def _rgb(color: int) -> tuple[float, float, float]:
    return ((color >> 16 & 255) / 255, (color >> 8 & 255) / 255, (color & 255) / 255)


def _luminance(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def describe(fg, bg, bold: bool) -> str:
    """Words for what a reader sees; empty for plain black text on white."""
    parts = []
    if bg is not None and _luminance(bg) < 0.4:
        parts.append("fondo oscuro")
    elif bg is not None and _luminance(bg) < 0.97:
        parts.append("fondo gris claro")
    if fg[0] > 0.6 and fg[1] < 0.35 and fg[2] < 0.35:
        parts.append("texto rojo")
    elif _luminance(fg) > 0.8:
        parts.append("texto blanco")
    if bold:
        parts.append("negrita")
    return ", ".join(parts)


def naive_text(path: Path) -> str:
    with pymupdf.open(path) as pdf:
        return pdf[0].get_text().strip()


def read_table(path: Path) -> dict:
    with pymupdf.open(path) as pdf:
        page = pdf[0]
        fills = [(d["rect"], d["fill"]) for d in page.get_drawings() if d.get("fill")]
        spans = [s for b in page.get_text("dict")["blocks"] for line in b.get("lines", [])
                 for s in line["spans"] if s["text"].strip()]
    lines: dict[int, list] = {}
    for s in spans:
        lines.setdefault(round(s["origin"][1]), []).append(s)
    rows = []
    for _, line in sorted(lines.items()):
        if len(line) < 2:
            continue  # title, intro, legend: not part of the table
        cells = []
        for s in sorted(line, key=lambda s: s["bbox"][0]):
            x, y = (s["bbox"][0] + s["bbox"][2]) / 2, (s["bbox"][1] + s["bbox"][3]) / 2
            under = [f for r, f in fills if r.contains(pymupdf.Point(x, y))]
            cells.append((s["text"].strip(), describe(_rgb(s["color"]), under[-1] if under
                                                      else None, bool(s["flags"] & 16))))
        rows.append(cells)
    out = []
    for i, cells in enumerate(rows):
        styles = {st for _, st in cells}
        row_style = cells[0][1] if len(styles) == 1 else ""
        out.append({"cells": [t for t, _ in cells], "style": row_style, "header": i == 0,
                    "cell_styles": {} if row_style or styles == {""} else
                    {j: st for j, (_, st) in enumerate(cells) if st}})

    def render(styled: bool) -> str:
        lines = []
        for r in out:
            cells = [f"{t} [{r['cell_styles'][j]}]" if styled and j in r["cell_styles"] else t
                     for j, t in enumerate(r["cells"])]
            note = f"  [fila: {r['style']}]" if styled and r["style"] else ""
            lines.append("| " + " | ".join(cells) + " |" + note)
        return "\n".join(lines)

    return {"rows": out, "plain": render(False), "styled": render(True)}
