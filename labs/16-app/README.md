# Lab 16: App y experimento final

**La pregunta del proyecto:** ¿corregir los documentos con el semáforo **antes** de indexarlos
mejora las respuestas del RAG?

## 1. La app

Todo lo de los labs anteriores, junto y usable (`app/`):

```bash
uv run uvicorn app.main:app      # http://localhost:8000
uv run pytest                    # flujo completo con un evaluador falso, sin modelos
```

| Pantalla | Qué hace |
|---|---|
| **Documentos** | Subir un PDF, HTML o Word. Se parsea en un proceso aparte (Docling para PDF, parser propio para HTML y Word, como decidió el lab 11) y se guarda como versión 1. |
| **Documento** | El texto con cada bloque coloreado y un contador ("4 rojos · 7 amarillos"). "Evaluar" corre el semáforo con progreso en vivo (SSE). "Indexar" aparece solo cuando no quedan rojos bloqueantes. |
| **Revisión** | Salta al primer rojo. Muestra la regla, su norma y qué significa el rojo, y pregunta qué falta. La persona contesta; un LLM reescribe solo ese bloque; se re-evalúa y se muestra el antes y el después palabra por palabra. Si la reescritura trae números que no estaban ni en el bloque ni en la respuesta, no se puede aceptar (lab 15). Atajos: `n` siguiente, `p` anterior, `Enter` aceptar, `Esc` saltear. |
| **Chat** | Responde solo con documentos indexados, en streaming, y lista los fragmentos citados. |
| **Reglas** | Las reglas con su norma. Escribir una nueva en lenguaje natural la compila (lab 14) o pide un criterio si es vaga. |

Decisiones tomadas por lo que midieron los labs:
- **Evaluador**: Qwen3.5-4B por logprobs local (lab 13: rinde igual que el 9B con la mitad de
  memoria). En la app con un solo orden de opciones, por velocidad; offline, con dos.
- **Qué reglas mira cada bloque**: filtros baratos (R6/R8 solo donde hay montos, R7 donde hay
  fechas, R3 donde hay enlaces, R2 en tablas…). Sin ellos, un documento de 100 bloques necesita
  unas 800 pasadas del modelo.
- **Guardrail de la revisión**: el determinista (números nuevos). El del evaluador se dejó
  afuera porque daba falsas alarmas (lab 15).
- **Cada corrección es una versión nueva** (SQLite): el original y el historial (qué regla, qué
  contestó la persona) no se pierden; los veredictos de los otros bloques se reutilizan.
- **Recuperación**: densa + re-ranking (labs 04 y 05), sin BM25.

### Prueba con los modelos reales

Con la página de aranceles de licencias de CABA (`data/raw/corpus/caba-licencias-aranceles.html`):

1. Subida y parseo: menos de un segundo.
2. Semáforo: 49 evaluaciones en 59 s. Marcó, entre otros, 3 montos sin vigencia (R8) y **el
   documento entero en rojo por R9**: la página no dice quién la publica ni cuándo (es cierto).
3. Revisión de R9: la persona contesta "lo publica el Gobierno de la Ciudad (Dirección General
   de Habilitación de Conductores), actualizado el 2 de marzo de 2026" → se agrega una oración
   al comienzo → R9 pasa a verde (28 s, con un modelo de respaldo porque Groq ya no tenía cuota).
4. Revisión de R8 sobre "$42.230,00" → "$42.230,00 (rige desde el 1 de enero de 2026, según la
   Ley Tarifaria 2026)" → verde (2 s).
5. Chat: "¿Quién publica la información de aranceles y cuánto cuesta el CENAT?" → responde los
   dos datos con dos citas, en streaming. **El primero solo se puede responder porque se
   corrigió R9**: el documento original no lo decía.

Encontrado en esta prueba y corregido: los problemas de alcance documento (R9, R10) bloqueaban
la indexación pero no aparecían en la revisión, así que un documento sin emisor no se podía
indexar nunca. Ahora la revisión los incluye y la corrección agrega una oración al comienzo.

Lo que la app todavía no hace (y por qué):
- **R1 (color)**: el parser no guarda el estilo del texto (SDD, riesgo 3).
- **R5, R11 y R12** no se evalúan en esta versión.
- Reglas deterministas generadas por el compilador: el compilador no genera código (lab 14).

## 2. El experimento

### Método

Dos corpus con el mismo pipeline de RAG, el mismo modelo y el mismo juez:

- **A**: los 49 documentos tal como salen del parseo.
- **B**: los mismos, después de pasar por el semáforo y la revisión guiada.

Pasos (`experiment.py`, cada uno se puede retomar):

1. **Semáforo**: R6 (moneda) y R8 (vigencia) sobre los 60 bloques con montos de los documentos
   que usan las preguntas, con el evaluador de 4B y dos órdenes de opciones.
2. **Revisión guiada automática** de los rojos. La "persona" que contesta es un LLM que hace
   de **autor del documento**: solo ve las oraciones con fechas de su propio documento, y si el
   dato no está, contesta "no sé". Otro LLM reescribe el bloque; el guardrail determinista
   rechaza números que no estén en el documento.
3. **RAG sobre A y sobre B**, comparando las preguntas donde los corpus pueden diferir: las 8 del
   set general cuya evidencia está en un documento corregido, 7 preguntas nuevas de vigencia
   ("¿desde cuándo rige la tasa de $154.000…?", `vigencia_questions.jsonl`) y las 10 sin
   respuesta.

Respuestas y juez: **Qwen3.5-9B local**. Se planeó con Qwen3.8-27B en Groq, pero el tier
gratuito tiene un tope de **200.000 tokens por día por modelo** y los labs de este día lo
agotaron en los dos modelos de Groq. Como A y B usan el mismo modelo y el mismo juez, la
comparación sigue siendo justa.

```bash
uv run labs/16-app/experiment.py --phase gate
uv run labs/16-app/experiment.py --phase review
uv run labs/16-app/experiment.py --phase rag
uv run labs/16-app/experiment.py --phase report
```

### Resultados

Todo, con ejemplos de reescritura, en [`results.md`](results.md).

| Etapa | Resultado |
|---|---|
| Semáforo, R8 vigencia | 43 rojos de 60 bloques con montos |
| Semáforo, R6 moneda | 0 rojos, 56 amarillos (solo el signo $) |
| Revisión | 40 revisados (3 quedaron sin revisar por la cuota), 33 corregidos, 3 marcados [FALTA], 1 rechazado por números nuevos |

| Preguntas | A, correctas | B, correctas |
|---|---|---|
| 8 del set general (evidencia en un documento corregido) | 7 | 7 |
| 7 de vigencia | 6 | 6 |
| 10 sin respuesta: se abstiene | 10 | 10 |

Cambiaron dos preguntas, en sentidos opuestos:
- **v07 mejoró.** En el documento de IOMA, cada fecha ("A partir del 01/06/2026") y su monto
  ("$ 105.037") estaban en bloques separados, y con A el modelo emparejó mal: respondió agosto en
  vez de junio. La corrección juntó la fecha con su monto en el mismo bloque.
- **v02 empeoró.** Su bloque fue uno de los 3 que no llegaron a corregirse; los otros chunks
  corregidos de la misma guía probablemente desplazaron del top 5 al fragmento con la vigencia
  (no se verificó), y el modelo se abstuvo.

### Conclusión

1. **En este corpus, corregir antes de indexar no mejoró las respuestas: empate.** La hipótesis
   del proyecto no queda demostrada. Con 15 preguntas comparables, un empate 13 a 13 no prueba
   que no haya efecto, pero tampoco hay señal de uno grande.
2. **Por qué: el RAG compensa lo que el semáforo marca.** R8 marcó 43 bloques sin vigencia, y
   es cierto que el bloque no la tiene. Pero la guía de tasas repite "Vigencia para documentos
   ingresados a partir del 01/01/26" en cada sección: la recuperación trae ese fragmento junto
   con el del monto y el modelo los conecta. En A ya respondía 6 de 7 preguntas de vigencia. El
   semáforo evalúa el bloque aislado; el RAG lee varios bloques juntos. **Lo que es rojo para un
   lector que salta a ese párrafo no es necesariamente rojo para el RAG.**
3. **Donde la corrección sí ayudó fue en la estructura, no en el dato.** v07 mejoró porque la
   revisión volvió a juntar una fecha con su monto, que el parseo había separado (el mismo
   problema que apareció en los labs 02 y 11). Eso apunta a otra versión del producto: un
   semáforo que detecte **datos desalineados** (montos sin su concepto o su fecha en el mismo
   bloque) más que reglas de redacción.
4. **Las correcciones tienen efectos secundarios en la recuperación.** Cambiar unos bloques
   cambia qué fragmentos compiten por el top 5, y eso puede empeorar preguntas que no tenían nada
   que ver (v02). Corregir parcialmente un documento puede ser peor que no tocarlo.
5. **Las reescrituras siguen siendo riesgosas aun sin inventar números**: "se verá impactado en
   la cuota del mes de abril 2026" pasó a "a partir del 1 de abril de 2026". Plausible, no
   idéntico. La aceptación humana con el antes y el después (la pantalla de revisión) no es un
   detalle de UX: es la última línea de defensa.

6. **El valor que el experimento no midió.** En la prueba de la app, la pregunta "¿quién
   publica esto?" pasó a tener respuesta **solo** porque se corrigió R9. Las reglas que agregan
   un dato que el documento no tenía (emisor, fecha, vigencia ausente en todo el documento)
   sí cambian lo que el RAG puede responder; las que reacomodan un dato que ya estaba en otro
   lado, no. El set de preguntas del experimento casi no tenía del primer tipo.

### Problemas que deja abiertos
- **Medir el valor del semáforo con otra vara.** Para el RAG, las reglas de redacción y vigencia
  aportan poco en este corpus; para una persona que lee un bloque suelto (o un buscador que
  muestra un fragmento), aportan más. Hace falta una evaluación centrada en el lector, no solo
  en la respuesta del chat.
- **Cuotas.** Con el tier gratuito, el proyecto entero no entra en un día: 200.000 tokens por
  modelo y por día en Groq, 20 pedidos por día en Gemini. El modelo local resuelve el costo,
  pero tarda alrededor de un minuto por respuesta en la Mac.
- **Escala del experimento**: 15 preguntas comparables y una sola corrida. Para decir algo
  firme harían falta más documentos con problemas reales y más preguntas que dependan de ellos.
