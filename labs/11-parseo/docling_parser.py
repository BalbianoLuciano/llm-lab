"""Docling parser: layout model for PDF, native converters for HTML and DOCX.

Docling can't read .doc (Word 97), so those are converted to .docx with textutil first. HTML
goes through html_main first, same as the manual parser.
"""

import re
import subprocess
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import HeadingHierarchyOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import (
    ContentLayer,
    DocItemLabel,
    InlineGroup,
    ListItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)
from html_main import clean_html

from llm_lab.blocks import Block, Link, assign_paths

_converter: DocumentConverter | None = None


def converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        options = PdfPipelineOptions(
            do_ocr=False,  # the corpus has embedded text; the only scanned PDF was left out
            do_table_structure=True,
            # Off by default: without it every PDF heading comes out as level 1
            heading_hierarchy_options=HeadingHierarchyOptions(enabled=True),
        )
        _converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    return _converter


def _page(item) -> int | None:
    return item.prov[0].page_no if getattr(item, "prov", None) else None


def _links(item) -> list[Link]:
    url = getattr(item, "hyperlink", None)
    return [Link(item.text, str(url))] if url else []


def to_docx_with_textutil(path: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"{path.stem}.docx"
    if not out.exists():
        subprocess.run(["textutil", "-convert", "docx", str(path), "-output", str(out)],
                       check=True, capture_output=True)
    return out


def _inline_text(group, doc) -> tuple[str, list[Link]]:
    """Docling splits inline markup (bold, links, commas) into one TextItem each: join them."""
    parts, links = [], []
    for ref in group.children:
        child = ref.resolve(doc)
        if isinstance(child, InlineGroup):
            text, sub = _inline_text(child, doc)
            parts.append(text)
            links += sub
        elif isinstance(child, TextItem):
            parts.append(child.text)
            links += _links(child)
    text = re.sub(r"\s+([,.;:)])", r"\1", " ".join(p.strip() for p in parts if p.strip()))
    return text.replace("( ", "("), links


def _walk(node, doc, blocks: list[Block], owner: Block | None = None) -> None:
    """Depth-first over the document tree. `owner` is the list item whose content we are in."""
    for ref in node.children:
        item = ref.resolve(doc)
        if getattr(item, "content_layer", None) == ContentLayer.FURNITURE:
            continue  # page headers and footers
        if isinstance(item, InlineGroup):
            text, links = _inline_text(item, doc)
            if owner is not None:
                owner.text = f"{owner.text} {text}".strip()
                owner.links += links
            elif text:
                blocks.append(Block("paragraph", text, page=_page(item), links=links))
        elif isinstance(item, TableItem):
            rows = [[c.text.strip() for c in row] for row in item.data.grid]
            rows = [r for r in rows if any(r)]
            if rows:
                blocks.append(Block("table", "", page=_page(item), rows=rows))
        elif isinstance(item, (TitleItem, SectionHeaderItem)):
            level = 1 if isinstance(item, TitleItem) else item.level
            if item.text.strip():
                blocks.append(Block("heading", item.text.strip(), level=level,
                                    page=_page(item)))
            _walk(item, doc, blocks)  # in HTML, a section's content hangs from its heading
        elif isinstance(item, ListItem):
            block = Block("list_item", item.text.strip(), page=_page(item), links=_links(item))
            blocks.append(block)
            _walk(item, doc, blocks, owner=block)
        elif isinstance(item, TextItem):
            if item.label in (DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER,
                              DocItemLabel.CAPTION):
                continue
            if owner is not None:
                owner.text = f"{owner.text} {item.text.strip()}".strip()
                owner.links += _links(item)
            elif item.text.strip():
                blocks.append(Block("paragraph", item.text.strip(), page=_page(item),
                                    links=_links(item)))
        else:  # groups (lists, sections), pictures: go inside
            _walk(item, doc, blocks)


def parse(path: Path, tmp: Path) -> tuple[list[Block], int | None]:
    if path.suffix == ".doc":
        source = to_docx_with_textutil(path, tmp)
    elif path.suffix == ".html":
        tmp.mkdir(parents=True, exist_ok=True)
        source = tmp / f"{path.stem}.main.html"
        source.write_text(clean_html(path.read_bytes()))
    else:
        source = path
    doc = converter().convert(source).document

    blocks: list[Block] = []
    _walk(doc.body, doc, blocks)
    blocks = [b for b in blocks if b.kind != "list_item" or b.text]
    pages = len(doc.pages) if doc.pages else None
    return assign_paths(blocks), pages
