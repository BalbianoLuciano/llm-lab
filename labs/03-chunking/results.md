# Lab 03: resultados

Última corrida: 2026-10-13. Modelo de embeddings: `BAAI/bge-m3` (denso, coseno). 62 preguntas con respuesta en el corpus.

| Estrategia | Chunks | Largo medio (caracteres) | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR@10 | Caracteres leídos en el top 5 |
|---|---|---|---|---|---|---|---|---|
| fijo 300 / 0 | 3330 | 298 | 40% | 58% | 65% | 71% | 0.50 | 1,488 |
| fijo 500 / 100 | 2500 | 494 | 56% | 73% | 82% | 94% | 0.67 | 2,471 |
| fijo 1000 / 200 | 1263 | 976 | 58% | 89% | 95% | 100% | 0.74 | 4,880 |
| fijo 2000 / 400 | 647 | 1898 | 60% | 89% | 95% | 98% | 0.75 | 9,488 |
| un bloque por chunk | 4254 | 298 | 65% | 84% | 87% | 90% | 0.75 | 1,489 |
| estructura 500 | 2909 | 412 | 63% | 87% | 94% | 98% | 0.77 | 2,058 |
| estructura 1000 | 1881 | 588 | 66% | 87% | 92% | 98% | 0.77 | 2,940 |
| estructura 2000 | 1338 | 791 | 63% | 85% | 95% | 98% | 0.76 | 3,954 |
| estructura 1000 sin ruta | 1881 | 533 | 55% | 73% | 81% | 92% | 0.66 | 2,665 |

Preguntas sin acierto en el top 10:

- fijo 300 / 0: q01, q06, q07, q10, q11, q12, q14, q18, q24, q27, q28, q35, q37, q38, q39, q40, q49, q58
- fijo 500 / 100: q11, q15, q17, q40
- fijo 1000 / 200: —
- fijo 2000 / 400: q24
- un bloque por chunk: q01, q02, q16, q27, q28, q53
- estructura 500: q27
- estructura 1000: q27
- estructura 2000: q10
- estructura 1000 sin ruta: q10, q14, q15, q24, q42
