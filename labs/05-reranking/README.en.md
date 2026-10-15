# Lab 05: Re-ranking

**The question:** how much does reordering the top results with a re-ranker improve precision,
and how much does it cost in time?

## 1. Concept

Dense search compares **vectors computed separately**: the question's and each
chunk's. It is fast because the chunk vectors are computed only once, but the model
never sees the question and the chunk together.

A **re-ranker** (cross-encoder) reads the question and the chunk **in the same input** and returns
a relevance score. It is much more precise and much slower: it has to be run once for
each pair. That is why it is used in two stages: the fast search brings N candidates and the re-ranker
reorders only those.

The re-ranker score is also useful for something else: if the best candidate has a low
score, the answer is probably not in the corpus. That is used in lab 07.

## 2. Method

- Structure-based chunks of 1000 characters (lab 03), 62 questions with evidence.
- First stage: dense with bge-m3, or hybrid with BM25 (lab 04 found that hybrid
  made things worse; it is measured again here because the re-ranker only cares that the passage is among
  the candidates).
- Re-ranker: `BAAI/bge-reranker-v2-m3`, local on the Mac's GPU, over 10, 20 or 50
  candidates.

```bash
uv run labs/05-reranking/run.py
```

## 3. Results

Full numbers in [`results.md`](results.md).

| Retrieval | Recall@1 | Recall@3 | Recall@5 | MRR@10 | Re-ranking per query |
|---|---|---|---|---|---|
| dense, no re-ranking | 66 % | 87 % | 92 % | 0.77 | — |
| **dense + re-ranking of 10** | **74 %** | **95 %** | **97 %** | **0.84** | 1.4 s |
| dense + re-ranking of 20 | 73 % | 94 % | 97 % | 0.83 | 3.0 s |
| dense + re-ranking of 50 | 73 % | 92 % | 97 % | 0.83 | 7.6 s |
| hybrid + re-ranking of 10 | 73 % | 90 % | 95 % | 0.82 | 1.6 s |

## 4. Conclusion

1. **Re-ranking is the biggest improvement in the whole retrieval pipeline**: the correct
   passage comes first in 74 % of the questions (previously 66 %) and among the top 3 in 95 %
   (previously 87 %). Since the model reads the top 5 to answer, that is what matters.
2. **More candidates do not help.** Dense search already brings the passage into the top 10 98 % of the
   time; reordering 20 or 50 costs twice or five times as much and gains nothing.
3. **With re-ranking, hybrid adds nothing.** Dense and hybrid end up the same (73–74 %
   recall@1). BM25 leaves the pipeline: `src/llm_lab/rag.py` stays with dense top 10 + re-ranking.
4. **The cost is real: 1.4 s per query** on the Mac, which is more than all the rest of
   retrieval combined. For the app it is acceptable; with many users a
   smaller re-ranker or a server with a dedicated GPU would be needed.

### Limits
- 62 questions: the difference between 73 % and 74 % is one question.
- Latencies measured with other loads on the machine (labs 02 and 14 via API).
