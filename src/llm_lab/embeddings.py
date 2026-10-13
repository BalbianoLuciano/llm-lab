"""Local embedding models with an on-disk cache (re-embedding the corpus costs minutes).

    emb = Embedder("BAAI/bge-m3")
    doc_vecs = emb.documents(["texto 1", "texto 2"])   # (n, d), L2-normalised
    q_vec = emb.queries(["¿cuánto cuesta...?"])

Each model wants its own prefixes for queries and documents; they live in PROMPTS.
"""

import hashlib
import pickle
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "interim" / "embeddings"

# (query prefix, document prefix) as each model card recommends
PROMPTS = {
    "BAAI/bge-m3": ("", ""),
    "intfloat/multilingual-e5-large": ("query: ", "passage: "),
    "intfloat/multilingual-e5-small": ("query: ", "passage: "),
    "Qwen/Qwen3-Embedding-0.6B": (
        ("Instruct: Dada una pregunta sobre un trámite, encontrá el pasaje que la responde\n"
         "Query: "), ""),
}


class Embedder:
    def __init__(self, name: str, device: str = "mps"):
        self.name = name
        self.device = device
        self._model = None
        self._path = CACHE / f"{name.replace('/', '__')}.pkl"
        self._cache: dict[str, np.ndarray] = (
            pickle.loads(self._path.read_bytes()) if self._path.exists() else {})

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.name, device=self.device)
        return self._model

    def _encode(self, texts: list[str], prefix: str) -> np.ndarray:
        keys = [hashlib.sha1((prefix + t).encode()).hexdigest() for t in texts]
        missing = [(k, prefix + t) for k, t in zip(keys, texts) if k not in self._cache]
        if missing:
            vecs = self.model.encode([t for _, t in missing], batch_size=16,
                                     normalize_embeddings=True, show_progress_bar=False,
                                     convert_to_numpy=True)
            for (k, _), v in zip(missing, vecs):
                self._cache[k] = v.astype(np.float32)
            CACHE.mkdir(parents=True, exist_ok=True)
            self._path.write_bytes(pickle.dumps(self._cache))
        return np.stack([self._cache[k] for k in keys])

    def queries(self, texts: list[str]) -> np.ndarray:
        return self._encode(texts, PROMPTS.get(self.name, ("", ""))[0])

    def documents(self, texts: list[str]) -> np.ndarray:
        return self._encode(texts, PROMPTS.get(self.name, ("", ""))[1])
