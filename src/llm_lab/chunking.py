"""Split parsed documents into chunks: the unit that gets embedded, retrieved and cited.

Two families, compared in lab 03:
- fixed_size: ignores structure, cuts the plain text every N characters with overlap.
- by_structure: groups consecutive blocks of the same section up to a size limit, never cuts
  a block in half, keeps tables whole (long ones are split by rows repeating the header) and
  prepends the heading path so a chunk can be understood on its own.
"""

from dataclasses import dataclass, field

from llm_lab.blocks import Block, Document


@dataclass
class Chunk:
    id: str
    doc_id: str
    text: str  # what gets embedded and shown to the model
    block_ids: list[int] = field(default_factory=list)
    path: list[str] = field(default_factory=list)
    page: int | None = None
    meta: dict = field(default_factory=dict)  # jurisdiction, agency, title, url


def block_text(b: Block) -> str:
    if b.kind == "table":
        return "\n".join("| " + " | ".join(r) + " |" for r in b.rows)
    if b.kind == "list_item":
        return f"- {b.text}"
    return b.text


def _meta(doc: Document) -> dict:
    return {k: doc.meta.get(k) for k in ("jurisdiction", "agency", "title", "url")}


def fixed_size(doc: Document, size: int, overlap: int) -> list[Chunk]:
    text = "\n".join(block_text(b) for b in doc.blocks)
    chunks, start, n = [], 0, 0
    step = max(1, size - overlap)
    while start < len(text):
        piece = text[start:start + size]
        if piece.strip():
            chunks.append(Chunk(f"{doc.id}#{n}", doc.id, piece, meta=_meta(doc)))
            n += 1
        start += step
    return chunks


def _split_table(b: Block, max_chars: int) -> list[str]:
    """A long table is split by rows; every piece repeats the header row."""
    header, rows = b.rows[0], b.rows[1:]
    pieces, current = [], [header]
    for r in rows:
        candidate = current + [r]
        if len(block_text(Block("table", "", rows=candidate))) > max_chars and len(current) > 1:
            pieces.append(block_text(Block("table", "", rows=current)))
            current = [header, r]
        else:
            current = candidate
    pieces.append(block_text(Block("table", "", rows=current)))
    return pieces


def by_structure(doc: Document, max_chars: int, with_path: bool = True) -> list[Chunk]:
    chunks: list[Chunk] = []
    group: list[tuple[int, Block]] = []

    def prefix(path: list[str]) -> str:
        title = doc.meta.get("title", "")
        return f"{title}\n{' > '.join(path)}\n\n" if with_path and path else (
            f"{title}\n\n" if with_path else "")

    def flush():
        if not group:
            return
        path = group[0][1].path
        body = "\n".join(block_text(b) for _, b in group)
        chunks.append(Chunk(f"{doc.id}#{len(chunks)}", doc.id, prefix(path) + body,
                            [i for i, _ in group], path, group[0][1].page, _meta(doc)))
        group.clear()

    for i, b in enumerate(doc.blocks):
        # A heading opens a new section and travels with what follows it
        if group:
            first = group[0][1]
            section = first.path + [first.text] if first.kind == "heading" else first.path
            size = sum(len(block_text(x)) for _, x in group) + len(block_text(b))
            if b.kind == "heading" or b.path != section or size > max_chars:
                flush()
        if b.kind == "table" and len(block_text(b)) > max_chars and len(b.rows) > 2:
            flush()
            for piece in _split_table(b, max_chars):
                chunks.append(Chunk(f"{doc.id}#{len(chunks)}", doc.id, prefix(b.path) + piece,
                                    [i], b.path, b.page, _meta(doc)))
            continue
        group.append((i, b))
    flush()
    return chunks


def per_block(doc: Document, with_path: bool = True) -> list[Chunk]:
    """One chunk per block (headings excluded): the smallest structural unit."""
    out = []
    for i, b in enumerate(doc.blocks):
        if b.kind == "heading":
            continue
        head = f"{doc.meta.get('title', '')}\n{' > '.join(b.path)}\n\n" if with_path else ""
        out.append(Chunk(f"{doc.id}#{len(out)}", doc.id, head + block_text(b), [i], b.path,
                         b.page, _meta(doc)))
    return out
