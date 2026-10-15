# Lab 04: Embeddings and search

**The question:** dense search, keyword search (BM25) or hybrid: which one finds the correct
passage most often? Which local embedding model is the best choice?

## 1. Concept

- **Dense search**: an embedding model turns the question and each chunk into vectors;
  the chunks with the highest cosine similarity are returned. It finds synonyms and paraphrases
  ("sacar el registro" ≈ "otorgamiento de licencia de conducir", both meaning getting a driver's license) but can fail with
  proper names, acronyms and exact numbers.
- **BM25** (`src/llm_lab/search.py`, written by hand): a score based on shared words. Each
  word weighs more the rarer it is in the corpus (idf), the weight saturates if it repeats a lot in
  a chunk (k1), and it is normalized by length (b). It finds exactly "CENAT" or "SIGEVA", but
  does not know that "plata" and "monto" (money and amount) are similar.
- **Hybrid with RRF** (Reciprocal Rank Fusion): the two lists are combined by adding
  1 / (60 + position) from each. It does not need the scores to be on the same scale.
- **Prefixes**: each model asks for one format for questions and another for documents
  (`query:` / `passage:` in e5, an instruction in Qwen3-Embedding). They are in
  `src/llm_lab/embeddings.py`.

## 2. Method

- Chunks: structure-based, 1000 characters with heading path (winner of lab 03), 1,881.
- 62 questions with evidence (`evals/questions.jsonl`), same hit criterion as lab 03.
- Four local models on the Mac's GPU (MPS): `multilingual-e5-small` (118M),
  `multilingual-e5-large` (560M), `bge-m3` (568M), `Qwen3-Embedding-0.6B`.

```bash
uv run labs/04-embeddings-busqueda/run.py
```

## 3. Results

Full numbers in [`results.md`](results.md).

| Search | Recall@1 | Recall@5 | Recall@10 | MRR@10 | Indexing the corpus |
|---|---|---|---|---|---|
| BM25 (by hand) | 37 % | 79 % | 85 % | 0.55 | 0.1 s |
| dense: e5-small | 42 % | 81 % | 92 % | 0.59 | 55 s |
| dense: e5-large | 60 % | 95 % | 98 % | 0.73 | 279 s |
| **dense: bge-m3** | **66 %** | 92 % | 98 % | **0.77** | ~300 s * |
| dense: Qwen3-Embedding-0.6B | 55 % | 89 % | 92 % | 0.68 | 583 s |
| hybrid: bge-m3 + BM25 | 55 % | 92 % | 98 % | 0.70 | |
| hybrid: e5-small + BM25 | 50 % | 84 % | 94 % | 0.64 | |

\* bge-m3 was already cached from lab 03; the time is from the original computation, of the same order as
e5-large.

## 4. Conclusion

1. **bge-m3 is the best dense model** for these questions: best recall@1 and MRR. e5-large
   comes close and has a better recall@5. Qwen3-Embedding-0.6B, the newest, is the worst of the
   large ones and the slowest on the Mac.
2. **Hybrid search does not help: it makes things worse.** Contrary to the SDD, which took it for granted. With bge-m3,
   adding BM25 lowers recall@1 from 66 % to 55 %. The reason: BM25 is much weaker here (37 %
   recall@1, because the questions use words different from the text, on purpose) and RRF gives it the
   same weight as the dense one, so it pushes bad chunks to the top. It only helps when the
   dense model is also weak (e5-small: 42 % → 50 %).
3. **BM25 does not rescue any question that dense search misses.** In the 8 where they differ, dense
   gets it right and BM25 does not. The questions with acronyms or exact numbers, where BM25 should shine,
   are solved by bge-m3 anyway.
4. **Problem for the design:** `src/llm_lab/rag.py` used hybrid as the first stage.
   Before changing it, lab 05 measures both with re-ranking: the re-ranker reorders the first
   20, so it is enough for the correct passage to be among them.

### Limits
- The questions were written paraphrasing on purpose, which hurts BM25. With users
  who copy words from the document ("certificado de dominio urgente") BM25 would perform better.
- Giving each list a different weight in the fusion was not tried.
