"""What the app does, without the web layer: parse, evaluate, review, index, answer.

Heavy models (evaluator, embeddings, re-ranker) load lazily, once, and can be replaced in tests
through `Services(evaluator=..., rag_factory=...)`.
"""

import difflib
import json
import re
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from app.store import Store
from llm_lab.blocks import Block, Document
from llm_lab.chunking import block_text
from llm_lab.corpus import drop_repeated, merge_broken_paragraphs
from llm_lab.models import DEFAULT_CHAIN, complete
from llm_lab.review import new_numbers, rewrite_block
from llm_lab.rules import Rule, load_rules

ROOT = Path(__file__).resolve().parents[1]
PARSE_SCRIPT = ROOT / "labs" / "11-parseo"
EVALUATOR_MODEL = "mlx-community/Qwen3.5-4B-4bit"  # lab 13

# Which blocks each block-scoped rule looks at. Cheap filters: without them a 100-block
# document needs ~800 forward passes. R1 (color) needs style information the parser does not
# keep yet (SDD risk 3); R11 and R12 are left out of this first version.
MONEY = re.compile(r"\$\s?\d|\d\s?\$|\bpesos\b|\bUT\b")
DATES = re.compile(r"\d{1,2}/\d{1,2}(/\d{2,4})?|\b\d{1,2}°? de \w+|\b(próximo|corriente|en curso)\b",
                   re.IGNORECASE)
LINKS = re.compile(r"\b(aquí|acá|click|clic|link)\b|https?://", re.IGNORECASE)
INSTRUCTIONS = re.compile(r"\b(deber[áa]n?|deberá ser|se deber[áa]|ingres|present|complet|"
                          r"adjunt|solicit)\w*", re.IGNORECASE)
APPLIES = {
    "r2-tablas": lambda b, t: b.kind == "table",
    "r3-enlaces": lambda b, t: bool(b.links) or bool(LINKS.search(t)),
    "r4-titulos": lambda b, t: b.kind == "heading",
    "r6-moneda": lambda b, t: b.kind != "heading" and bool(MONEY.search(t)),
    "r7-fechas": lambda b, t: b.kind != "heading" and bool(DATES.search(t)),
    "r8-vigencia": lambda b, t: b.kind != "heading" and bool(MONEY.search(t)),
    "r13-concision": lambda b, t: b.kind in ("paragraph", "list_item"),
    "r14-voz-activa": lambda b, t: b.kind in ("paragraph", "list_item")
    and bool(INSTRUCTIONS.search(t)),
}
DOCUMENT_RULES = ["r9-emisor-fecha", "r10-proposito"]


def concision(text: str) -> str:
    """R13, deterministic: 30 words per sentence, 150 per paragraph (SDD §12)."""
    words = len(text.split())
    longest = max((len(s.split()) for s in re.split(r"(?<=[.!?;:])\s+", text)), default=0)
    if words > 150:
        return "red"
    return "yellow" if longest > 30 else "green"


@dataclass
class Problem:
    block: int
    rule: str
    level: str
    blocking: bool


@dataclass
class Services:
    store: Store
    evaluator: object = None
    rag_factory: object = None
    rules: dict[str, Rule] = field(default_factory=load_rules)
    _rag: object = None

    # ---------------------------------------------------------------- models

    def get_evaluator(self):
        if self.evaluator is None:
            from llm_lab.evaluator import LogprobsEvaluator
            # one option order: half the cost; lab 13 measured two orders 4 points better,
            # worth it offline, too slow for a person waiting on the screen
            self.evaluator = LogprobsEvaluator(EVALUATOR_MODEL, permutations=1)
        return self.evaluator

    def get_rag(self):
        if self._rag is None:
            docs = [self.store.document(d, v) for d, v in self.store.indexed()]
            if self.rag_factory:
                self._rag = self.rag_factory(docs)
            else:
                from llm_lab.rag import RAG
                self._rag = RAG.from_corpus(docs) if docs else None
        return self._rag

    # ---------------------------------------------------------------- ingest

    def ingest(self, filename: str, content: bytes, tmp: Path) -> str:
        """Parse an uploaded file in a separate process (lab 11: Docling and PyMuPDF must not
        share one) and store version 1."""
        stem = re.sub(r"[^a-z0-9-]+", "-", Path(filename).stem.lower()).strip("-")
        suffix = Path(filename).suffix.lower()
        tmp.mkdir(parents=True, exist_ok=True)
        path = tmp / f"{stem}{suffix}"
        path.write_bytes(content)
        out = tmp / f"{stem}.json"
        code = (
            "import sys, json, importlib; from pathlib import Path; "
            f"sys.path.insert(0, {str(PARSE_SCRIPT)!r}); "
            "from llm_lab.blocks import Document; "
            f"name = 'docling_parser' if {suffix!r} == '.pdf' else 'manual_parser'; "
            "parse = importlib.import_module(name).parse; "
            f"blocks, pages = parse(Path({str(path)!r}), Path({str(tmp)!r})); "
            f"Document({stem!r}, {suffix.lstrip('.')!r}, name, pages, 0.0, blocks)"
            f".save(Path({str(out)!r}))"
        )
        subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
        doc = merge_broken_paragraphs(drop_repeated(Document.load(out)))
        doc.meta = {"title": Path(filename).stem, "jurisdiction": None, "agency": None}
        self.store.add_document(doc)
        return doc.id

    # ---------------------------------------------------------------- quality gate

    def checks(self, doc: Document) -> list[tuple[int | None, str]]:
        """(block index or None for document rules, rule id) pairs to evaluate."""
        pairs = []
        for i, b in enumerate(doc.blocks):
            text = block_text(b)
            for rid, applies in APPLIES.items():
                if applies(b, text):
                    pairs.append((i, rid))
        return pairs + [(None, rid) for rid in DOCUMENT_RULES]

    def evaluate(self, doc_id: str) -> Iterator[dict]:
        """Yields progress events; every verdict is stored as soon as it is known."""
        from llm_lab.evaluator import build_state
        version = self.store.latest_version(doc_id)
        doc = self.store.document(doc_id, version)
        done = {(e["block"], e["rule"]) for e in self.store.evaluations(doc_id, version)}
        pairs = [p for p in self.checks(doc) if (p[0] if p[0] is not None else -1, p[1])
                 not in done]
        total = len(pairs)
        for n, (i, rid) in enumerate(pairs, start=1):
            if rid == "r13-concision":
                level, probs = concision(doc.blocks[i].text), {}
            else:
                state = build_state(doc, i) if i is not None else self.document_state(doc)
                v = self.get_evaluator().evaluate(state, self.rules[rid])
                level, probs = v.level, v.probs
            self.store.save_evaluation(doc_id, version, i if i is not None else -1, rid, level,
                                       probs)
            yield {"done": n, "total": total, "block": i, "rule": rid, "level": level}
        self.store.set_status(doc_id, "evaluado")

    @staticmethod
    def document_state(doc: Document) -> str:
        head = "\n".join(block_text(b) for b in doc.blocks[:12])[:1500]
        return (f"Documento: {doc.meta.get('title', doc.id)}\n\n[BLOQUE A EVALUAR: comienzo "
                f"del documento]\n{head}")

    def problems(self, doc_id: str) -> list[Problem]:
        version = self.store.latest_version(doc_id)
        out = []
        for e in self.store.evaluations(doc_id, version):
            if e["level"] in ("red", "yellow"):
                rule = self.rules[e["rule"]]
                out.append(Problem(e["block"], e["rule"], e["level"],
                                   rule.blocking and e["level"] == "red"))
        # reds first (blocking before the rest), then yellows, in document order
        return sorted(out, key=lambda p: (p.level != "red", not p.blocking, p.block))

    def can_index(self, doc_id: str) -> bool:
        evaluated = self.store.evaluations(doc_id, self.store.latest_version(doc_id))
        return bool(evaluated) and not any(p.blocking for p in self.problems(doc_id))

    # ---------------------------------------------------------------- guided review

    def propose(self, doc_id: str, block: int, rule_id: str, answer: str) -> int:
        from llm_lab.evaluator import build_state
        doc = self.store.document(doc_id)
        rule = self.rules[rule_id]
        if block < 0:
            # Document rule (who publishes it, what it is for): the fix is a short sentence
            # added at the top, written only from the person's answer.
            original = ""
            rewrite = complete([{"role": "user", "content": (
                f"Escribí una o dos oraciones para agregar al comienzo del documento "
                f"«{doc.meta.get('title', doc.id)}» de modo que cumpla: {rule.levels.green} "
                f"Usá solo esta información y no agregues nada más: {answer}\n"
                "Devolvé solo las oraciones.")}], DEFAULT_CHAIN).text.strip()
            fixed = Document(doc.id, doc.format, doc.parser, doc.pages, doc.seconds,
                             [Block("paragraph", rewrite), *doc.blocks], doc.meta)
            level = self.get_evaluator().evaluate(self.document_state(fixed), rule).level
            invented = sorted(new_numbers(original, answer, rewrite))
            return self.store.save_review(doc_id=doc_id, block=block, rule=rule_id,
                                          answer=answer, before=original, after=rewrite,
                                          level_after=level, invented=json.dumps(invented))
        original = block_text(doc.blocks[block])
        state = build_state(doc, block)
        rewrite = rewrite_block(state, original, rule, answer, DEFAULT_CHAIN)
        invented = sorted(new_numbers(original, answer, rewrite))
        level = self.get_evaluator().evaluate(state.replace(original, rewrite), rule).level
        return self.store.save_review(doc_id=doc_id, block=block, rule=rule_id, answer=answer,
                                      before=original, after=rewrite, level_after=level,
                                      invented=json.dumps(invented))

    def accept(self, review_id: int) -> None:
        r = self.store.review(review_id)
        doc = self.store.document(r["doc_id"])
        old_version = self.store.latest_version(r["doc_id"])
        if r["block"] < 0:
            doc.blocks.insert(0, Block("paragraph", r["after"]))
            version = self.store.save_version(doc, f"revisión {r['rule']}: encabezado")
            self.store.copy_evaluations(r["doc_id"], old_version, version, skip_block=-2,
                                        shift=1)
            self.store.save_evaluation(r["doc_id"], version, -1, r["rule"], r["level_after"],
                                       {})
            self.store.accept_review(review_id)
            return
        old = doc.blocks[r["block"]]
        kind = "table" if r["after"].lstrip().startswith("|") and old.kind == "table" else (
            old.kind if old.kind != "table" else "paragraph")
        new = Block(kind, "" if kind == "table" else r["after"], level=old.level,
                    page=old.page, links=old.links, path=old.path,
                    rows=_markdown_rows(r["after"]) if kind == "table" else [])
        doc.blocks[r["block"]] = new
        version = self.store.save_version(doc, f"revisión {r['rule']} bloque {r['block']}")
        self.store.copy_evaluations(r["doc_id"], old_version, version, r["block"])
        self.store.save_evaluation(r["doc_id"], version, r["block"], r["rule"],
                                   r["level_after"], {})
        self.store.accept_review(review_id)

    # ---------------------------------------------------------------- index and chat

    def index(self, doc_id: str) -> None:
        if not self.can_index(doc_id):
            raise ValueError("El documento tiene rojos bloqueantes: no se indexa.")
        self.store.mark_indexed(doc_id, self.store.latest_version(doc_id),
                                reviewed=bool(self.store.history(doc_id)))
        self._rag = None  # rebuilt on the next question (embeddings are cached)

    def ask(self, question: str) -> Iterator[dict]:
        from llm_lab.models import stream
        from llm_lab.rag import NO_INFO, SYSTEM
        yield {"stage": "buscando"}
        rag = self.get_rag()
        if rag is None:
            yield {"token": "Todavía no hay documentos indexados."}
            yield {"done": True, "sources": []}
            return
        hits = rag.retrieve(question, k=5)
        yield {"stage": "respondiendo"}
        context = "\n\n".join(f"[{n}] ({h.chunk.meta.get('title') or h.chunk.doc_id})\n"
                              f"{h.chunk.text}" for n, h in enumerate(hits, start=1))
        text = ""
        for token in stream([{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": f"Fragmentos:\n\n{context}\n\n"
                                                         f"Pregunta: {question}"}],
                            DEFAULT_CHAIN):
            text += token
            yield {"token": token}
        cited = sorted({int(n) for n in re.findall(r"[\[【](\d+)[\]】]", text)
                        if 0 < int(n) <= len(hits)})
        yield {"done": True, "abstained": NO_INFO.lower()[:25] in text.lower(),
               "sources": [{"n": n, "doc": hits[n - 1].chunk.doc_id,
                            "path": " > ".join(hits[n - 1].chunk.path),
                            "text": hits[n - 1].chunk.text[:400]} for n in cited]}


def _markdown_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and not re.fullmatch(r"\|[\s\-:|]+\|", line):
            rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows


def word_diff(before: str, after: str) -> str:
    """HTML with <del> and <ins> at word level, for the before/after view."""
    import html
    a, b = before.split(), after.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b).get_opcodes():
        if op == "equal":
            out.append(html.escape(" ".join(a[i1:i2])))
        if op in ("delete", "replace"):
            out.append(f"<del>{html.escape(' '.join(a[i1:i2]))}</del>")
        if op in ("insert", "replace"):
            out.append(f"<ins>{html.escape(' '.join(b[j1:j2]))}</ins>")
    return " ".join(out)
