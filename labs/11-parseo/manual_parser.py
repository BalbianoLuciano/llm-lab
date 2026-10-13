"""Hand-written parser: PDF with PyMuPDF, HTML with BeautifulSoup, DOC/DOCX via textutil → HTML.

The point is to see how much can be recovered with simple heuristics before reaching for a
library. Every rule is visible here, to understand later what Docling does differently.
"""

import re
import subprocess
from collections import Counter
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from html_main import main_content

from llm_lab.blocks import Block, Link, assign_paths

BULLET = re.compile(r"^\s*([•●○■□▪◦\-–—*➢✓✔►]|\d{1,2}[.)]|[a-zA-Z][.)])\s+")
BOLD = 16  # "bold" bit in PyMuPDF span flags


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_heading(text: str) -> bool:
    """Short and not ending like a sentence. A trailing colon is allowed ("CONSIDERANDO:")."""
    return len(text.split()) <= 15 and not text.endswith((".", ",", ";"))


# ---------------------------------------------------------------- PDF


def _headers_and_footers(doc: pymupdf.Document) -> set[str]:
    """Lines repeated at the top or bottom edge of many pages."""
    if len(doc) < 3:
        return set()
    counts: Counter[str] = Counter()
    for page in doc:
        height = page.rect.height
        seen = set()
        for b in page.get_text("blocks"):
            if b[1] < height * 0.1 or b[3] > height * 0.9:
                seen.add(re.sub(r"\d+", "#", clean(b[4])))
        counts.update(seen)
    return {t for t, n in counts.items() if n >= len(doc) / 2}


def parse_pdf(path: Path) -> tuple[list[Block], int]:
    doc = pymupdf.open(path)
    repeated = _headers_and_footers(doc)

    # Body font size: the one carrying the most characters in the whole document
    sizes: Counter[float] = Counter()
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                for s in line["spans"]:
                    sizes[round(s["size"])] += len(s["text"].strip())
    body = sizes.most_common(1)[0][0] if sizes else 11

    raw = []  # (kind, text, size, page, links, rows, y)
    for n, page in enumerate(doc, start=1):
        tables = page.find_tables().tables
        zones = [pymupdf.Rect(t.bbox) for t in tables]
        for t in tables:
            rows = [[clean(c or "") for c in r] for r in t.extract()]
            rows = [r for r in rows if any(r)]
            markers = [bool(BULLET.match(r[0] + " ")) and len(r[0]) <= 3 for r in rows]
            if rows and markers[0] and all(m or not r[0] for m, r in zip(markers, rows)):
                # find_tables sees a bulleted list as a table (bullet | text); rows with an
                # empty first cell continue the previous item
                items: list[str] = []
                for m, cells in zip(markers, rows):
                    text = clean(" ".join(c for c in cells[1:] if c))
                    if m:
                        items.append(f"{cells[0]} {text}")
                    else:
                        items[-1] += " " + text
                for i, text in enumerate(items):
                    raw.append(("list_item", text, 0, n, [], [], t.bbox[1] + i / 100))
            elif len(rows) >= 2:
                raw.append(("table", "", 0, n, [], rows, t.bbox[1]))

        uris = [(pymupdf.Rect(e["from"]), e["uri"]) for e in page.get_links() if e.get("uri")]
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0 or any(z.intersects(pymupdf.Rect(b["bbox"])) for z in zones):
                continue
            # A PyMuPDF block can mix a heading and a paragraph: split it at every line that
            # starts with a bullet or changes font size or boldness.
            groups: list[list[dict]] = []
            bullet = False  # the previous line was a lone bullet glyph
            for line in b["lines"]:
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans)
                if BULLET.match(text.strip() + " ") and len(text.strip()) <= 3:
                    bullet = True  # some PDFs draw the bullet as its own line, in another font
                    continue
                if bullet:
                    text, bullet = "• " + text, False
                style = (round(max(s["size"] for s in spans)),
                         all(s["flags"] & BOLD for s in spans))
                entry = {"text": text, "style": style, "bbox": pymupdf.Rect(line["bbox"])}
                if not groups or BULLET.match(text) or groups[-1][-1]["style"] != style:
                    groups.append([entry])
                else:
                    groups[-1].append(entry)
            for g in groups:
                text = clean(" ".join(x["text"] for x in g))
                if len(text) < 2 or re.sub(r"\d+", "#", text) in repeated:
                    continue
                size, bold = g[0]["style"]
                rect = pymupdf.Rect(g[0]["bbox"])
                for x in g[1:]:
                    rect |= x["bbox"]
                links = [Link(clean(page.get_textbox(r)), u) for r, u in uris
                         if r.intersects(rect)]
                if BULLET.match(text):
                    kind = "list_item"
                elif _looks_like_heading(text) and (size >= body + 2 or (bold and size >= body)):
                    kind = "heading"
                else:
                    kind = "paragraph"
                raw.append((kind, text, size, n, links, [], rect.y0))

    # Reading order within each page: top to bottom (single column)
    raw.sort(key=lambda c: (c[3], c[6]))

    # Heading level: the largest size is level 1, the next one level 2, etc. (max. 3)
    heading_sizes = sorted({c[2] for c in raw if c[0] == "heading"}, reverse=True)
    blocks: list[Block] = []
    for kind, text, size, n, links, rows, _ in raw:
        if kind == "heading":
            level = min(heading_sizes.index(size) + 1, 3)
            blocks.append(Block("heading", text, level=level, page=n))
        elif kind == "table":
            blocks.append(Block("table", "", page=n, rows=rows))
        elif kind == "paragraph" and blocks and blocks[-1].kind == "paragraph" \
                and blocks[-1].page == n and not blocks[-1].text.endswith((".", ":")):
            # Paragraph split across two blocks (common with column breaks)
            blocks[-1].text += " " + text
            blocks[-1].links += links
        else:
            blocks.append(Block(kind, text, page=n, links=links))
    return assign_paths(blocks), len(doc)


# ---------------------------------------------------------------- HTML


INLINE = ("b", "strong", "span", "a", "em", "i", "u", "small", "sup", "font")


def _links(node: Tag) -> list[Link]:
    return [Link(clean(a.get_text()), a["href"]) for a in node.find_all("a", href=True)
            if a["href"].startswith(("http", "/", "mailto:"))]


def _walk(node: Tag, blocks: list[Block]) -> None:
    loose: list[str] = []  # text hanging directly from a div, with no <p>

    def flush():
        text = clean(" ".join(loose))
        if len(text) > 1:
            blocks.append(Block("paragraph", text))
        loose.clear()

    for child in node.children:
        if isinstance(child, Comment):
            continue  # HTML comments are NavigableStrings too (lab 02 finding)
        if isinstance(child, NavigableString):
            loose.append(str(child))
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name
        if name in INLINE:
            loose.append(child.get_text(" "))
            continue
        flush()
        if re.fullmatch(r"h[1-6]", name):
            text = clean(child.get_text(" "))
            if text:
                blocks.append(Block("heading", text, level=int(name[1])))
        elif name == "p":
            text = clean(child.get_text(" "))
            bold = clean(" ".join(b.get_text(" ") for b in child.find_all(["b", "strong"])))
            if text and bold == text and _looks_like_heading(text):
                # A paragraph that is all bold works as a heading (Word documents, CMS pages)
                blocks.append(Block("heading", text, level=4))
            elif text:
                blocks.append(Block("paragraph", text, links=_links(child)))
        elif name in ("ul", "ol"):
            for li in child.find_all("li", recursive=False):
                nested = [x.extract() for x in li.find_all(["ul", "ol"], recursive=False)]
                text = clean(li.get_text(" "))
                if text:
                    blocks.append(Block("list_item", text, links=_links(li)))
                for sub in nested:
                    _walk(BeautifulSoup(f"<div>{sub}</div>", "html.parser").div, blocks)
        elif name == "table":
            rows = [[clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
                    for tr in child.find_all("tr")]
            rows = [r for r in rows if any(r)]
            if len(rows) >= 2 and max(len(r) for r in rows) >= 2:
                blocks.append(Block("table", "", rows=rows, links=_links(child)))
            else:  # single-cell layout tables: read what's inside
                for cell in child.find_all(["td", "th"]):
                    _walk(cell, blocks)
        elif name == "br":
            loose.append("\n")
        else:
            _walk(child, blocks)
    flush()


def parse_html(path: Path) -> tuple[list[Block], None]:
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    blocks: list[Block] = []
    _walk(main_content(soup), blocks)
    return assign_paths(blocks), None


# ---------------------------------------------------------------- DOC / DOCX


def to_html_with_textutil(path: Path, dest: Path) -> Path:
    """textutil ships with macOS and converts .doc/.docx/.rtf to HTML."""
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"{path.stem}.html"
    if not out.exists():
        subprocess.run(["textutil", "-convert", "html", str(path), "-output", str(out)],
                       check=True, capture_output=True)
    return out


def parse(path: Path, tmp: Path) -> tuple[list[Block], int | None]:
    fmt = path.suffix.lstrip(".")
    if fmt == "pdf":
        return parse_pdf(path)
    if fmt == "html":
        return parse_html(path)
    if fmt in ("doc", "docx"):
        return parse_html(to_html_with_textutil(path, tmp))
    raise ValueError(f"Unsupported format: {fmt}")
