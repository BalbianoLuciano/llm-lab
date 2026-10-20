"""Eight synthetic tables drawn as PDFs, with a known answer: does the formatting say something
the words don't? The organisation and the numbers are made up.

The main case (MAIN) is the one from the original problem: a fee table where some rows have a
dark background and red text, and nothing on the page says what that means.
"""

from pathlib import Path

import pymupdf

MAIN = "c2"
TITLE = "Registro de ejemplo: aranceles 2026"
INTRO = "Valores vigentes para los trámites presenciales del registro."
HEADER = ["Trámite", "Arancel", "Turno"]
ROWS = [["Licencia nueva", "$42.230", "Con turno previo"],
        ["Renovación", "$35.000", "Con turno previo"],
        ["Duplicado", "$23.460", "Sin turno"],
        ["Cambio de domicilio", "$8.900", "Sin turno"],
        ["Certificado de antecedentes", "$5.100", "Sin turno"]]

# style: (background or None, text colour, bold)
STYLES = {
    "normal": (None, (0, 0, 0), False),
    "header": ((0.12, 0.12, 0.12), (1, 1, 1), True),
    "alert": ((0.15, 0.15, 0.15), (0.85, 0.06, 0.1), False),  # dark background, red text
    "red": (None, (0.85, 0.06, 0.1), False),
    "bold": (None, (0, 0, 0), True),
    "zebra": ((0.92, 0.92, 0.92), (0, 0, 0), False),
}


def _rows(styles: dict[int, str] | None = None, cells: dict[tuple[int, int], str] | None = None,
          extra: list[str] | None = None) -> list[dict]:
    out = [{"cells": HEADER + ([extra[0]] if extra else []), "style": "header"}]
    for i, r in enumerate(ROWS):
        row = {"cells": r + ([extra[i + 1]] if extra else []),
               "style": (styles or {}).get(i, "normal"), "cell_styles": {}}
        for (ri, ci), s in (cells or {}).items():
            if ri == i:
                row["cell_styles"][ci] = s
        out.append(row)
    return out


CASES = [
    {"id": "c1", "description": "solo el encabezado oscuro", "visual_meaning": False,
     "rows": _rows()},
    {"id": "c2", "description": "dos filas con fondo oscuro y texto rojo, sin leyenda",
     "visual_meaning": True, "rows": _rows({1: "alert", 2: "alert"}),
     "user_question": "¿Cuánto sale renovar la licencia y puedo hacerlo esta semana?",
     "person_answer": "Suspendido hasta el 30/11/2026 por cambio de sistema"},
    {"id": "c3", "description": "las mismas filas, con una leyenda que lo explica",
     "visual_meaning": False, "rows": _rows({1: "alert", 2: "alert"}),
     "legend": "Los trámites Renovación y Duplicado están suspendidos hasta el 30/11/2026."},
    {"id": "c4", "description": "dos montos en rojo, sin leyenda (aumentaron)",
     "visual_meaning": True, "rows": _rows(cells={(0, 1): "red", (3, 1): "red"})},
    {"id": "c5", "description": "última fila en negrita", "visual_meaning": False,
     "rows": _rows({4: "bold"})},
    {"id": "c6", "description": "filas alternadas en gris claro", "visual_meaning": False,
     "rows": _rows({1: "zebra", 3: "zebra"})},
    {"id": "c7", "description": "una celda de turno con fondo oscuro y texto rojo, sin leyenda",
     "visual_meaning": True, "rows": _rows(cells={(2, 2): "alert"})},
    {"id": "c8", "description": "montos en rojo y una columna que dice que aumentaron",
     "visual_meaning": False,
     "rows": _rows(cells={(0, 1): "red", (3, 1): "red"},
                   extra=["Cambio", "Aumentó en octubre", "", "", "Aumentó en octubre", ""])},
]
for c in CASES:
    c.setdefault("title", TITLE)
    c.setdefault("intro", INTRO)


def make_pdf(case: dict, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{case['id']}.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 70), case["title"], fontsize=16, fontname="hebo")
    page.insert_text((50, 100), case["intro"], fontsize=10, fontname="helv")
    n_cols = len(case["rows"][0]["cells"])
    width, height, x0, y = 495 / n_cols, 24, 50, 125
    for row in case["rows"]:
        for ci, cell in enumerate(row["cells"]):
            bg, fg, bold = STYLES[row.get("cell_styles", {}).get(ci, row["style"])]
            rect = pymupdf.Rect(x0 + ci * width, y, x0 + (ci + 1) * width, y + height)
            if bg:
                page.draw_rect(rect, fill=bg, color=None)
            if cell:
                page.insert_text((rect.x0 + 6, rect.y0 + 16), cell, fontsize=9.5, color=fg,
                                 fontname="hebo" if bold else "helv")
        y += height
    if case.get("legend"):
        page.insert_text((50, y + 25), case["legend"], fontsize=9, fontname="helv")
    doc.save(path)
    return path
