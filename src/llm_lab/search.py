"""Search over chunks: BM25 written by hand, dense cosine, and hybrid fusion with RRF.

    bm25 = BM25([c.text for c in chunks])
    ids, scores = bm25.search("costo licencia duplicado", k=10)
    fused = rrf([dense_ids, bm25_ids], k=10)
"""

import math
import re
import unicodedata
from collections import Counter

import numpy as np

# Short Spanish stopword list: function words that carry no meaning for matching
STOPWORDS = frozenset("""
a al algo algun alguna algunas alguno algunos ante antes como con contra cual cuales
cuando de del desde donde dos e el ella ellas ellos en entre era es esa esas ese eso esos
esta estas este esto estos fue ha hay la las le les lo los mas me mi mis mucho muy ni no
nos o os otra otro para pero por porque que quien se sea segun ser si sin sobre su sus
tambien te tiene tengo tu tus un una uno unos y ya yo cuanto cuanta cuantos cuantas puedo
hacer
""".split())  # noqa: SIM905 — easier to read and edit as a block


def tokenize(text: str) -> list[str]:
    no_accents = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    tokens = re.findall(r"[a-z0-9]+", no_accents)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


class BM25:
    """Okapi BM25. k1 saturates term frequency; b normalises by document length."""

    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.lengths = np.array([sum(d.values()) for d in self.docs], dtype=float)
        self.avg_len = self.lengths.mean() if len(self.docs) else 0.0
        df = Counter(term for d in self.docs for term in d)
        n = len(self.docs)
        # +1 inside the log keeps idf positive for very common terms
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.postings: dict[str, list[int]] = {}
        for i, d in enumerate(self.docs):
            for term in d:
                self.postings.setdefault(term, []).append(i)

    def scores(self, query: str) -> np.ndarray:
        out = np.zeros(len(self.docs))
        norm = self.k1 * (1 - self.b + self.b * self.lengths / self.avg_len)
        for term in set(tokenize(query)):
            for i in self.postings.get(term, []):
                tf = self.docs[i][term]
                out[i] += self.idf[term] * tf * (self.k1 + 1) / (tf + norm[i])
        return out

    def search(self, query: str, k: int = 10) -> tuple[list[int], list[float]]:
        s = self.scores(query)
        top = np.argsort(-s)[:k]
        return top.tolist(), s[top].tolist()


def dense_search(query_vec: np.ndarray, doc_vecs: np.ndarray, k: int = 10) -> list[int]:
    return np.argsort(-(doc_vecs @ query_vec))[:k].tolist()


def rrf(rankings: list[list[int]], k: int = 10, c: int = 60) -> list[int]:
    """Reciprocal Rank Fusion: each list adds 1 / (c + rank). Needs no score calibration."""
    fused: Counter[int] = Counter()
    for ranking in rankings:
        for rank, idx in enumerate(ranking, start=1):
            fused[idx] += 1 / (c + rank)
    return [idx for idx, _ in fused.most_common(k)]
