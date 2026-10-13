# Lab 03: Chunking

**La pregunta:** ¿qué forma de cortar los documentos recupera el pasaje correcto más seguido,
con el mismo modelo de embeddings y las mismas preguntas?

## 1. Concepto

Un **chunk** es el pedazo de documento que se convierte en vector, se busca y se le pasa al
modelo para responder. Es la unidad de todo lo que sigue: si el dato quedó partido entre dos
chunks, ninguno de los dos lo trae completo; si el chunk es enorme, su vector "promedia" muchos
temas y no se parece a ninguna pregunta concreta.

Dos familias:
- **Tamaño fijo**: cortar el texto cada N caracteres, con un solapamiento para no partir
  oraciones en el borde. No sabe nada de la estructura.
- **Por estructura** (`src/llm_lab/chunking.py`): juntar bloques seguidos de la misma sección
  hasta un tope, sin partir nunca un bloque; las tablas no se cortan (si son largas, se parten
  por filas repitiendo el encabezado), y a cada chunk se le antepone **el título del documento
  y la ruta de títulos**. Así un chunk que dice "$42.230,00" también dice "Costos de los
  trámites (licencias de conducir) > Aranceles > Costos de los trámites".

## 2. Método

- Corpus: los 49 documentos, parseados con lo que ganó en el lab 11 (`src/llm_lab/corpus.py`).
- **Set de preguntas** (`evals/questions.jsonl`): 62 preguntas escritas a mano leyendo el
  corpus, con palabras distintas a las del texto ("¿cuánto sale sacar la licencia por primera
  vez?" para un texto que dice "Otorgamiento de Licencia de Conducir"). Cada una tiene la
  evidencia exacta: un fragmento de texto y el documento donde está. Más 10 preguntas sin
  respuesta en el corpus para el lab 07. Se verificó que cada evidencia aparece tal cual.
- **Acierto**: un chunk recuperado acierta si es del documento correcto y **contiene la
  evidencia completa**. Si la corta a la mitad, no cuenta.
- Embeddings: `BAAI/bge-m3` local, coseno. Métricas: recall@k y MRR@10.

```bash
uv run labs/03-chunking/run.py
```

## 3. Resultados

Números completos en [`results.md`](results.md).

| Estrategia | Chunks | Recall@1 | Recall@5 | Recall@10 | MRR@10 | Caracteres en el top 5 |
|---|---|---|---|---|---|---|
| fijo 300 | 3.330 | 40 % | 65 % | 71 % | 0,50 | 1.488 |
| fijo 1000 / 200 | 1.263 | 58 % | **95 %** | **100 %** | 0,74 | 4.880 |
| fijo 2000 / 400 | 647 | 60 % | **95 %** | 98 % | 0,75 | 9.488 |
| un bloque por chunk | 4.254 | 65 % | 87 % | 90 % | 0,75 | 1.489 |
| estructura 1000 | 1.881 | **66 %** | 92 % | 98 % | **0,77** | 2.940 |
| estructura 1000 **sin ruta** | 1.881 | 55 % | 81 % | 92 % | 0,66 | 2.665 |

## 4. Conclusión

1. **La ruta de títulos es lo que más pesa.** Mismos cortes, con y sin ruta antepuesta:
   recall@1 de 55 % a 66 % y recall@5 de 81 % a 92 %. Un bloque que dice "$ 17540,00" no se
   parece a "¿cuánto cuesta la partida urgente?"; con "Solicitud de partidas urgentes > Costos
   del trámite" adelante, sí.
2. **Los chunks chicos cortan la evidencia.** Con 300 caracteres fijos, 18 preguntas no se
   encuentran ni en el top 10: el dato quedó partido o separado de lo que lo nombra.
3. **Por estructura gana arriba, por tamaño fijo grande gana abajo.** Estructura 1000 tiene
   el mejor recall@1 y MRR; fijo 1000 llega a 100 % en el top 10, pero cada chunk es casi el
   doble de largo. Para el RAG importa más que el bueno esté primero (el modelo lee el top 5)
   y que haya menos texto que leer: **estructura 1000** es la elección, y el lab 05 (re-ranking)
   ataca justamente el orden.
4. **Un bloque por chunk se queda corto**: buen recall@1, pero pierde contexto (q01 y q02 no se
   encuentran: el monto está en un bloque y lo que se paga, en otro, lo mismo que se vio en el
   lab 02).

### Límites
- 62 preguntas: diferencias de 2 o 3 puntos (una o dos preguntas) no son concluyentes.
- Las preguntas las escribió quien conoce el corpus; usuarios reales preguntan peor.
