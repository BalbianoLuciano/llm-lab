"""SQLite persistence for the app: documents, versions, evaluations, reviews and the index.

Every correction creates a new version of the document, so the original and the history of
what changed (which rule, what the person answered) are never lost (SDD §5.4).
"""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from llm_lab.blocks import Block, Document, Link

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY, title TEXT, format TEXT, created TEXT,
    status TEXT DEFAULT 'nuevo'  -- nuevo | evaluado | aprobado | indexado
);
CREATE TABLE IF NOT EXISTS versions (
    doc_id TEXT, version INTEGER, document TEXT, created TEXT, note TEXT,
    PRIMARY KEY (doc_id, version)
);
CREATE TABLE IF NOT EXISTS evaluations (
    doc_id TEXT, version INTEGER, block INTEGER, rule TEXT, level TEXT, probs TEXT,
    PRIMARY KEY (doc_id, version, block, rule)
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT, block INTEGER, rule TEXT,
    answer TEXT, before TEXT, after TEXT, level_after TEXT, invented TEXT,
    accepted INTEGER, created TEXT
);
CREATE TABLE IF NOT EXISTS indexed (
    doc_id TEXT PRIMARY KEY, version INTEGER, indexed_at TEXT, reviewed INTEGER
);
"""


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    # ---------------------------------------------------------------- documents

    def add_document(self, doc: Document, note: str = "original") -> None:
        with self.conn() as c:
            c.execute("INSERT OR REPLACE INTO documents (id, title, format, created, status) "
                      "VALUES (?, ?, ?, ?, 'nuevo')",
                      (doc.id, doc.meta.get("title", doc.id), doc.format, _now()))
        self.save_version(doc, note)

    def save_version(self, doc: Document, note: str) -> int:
        version = self.latest_version(doc.id) + 1
        with self.conn() as c:
            c.execute("INSERT INTO versions VALUES (?, ?, ?, ?, ?)",
                      (doc.id, version, json.dumps(asdict(doc), ensure_ascii=False), _now(),
                       note))
        return version

    def latest_version(self, doc_id: str) -> int:
        with self.conn() as c:
            row = c.execute("SELECT MAX(version) v FROM versions WHERE doc_id=?",
                            (doc_id,)).fetchone()
        return row["v"] or 0

    def document(self, doc_id: str, version: int | None = None) -> Document:
        version = version or self.latest_version(doc_id)
        with self.conn() as c:
            row = c.execute("SELECT document FROM versions WHERE doc_id=? AND version=?",
                            (doc_id, version)).fetchone()
        d = json.loads(row["document"])
        blocks = [Block(**{**b, "links": [Link(**x) for x in b["links"]]})
                  for b in d.pop("blocks")]
        return Document(**d, blocks=blocks)

    def documents(self) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT d.*, (SELECT MAX(version) FROM versions v WHERE v.doc_id=d.id) version,"
                " i.reviewed FROM documents d LEFT JOIN indexed i ON i.doc_id=d.id "
                "ORDER BY created DESC")]

    def set_status(self, doc_id: str, status: str) -> None:
        with self.conn() as c:
            c.execute("UPDATE documents SET status=? WHERE id=?", (status, doc_id))

    # ---------------------------------------------------------------- evaluations

    def save_evaluation(self, doc_id: str, version: int, block: int, rule: str, level: str,
                        probs: dict) -> None:
        with self.conn() as c:
            c.execute("INSERT OR REPLACE INTO evaluations VALUES (?, ?, ?, ?, ?, ?)",
                      (doc_id, version, block, rule, level, json.dumps(probs)))

    def evaluations(self, doc_id: str, version: int) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM evaluations WHERE doc_id=? AND version=? ORDER BY block",
                (doc_id, version))]

    def copy_evaluations(self, doc_id: str, src: int, dst: int, skip_block: int,
                         shift: int = 0) -> None:
        """A correction changes one block: the other verdicts carry over (cache, SDD §5.3).
        `shift` moves block indices (a block inserted at the top); document rules (-1) stay."""
        with self.conn() as c:
            c.execute("INSERT OR REPLACE INTO evaluations SELECT doc_id, ?, "
                      "CASE WHEN block >= 0 THEN block + ? ELSE block END, rule, level, probs "
                      "FROM evaluations WHERE doc_id=? AND version=? AND block!=?",
                      (dst, shift, doc_id, src, skip_block))

    # ---------------------------------------------------------------- reviews and index

    def save_review(self, **row) -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO reviews (doc_id, block, rule, answer, before, after, level_after, "
                "invented, accepted, created) VALUES (:doc_id, :block, :rule, :answer, :before, "
                ":after, :level_after, :invented, 0, :created)", {**row, "created": _now()})
            return cur.lastrowid

    def review(self, review_id: int) -> dict:
        with self.conn() as c:
            return dict(c.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone())

    def accept_review(self, review_id: int) -> None:
        with self.conn() as c:
            c.execute("UPDATE reviews SET accepted=1 WHERE id=?", (review_id,))

    def history(self, doc_id: str) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM reviews WHERE doc_id=? AND accepted=1 ORDER BY id", (doc_id,))]

    def mark_indexed(self, doc_id: str, version: int, reviewed: bool) -> None:
        with self.conn() as c:
            c.execute("INSERT OR REPLACE INTO indexed VALUES (?, ?, ?, ?)",
                      (doc_id, version, _now(), int(reviewed)))
        self.set_status(doc_id, "indexado")

    def indexed(self) -> list[tuple[str, int]]:
        with self.conn() as c:
            return [(r["doc_id"], r["version"]) for r in c.execute("SELECT * FROM indexed")]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
