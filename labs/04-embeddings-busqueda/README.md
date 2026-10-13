# Lab 04: Embeddings y búsqueda

**La pregunta:** búsqueda densa, por palabras (BM25) o híbrida: ¿cuál encuentra el pasaje
correcto más seguido? ¿Qué modelo de embeddings local conviene?

## 1. Concepto

- **Búsqueda densa**: un modelo de embeddings convierte la pregunta y cada chunk en vectores;
  se devuelven los chunks con mayor similitud coseno. Encuentra sinónimos y paráfrasis
  ("sacar el registro" ≈ "otorgamiento de licencia de conducir") pero puede fallar con
  nombres propios, siglas y números exactos.
- **BM25** (`src/llm_lab/search.py`, escrito a mano): puntaje por palabras compartidas. Cada
  palabra pesa más cuanto más rara es en el corpus (idf), el peso satura si se repite mucho en
  un chunk (k1) y se normaliza por largo (b). Encuentra exactamente "CENAT" o "SIGEVA", pero
  no sabe que "plata" y "monto" se parecen.
- **Híbrida con RRF** (Reciprocal Rank Fusion): se combinan las dos listas sumando
  1 / (60 + posición) de cada una. No necesita que los puntajes estén en la misma escala.
- **Prefijos**: cada modelo pide un formato para preguntas y otro para documentos
  (`query:` / `passage:` en e5, una instrucción en Qwen3-Embedding). Están en
  `src/llm_lab/embeddings.py`.

## 2. Método

- Chunks: estructura de 1000 caracteres con ruta de títulos (ganador del lab 03), 1.881.
- 62 preguntas con evidencia (`evals/questions.jsonl`), mismo criterio de acierto del lab 03.
- Cuatro modelos locales en la GPU de la Mac (MPS): `multilingual-e5-small` (118M),
  `multilingual-e5-large` (560M), `bge-m3` (568M), `Qwen3-Embedding-0.6B`.

```bash
uv run labs/04-embeddings-busqueda/run.py
```

## 3. Resultados

Números completos en [`results.md`](results.md).

| Búsqueda | Recall@1 | Recall@5 | Recall@10 | MRR@10 | Indexar el corpus |
|---|---|---|---|---|---|
| BM25 (a mano) | 37 % | 79 % | 85 % | 0,55 | 0,1 s |
| densa: e5-small | 42 % | 81 % | 92 % | 0,59 | 55 s |
| densa: e5-large | 60 % | 95 % | 98 % | 0,73 | 279 s |
| **densa: bge-m3** | **66 %** | 92 % | 98 % | **0,77** | ~300 s * |
| densa: Qwen3-Embedding-0.6B | 55 % | 89 % | 92 % | 0,68 | 583 s |
| híbrida: bge-m3 + BM25 | 55 % | 92 % | 98 % | 0,70 | |
| híbrida: e5-small + BM25 | 50 % | 84 % | 94 % | 0,64 | |

\* bge-m3 ya estaba en caché del lab 03; el tiempo es del cálculo original, del mismo orden que
e5-large.

## 4. Conclusión

1. **bge-m3 es el mejor modelo denso** para estas preguntas: mejor recall@1 y MRR. e5-large
   queda cerca y tiene mejor recall@5. Qwen3-Embedding-0.6B, el más nuevo, es el peor de los
   grandes y el más lento en la Mac.
2. **La búsqueda híbrida no ayuda: empeora.** Contra el SDD, que la daba por hecha. Con bge-m3,
   sumar BM25 baja el recall@1 de 66 % a 55 %. La razón: BM25 es mucho más débil acá (37 % de
   recall@1, porque las preguntas usan palabras distintas al texto, a propósito) y RRF le da el
   mismo peso que a la densa, así que sube chunks malos al principio. Solo ayuda cuando el
   modelo denso también es débil (e5-small: 42 % → 50 %).
3. **BM25 no rescata ninguna pregunta que la densa pierda.** En las 8 donde difieren, la densa
   acierta y BM25 no. Las preguntas con siglas o números exactos, donde BM25 debería brillar,
   las resuelve igual bge-m3.
4. **Problema para el diseño:** `src/llm_lab/rag.py` usaba la híbrida como primera etapa.
   Antes de cambiarlo, el lab 05 mide las dos con re-ranking: el re-ranker reordena los 20
   primeros, así que alcanza con que el pasaje correcto esté entre ellos.

### Límites
- Las preguntas se escribieron parafraseando a propósito, lo que perjudica a BM25. Con usuarios
  que copian palabras del documento ("certificado de dominio urgente") BM25 rendiría mejor.
- No se probó dar distinto peso a cada lista en la fusión.
