"""The parsed corpus, ready to use: the parser that won lab 11 for each format, cleaned.

    from llm_lab.corpus import load_corpus
    for doc in load_corpus():
        print(doc.id, doc.meta["title"], len(doc.blocks))

Lab 11 conclusion: Docling for PDF, the hand-written parser for HTML and Word, and in every
case drop the page banners that repeat on many pages (Docling keeps them as headings).
"""

import csv
import re
import unicodedata
from collections import Counter
from functools import cache
from pathlib import Path

from llm_lab.blocks import Block, Document

ROOT = Path(__file__).resolve().parents[2]
BLOCKS = ROOT / "data" / "processed" / "blocks"
URLS = ROOT / "corpus" / "urls.tsv"
PARSER_BY_FORMAT = {"pdf": "docling", "html": "manual", "doc": "manual", "docx": "manual"}


def norm(text: str) -> str:
    """Lowercase, no accents, alphanumerics only. Used for lenient matching across labs."""
    no_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(c for c in no_accents.lower() if c.isalnum())


def drop_repeated(doc: Document) -> Document:
    """Remove blocks whose text shows up on at least half the pages (banners, footers).

    The first occurrence is kept: on a cover page the banner is usually the real title.
    """
    if not doc.pages or doc.pages < 3:
        return doc
    pages_by_text: dict[str, set[int]] = {}
    for b in doc.blocks:
        if b.kind != "table" and b.page:
            pages_by_text.setdefault(re.sub(r"\d+", "#", norm(b.text)), set()).add(b.page)
    repeated = {t for t, pages in pages_by_text.items() if len(pages) >= doc.pages / 2}
    seen: Counter[str] = Counter()
    kept: list[Block] = []
    for b in doc.blocks:
        key = re.sub(r"\d+", "#", norm(b.text))
        if b.kind != "table" and key in repeated:
            seen[key] += 1
            if seen[key] > 1:
                continue
        kept.append(b)
    doc.blocks = kept
    return doc


def merge_broken_paragraphs(doc: Document) -> Document:
    """Join a paragraph that a PDF parser split mid-sentence (one block per printed line).

    Conservative on purpose: only when the first block doesn't close a sentence and the next
    one starts in lowercase. Found in lab 02: a fee and its effective date ended up in
    different blocks, so no per-block rule could see both.
    """
    merged: list[Block] = []
    for b in doc.blocks:
        prev = merged[-1] if merged else None
        if (prev and prev.kind == b.kind == "paragraph" and prev.page == b.page
                and prev.path == b.path and not re.search(r"[.:;!?]\s*$", prev.text)
                and re.match(r"[a-záéíóúñü]", b.text)):
            prev.text = f"{prev.text} {b.text}"
            prev.links += b.links
        else:
            merged.append(b)
    doc.blocks = merged
    return doc


@cache
def metadata() -> dict[str, dict]:
    with URLS.open(newline="") as f:
        return {row["id"]: row for row in csv.DictReader(f, delimiter="\t")}


def load_document(doc_id: str) -> Document:
    meta = metadata()[doc_id]
    doc = Document.load(BLOCKS / PARSER_BY_FORMAT[meta["format"]] / f"{doc_id}.json")
    doc = merge_broken_paragraphs(drop_repeated(doc))
    doc.meta = meta
    return doc


def load_corpus() -> list[Document]:
    return [load_document(doc_id) for doc_id in metadata()]
