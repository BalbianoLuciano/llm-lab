"""Common format for a parsed document: an ordered list of blocks.

Produced by the lab 11 parsers (manual and Docling) and consumed by the quality gate (per-block
rules), chunking (lab 03) and guided review (lab 15).

    doc = Document.load(Path("data/processed/blocks/docling/pba-arba-baja-exencion.json"))
    for b in doc.blocks:
        print(b.kind, b.path, b.text[:60])
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

Kind = Literal["heading", "paragraph", "list_item", "table"]


@dataclass
class Link:
    text: str
    url: str


@dataclass
class Block:
    kind: Kind
    text: str
    level: int = 0  # headings only: 1 is the top level
    page: int | None = None  # None for formats without pages (html, doc)
    rows: list[list[str]] = field(default_factory=list)  # tables only; the first row is the header
    links: list[Link] = field(default_factory=list)
    path: list[str] = field(default_factory=list)  # headings that contain the block


@dataclass
class Document:
    id: str
    format: str
    parser: str
    pages: int | None
    seconds: float
    blocks: list[Block]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1))

    @classmethod
    def load(cls, path: Path) -> "Document":
        d = json.loads(path.read_text())
        blocks = [Block(**{**b, "links": [Link(**x) for x in b["links"]]})
                  for b in d.pop("blocks")]
        return cls(**d, blocks=blocks)

    def text(self) -> str:
        parts = []
        for b in self.blocks:
            parts.append("\n".join(" | ".join(r) for r in b.rows) if b.kind == "table"
                         else b.text)
        return "\n".join(parts)


def assign_paths(blocks: list[Block]) -> list[Block]:
    """Fill in each block's heading path (the stack of open headings)."""
    stack: list[tuple[int, str]] = []
    for b in blocks:
        if b.kind == "heading":
            while stack and stack[-1][0] >= b.level:
                stack.pop()
            b.path = [t for _, t in stack]
            stack.append((b.level, b.text))
        else:
            b.path = [t for _, t in stack]
    return blocks
