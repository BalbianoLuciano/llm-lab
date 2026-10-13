# Lab 12: resultados

Última corrida: 2026-10-13. 15506 vectores reales (bge-m3, 1024 dimensiones), 72 consultas. Verdad: búsqueda exacta con numpy.

## Velocidad contra recall

| Índice | ef | Construcción (s) | Consulta (ms) | Recall@10 vs exacto | Distancias calculadas por consulta |
|---|---|---|---|---|---|
| numpy exacto | — | 0.0 | 2.12 | 100.0% | 15,506 |
| HNSW propio, vecinos más cercanos | 10 | 22.3 | 0.19 | 56.0% | 193 |
| HNSW propio, vecinos más cercanos | 20 | 22.3 | 0.27 | 60.4% | 258 |
| HNSW propio, vecinos más cercanos | 50 | 22.3 | 0.63 | 67.6% | 438 |
| HNSW propio, vecinos más cercanos | 100 | 22.3 | 0.95 | 73.1% | 696 |
| HNSW propio, vecinos más cercanos | 200 | 22.3 | 1.79 | 77.4% | 1,170 |
| HNSW propio, heurística de diversidad | 10 | 442.1 | 1.63 | 76.5% | 223 |
| HNSW propio, heurística de diversidad | 20 | 442.1 | 2.34 | 82.4% | 312 |
| HNSW propio, heurística de diversidad | 50 | 442.1 | 3.92 | 90.0% | 561 |
| HNSW propio, heurística de diversidad | 100 | 442.1 | 6.28 | 95.4% | 915 |
| HNSW propio, heurística de diversidad | 200 | 442.1 | 16.95 | 96.8% | 1,562 |
| Qdrant modo local | — | 130.8 | 240.47 | 99.7% | 15,506 |
| Qdrant servidor | 10 | 36.3 | 7.02 | 80.4% | — |
| Qdrant servidor | 20 | 36.3 | 7.49 | 85.3% | — |
| Qdrant servidor | 50 | 36.3 | 6.91 | 88.1% | — |
| Qdrant servidor | 100 | 36.3 | 5.86 | 91.1% | — |
| Qdrant servidor | 200 | 36.3 | 10.49 | 95.0% | — |

## Filtros

| Filtro | Fracción de vectores que pasa | Estrategia | Resultados devueltos (de 10) | Recall@10 vs exacto filtrado |
|---|---|---|---|---|
| jurisdicción | 50.8% | HNSW propio (heurística), top 10 y después filtrar | 9.4 | 92.1% |
| jurisdicción | 50.8% | HNSW propio (heurística), top 100 y después filtrar | 9.8 | 96.8% |
| jurisdicción | 50.8% | Qdrant servidor, filtro durante la búsqueda | 10.0 | 99.8% |
| documento | 1.0% | HNSW propio (heurística), top 10 y después filtrar | 7.6 | 75.3% |
| documento | 1.0% | HNSW propio (heurística), top 100 y después filtrar | 9.5 | 95.0% |
| documento | 1.0% | Qdrant servidor, filtro durante la búsqueda | 10.0 | 99.7% |
