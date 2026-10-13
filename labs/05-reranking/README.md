# Lab 05: Re-ranking

**La pregunta:** ¿cuánto mejora la precisión reordenar los primeros resultados con un
re-ranker, y cuánto cuesta en tiempo?

## 1. Concepto

La búsqueda densa compara **vectores calculados por separado**: el de la pregunta y el de cada
chunk. Es rápida porque los vectores de los chunks se calculan una sola vez, pero el modelo
nunca ve la pregunta y el chunk juntos.

Un **re-ranker** (cross-encoder) lee la pregunta y el chunk **en la misma entrada** y devuelve
un puntaje de relevancia. Es mucho más preciso y mucho más lento: hay que correrlo una vez por
cada par. Por eso se usa en dos etapas: la búsqueda rápida trae N candidatos y el re-ranker
reordena solo esos.

El puntaje del re-ranker sirve además para otra cosa: si el mejor candidato tiene un puntaje
bajo, probablemente la respuesta no está en el corpus. Eso se usa en el lab 07.

## 2. Método

- Chunks por estructura de 1000 caracteres (lab 03), 62 preguntas con evidencia.
- Primera etapa: densa con bge-m3, o híbrida con BM25 (el lab 04 encontró que la híbrida
  empeoraba; se vuelve a medir acá porque al re-ranker solo le importa que el pasaje esté entre
  los candidatos).
- Re-ranker: `BAAI/bge-reranker-v2-m3`, local en la GPU de la Mac, sobre 10, 20 o 50
  candidatos.

```bash
uv run labs/05-reranking/run.py
```

## 3. Resultados

Números completos en [`results.md`](results.md).

| Recuperación | Recall@1 | Recall@3 | Recall@5 | MRR@10 | Re-ranking por consulta |
|---|---|---|---|---|---|
| densa, sin re-ranking | 66 % | 87 % | 92 % | 0,77 | — |
| **densa + re-ranking de 10** | **74 %** | **95 %** | **97 %** | **0,84** | 1,4 s |
| densa + re-ranking de 20 | 73 % | 94 % | 97 % | 0,83 | 3,0 s |
| densa + re-ranking de 50 | 73 % | 92 % | 97 % | 0,83 | 7,6 s |
| híbrida + re-ranking de 10 | 73 % | 90 % | 95 % | 0,82 | 1,6 s |

## 4. Conclusión

1. **El re-ranking es la mejora más grande de todo el pipeline de recuperación**: el pasaje
   correcto queda primero en 74 % de las preguntas (antes 66 %) y entre los 3 primeros en 95 %
   (antes 87 %). Como el modelo lee el top 5 para responder, eso es lo que importa.
2. **Más candidatos no ayuda.** La búsqueda densa ya trae el pasaje en el top 10 el 98 % de las
   veces; reordenar 20 o 50 cuesta el doble o cinco veces más y no gana nada.
3. **Con re-ranking, la híbrida no aporta.** Densa y híbrida terminan iguales (73–74 % de
   recall@1). BM25 sale del pipeline: `src/llm_lab/rag.py` queda con densa top 10 + re-ranking.
4. **El costo es real: 1,4 s por consulta** en la Mac, que es más que todo el resto de la
   recuperación junto. Para la app es aceptable; con muchos usuarios habría que usar un
   re-ranker más chico o un servidor con GPU dedicada.

### Límites
- 62 preguntas: la diferencia entre 73 % y 74 % es una pregunta.
- Latencias medidas con otras cargas en la máquina (labs 02 y 14 por API).
