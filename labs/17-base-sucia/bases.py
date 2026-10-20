"""The four indexes compared in lab 17, from a clean pipeline down to a naive one.

    from bases import build
    chunks = build("sucia")

- limpia: the production pipeline (labs 03, 11): best parser per format, repeated banners
  dropped, broken paragraphs joined, structural chunks of 1000 characters with the heading path.
- sin_ruta: the same chunks without the title and heading path in front.
- fijo: the same clean blocks, but cut every 1000 characters with 200 of overlap.
- sucia: what a first version usually does. Plain text straight from the file (PyMuPDF
  get_text, BeautifulSoup get_text on the whole page, textutil to txt), no cleaning, fixed
  chunks of 1000/200. Tables come out as loose lines; menus and footers stay in.
"""

import re
import subprocess
from functools import cache
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup

from llm_lab.blocks import Block, Document
from llm_lab.chunking import Chunk, by_structure, fixed_size
from llm_lab.corpus import load_corpus, metadata

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "corpus"
TMP = ROOT / "data" / "interim" / "lab17-txt"
BASES = ["limpia", "sin_ruta", "fijo", "sucia"]


def raw_text(doc_id: str, fmt: str) -> str:
    path = RAW / f"{doc_id}.{fmt}"
    if fmt == "pdf":
        with pymupdf.open(path) as pdf:
            text = "\n".join(page.get_text() for page in pdf)
    elif fmt == "html":
        text = BeautifulSoup(path.read_bytes(), "html.parser").get_text("\n")
    else:  # doc, docx
        TMP.mkdir(parents=True, exist_ok=True)
        out = TMP / f"{doc_id}.txt"
        if not out.exists():
            subprocess.run(["textutil", "-convert", "txt", str(path), "-output", str(out)],
                           check=True, capture_output=True)
        text = out.read_text(errors="ignore")
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def naive_document(doc_id: str) -> Document:
    meta = metadata()[doc_id]
    text = raw_text(doc_id, meta["format"])
    return Document(doc_id, meta["format"], "naive", None, 0.0,
                    [Block("paragraph", text)], meta)


@cache
def build(base: str) -> list[Chunk]:
    if base == "sucia":
        return [c for d in metadata() for c in fixed_size(naive_document(d), 1000, 200)]
    docs = load_corpus()
    if base == "limpia":
        return [c for d in docs for c in by_structure(d, 1000)]
    if base == "sin_ruta":
        return [c for d in docs for c in by_structure(d, 1000, with_path=False)]
    if base == "fijo":
        return [c for d in docs for c in fixed_size(d, 1000, 200)]
    raise ValueError(base)


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def is_hit(chunk: Chunk, question: dict) -> bool:
    """Evidence contained in the chunk, ignoring whitespace: the naive text breaks lines anywhere,
    and the same tolerance is applied to every base so none is favoured."""
    return any(chunk.doc_id == e["doc"] and squash(e["text"]) in squash(chunk.text)
               for e in question["evidence"])
