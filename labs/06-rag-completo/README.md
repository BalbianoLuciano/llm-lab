# Lab 06: RAG completo

**La pregunta:** con todo el pipeline armado, ¿las respuestas son correctas, están respaldadas
por lo que se recuperó y citan el fragmento correcto?

## 1. Concepto

El pipeline (`src/llm_lab/rag.py`), con lo que ganó en cada lab anterior:

1. Chunks por estructura de 1000 caracteres con la ruta de títulos (lab 03).
2. Búsqueda densa con bge-m3, top 10 (lab 04: la híbrida no ayudaba).
3. Re-ranking con bge-reranker-v2-m3, top 5 (lab 05).
4. Generación con Qwen3.8-27B: responder **solo** con los fragmentos, citar cada dato con su
   número `[n]`, y si no está, decir exactamente "No tengo esa información en los documentos".
   Los fragmentos van marcados como datos, no como instrucciones (defensa básica contra
   prompt injection, SDD §9).

Tres cosas distintas que medir:
- **Correcta**: ¿tiene el dato esperado?
- **Fiel** (*faithfulness*): ¿todo lo que afirma está en los fragmentos que cita? Una respuesta
  puede ser correcta y no fiel (sabe el dato "de memoria") o fiel e incorrecta (cita bien un
  fragmento que no responde).
- **Cita correcta**: ¿el fragmento citado contiene la evidencia? Esto se mide **sin LLM**:
  string exacto de la evidencia dentro del chunk citado.

## 2. Método

- 72 preguntas (`evals/questions.jsonl`): 62 con respuesta en el corpus y 10 sin.
- Correctitud y fidelidad las juzga **otro modelo** (gpt-oss-120b) con un criterio escrito
  (`run.py`), para no sumar el sesgo de que un modelo se corrija a sí mismo. El lab 10 mide
  cuánto se puede confiar en ese juez.

```bash
uv run labs/06-rag-completo/run.py
```

## 3. Resultados

Números y cada respuesta fallida en [`results.md`](results.md).

| Métrica | Resultado |
|---|---|
| Pasaje correcto entre los 5 recuperados | 60/62 |
| Respuesta correcta (juez) | 50/62 (+7 parciales) |
| Respuesta incorrecta (juez) | 5/62, **las 5 son "no tengo esa información"** |
| Respuestas respaldadas por lo que citan | 55/57, 0 no respaldadas |
| Cita el fragmento que tiene la evidencia | 55/62 |
| Se abstiene en preguntas sin respuesta | **10/10** |
| Latencia p50 (recuperación + generación) | 2,2 s |

## 4. Conclusión

1. **El sistema no inventa.** Ninguna respuesta afirma algo que no esté en lo que cita, y en
   las 10 preguntas sin respuesta en el corpus dice que no sabe. El costo de esa prudencia son
   las 5 incorrectas: todas son abstenciones.
2. **Dos fallas de recuperación y tres de exceso de prudencia.** En q01 y q27 el pasaje no
   llegó al top 5. En q03, q20 y q59 **la evidencia estaba en los fragmentos** y el modelo dijo
   que no sabía (por ejemplo, no conectó "la obra social de la Ciudad" con "ObSBA"). Eso lo
   ataca el lab 07.
3. **Bug encontrado: las citas de otro modelo no se contaban.** Cuando Qwen da 429, responde
   gpt-oss, que cita con corchetes de ancho completo (`【1】`). El parser solo reconocía `[1]`,
   y el juez marcaba esas respuestas como "no respaldadas" (eran 2). Corregido en `rag.py`.
   Una cadena de respaldo entre modelos cambia el formato de salida, no solo la calidad.
4. **Las "parciales" son, en su mayoría, respuestas correctas a lo que se preguntó** que no
   repiten un detalle extra de la respuesta esperada (el horario cuando se preguntó la
   dirección). El lab 10 muestra que este juez es más estricto que una lectura humana.

### Límites
- Juez y respondedor son modelos distintos, pero el juez no está validado contra personas
  reales: ver el lab 10.
- 62 preguntas escritas por quien conoce el corpus.
