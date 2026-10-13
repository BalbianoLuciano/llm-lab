# Lab 07: Cuándo no sabe

**La pregunta:** cuando la respuesta no está en los documentos, ¿el sistema dice "no tengo esa
información" en vez de inventar? ¿Y a qué costo para las preguntas que sí tienen respuesta?

## 1. Concepto

Hay dos lugares donde el sistema puede decidir no responder:

- **Antes de generar**: si el mejor fragmento que encontró el re-ranker tiene un puntaje bajo,
  probablemente la respuesta no está. Un umbral corta ahí y no se llama al modelo.
- **Al generar**: el prompt le pide al modelo que, si los fragmentos no responden, lo diga con
  una frase exacta.

Son dos errores con costos distintos: inventar una respuesta (grave: alguien paga un monto
equivocado) o callarse teniendo el dato (molesto: la persona busca por otro lado).

## 2. Método

- Las 72 respuestas del lab 06: 62 preguntas con respuesta y 10 sin (`u01`–`u10`: pasaporte,
  VTV en la Ciudad, boleto mínimo de colectivo, etc.).
- El umbral del re-ranker se elige con validación dejando uno afuera: el de cada pregunta se
  ajusta con las otras 71, para no medir sobre lo mismo que se ajustó.
- **Variante del prompt (B)**: misma instrucción, más una línea que aclara que la pregunta
  puede usar otras palabras, sinónimos o siglas que los fragmentos, y que se responda si algún
  fragmento tiene el dato. Se re-pregunta sobre **los mismos fragmentos** del lab 06.

```bash
uv run labs/07-cuando-no-sabe/run.py
```

## 3. Resultados

Números completos en [`results.md`](results.md).

| Estrategia | Se abstiene sin respuesta | Se abstiene **con** respuesta | Inventa |
|---|---|---|---|
| Solo el modelo (prompt A) | **10/10** | 5/62 | 0 |
| Solo umbral del re-ranker | 4/10 | 1/62 | — |
| Modelo + umbral | 10/10 | 5/62 | 0 |
| Prompt B (parcial: 58 de 72) | 6/6 | 3/52 | 0 |

Puntaje del mejor fragmento según el re-ranker: mediana 0,89 en las preguntas con respuesta y
**0,56** en las sin respuesta, con máximos de 1,00 y **0,99**.

## 4. Conclusión

1. **El umbral del re-ranker no sirve para detectar preguntas sin respuesta.** "¿Cuánto cuesta
   la VTV en la Ciudad?" tiene puntaje 0,99: el corpus tiene la VTV de la Provincia. El
   re-ranker mide si el fragmento habla del mismo tema, no si responde la pregunta. Con el
   umbral solo se detectan 4 de 10, y agregarlo al modelo no suma nada.
2. **El modelo sí distingue**: lee el fragmento y ve que es de otra jurisdicción. 10 de 10.
   Esto contradice el diseño del SDD (§5.5 y §9), que ponía el umbral del re-ranker como
   guardrail contra respuestas sin evidencia. **Problema para el diseño**: el guardrail tiene
   que ser el modelo (o un clasificador sobre pregunta + fragmento), no un puntaje de similitud.
3. **El costo es la sobre-abstención**: 5 de 62 preguntas con respuesta, 3 de ellas con la
   evidencia en los fragmentos. El prompt B, que aclara que las palabras pueden no coincidir,
   la baja a 3 de 52 sin empezar a inventar en las preguntas sin respuesta (6 de 6).
4. **Medición incompleta.** La variante B quedó en 58 de 72 preguntas: la cuota diaria de
   Groq (200.000 tokens por modelo, ver el lab 16) se agotó. La tendencia es clara, pero no
   alcanza para cambiar el prompt de producción sin completar la corrida.

### Límites
- 10 preguntas sin respuesta: pocas para estimar una tasa; alcanzan para ver que el umbral no
  separa.
