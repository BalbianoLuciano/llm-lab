# Lab 04: resultados

Última corrida: 2026-10-13. 1881 chunks (estructura, 1000 caracteres), 62 preguntas.

| Búsqueda | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR@10 | Indexado (s) | Consulta (ms) |
|---|---|---|---|---|---|---|---|
| BM25 (a mano) | 37% | 74% | 79% | 85% | 0.55 | 0.1 | 0.2 |
| densa: multilingual-e5-small | 42% | 74% | 81% | 92% | 0.59 | 55.4 | 5.5 |
| híbrida: multilingual-e5-small + BM25 | 50% | 76% | 84% | 94% | 0.64 | 55.4 | 5.5 |
| densa: multilingual-e5-large | 60% | 84% | 95% | 98% | 0.73 | 279.4 | 12.7 |
| híbrida: multilingual-e5-large + BM25 | 56% | 84% | 90% | 97% | 0.70 | 279.4 | 12.7 |
| densa: bge-m3 | 66% | 87% | 92% | 98% | 0.77 | 0.0 | 0.3 |
| híbrida: bge-m3 + BM25 | 55% | 84% | 92% | 98% | 0.70 | 0.0 | 0.3 |
| densa: Qwen3-Embedding-0.6B | 55% | 77% | 89% | 92% | 0.68 | 582.8 | 31.7 |
| híbrida: Qwen3-Embedding-0.6B + BM25 | 56% | 76% | 90% | 94% | 0.68 | 582.8 | 31.7 |

Preguntas que ninguna búsqueda encuentra en el top 10:

ninguna

Preguntas que BM25 encuentra y la mejor densa no (o al revés):

- q01 (¿Cuánto sale sacar la licencia de conducir por primera vez en la Ciudad?): BM25 —, multilingual-e5-large 5
- q06 (Soy jubilado y vivo en CABA, ¿pago la renovación del registro de conducir?): BM25 —, multilingual-e5-large 1
- q08 (¿Cuánto hay que pagar para pedir una partida de nacimiento urgente en la Ciudad?): BM25 —, multilingual-e5-large 3
- q09 (Si pido la partida sin urgencia, ¿cuánto tarda en llegar?): BM25 —, multilingual-e5-large 2
- q12 (¿La partida que pido en la Ciudad ya viene apostillada?): BM25 —, multilingual-e5-large 4
- q36 (¿Desde cuándo se aplican las tasas registrales de la guía 2026?): BM25 —, multilingual-e5-large 5
- q39 (¿Qué plazo tengo para informar a ARBA la transferencia de un auto?): BM25 —, multilingual-e5-large 1
- q40 (Me robaron el auto, ¿qué papeles necesito para darlo de baja en ARBA?): BM25 —, multilingual-e5-large 7
