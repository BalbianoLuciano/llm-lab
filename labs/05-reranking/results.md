# Lab 05: resultados

Última corrida: 2026-10-13. 1881 chunks, 62 preguntas con respuesta. Re-ranker: `BAAI/bge-reranker-v2-m3` en MPS.

| Recuperación | Candidatos | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR@10 | Re-ranking por consulta (ms) |
|---|---|---|---|---|---|---|---|
| densa (bge-m3), sin re-ranking | — | 66% | 87% | 92% | 98% | 0.77 | 0 |
| densa (bge-m3) + re-ranking | 10 | 74% | 95% | 97% | 98% | 0.84 | 1401 |
| densa (bge-m3) + re-ranking | 20 | 73% | 94% | 97% | 98% | 0.83 | 2955 |
| densa (bge-m3) + re-ranking | 50 | 73% | 92% | 97% | 98% | 0.83 | 7613 |
| híbrida (bge-m3 + BM25, RRF), sin re-ranking | — | 55% | 84% | 92% | 97% | 0.69 | 0 |
| híbrida (bge-m3 + BM25, RRF) + re-ranking | 10 | 73% | 90% | 95% | 97% | 0.82 | 1551 |
| híbrida (bge-m3 + BM25, RRF) + re-ranking | 20 | 73% | 92% | 95% | 97% | 0.82 | 3751 |
| híbrida (bge-m3 + BM25, RRF) + re-ranking | 50 | 73% | 92% | 95% | 98% | 0.83 | 6143 |
