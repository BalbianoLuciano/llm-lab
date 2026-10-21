# Lab 17: Base sucia contra base limpia

**La pregunta:** la regla dice que una base vectorial mal armada ensucia el RAG. ¿Cuánto? Si
en vez del pipeline de los labs 03 y 11 se indexa el texto crudo de cada archivo, cortado cada
1000 caracteres, ¿cuántas respuestas se pierden?

## 1. Concepto

El experimento del lab 16 comparó una base limpia con la misma base después de corregir la
redacción, y dio empate. Pero las dos ya habían pasado por el parseo y el chunking de los labs
03 y 11: no comparaba una base sucia con una limpia. Este lab sí lo hace, y separa los pasos
para ver cuál importa:

| Base | Qué se indexa |
|---|---|
| **Limpia** (producción) | El mejor parser por formato, sin encabezados repetidos, párrafos rotos unidos, chunks por estructura de 1000 caracteres con el título y la ruta de títulos adelante |
| **Sin ruta** | Los mismos chunks, sin el título ni la ruta de títulos |
| **Fijo** | Los mismos bloques limpios, cortados cada 1000 caracteres con 200 de solapamiento |
| **Sucia** | Lo que hace una primera versión: el texto plano del archivo (`get_text` de PyMuPDF, `get_text` de BeautifulSoup sobre la página entera, `textutil` a txt), sin limpiar, cortado cada 1000 caracteres. Las tablas salen como líneas sueltas; los menús y los pies quedan |

Un ejemplo de la base sucia: un volante de ARBA sale con una palabra por renglón.

## 2. Método

- Las 72 preguntas de siempre (`evals/questions.jsonl`): 62 con respuesta en el corpus y 10 sin.
- La misma recuperación en las cuatro bases: bge-m3 denso, re-ranking del top 10 con
  bge-reranker-v2-m3, top 5 al modelo. Un chunk "tiene la evidencia" si contiene el texto
  esperado, sin contar espacios (la base sucia corta renglones en cualquier lado).
- Respuestas en las bases limpia y sucia con **un solo modelo fijo**, Qwen3.5-9B local, y el
  mismo juez, gpt-oss-120b en Groq, en las 124 respuestas.
- Un Score tipo Jev (`src/llm_lab/system_one.py`, Qwen3.5-4B por logprobs) sobre 100 chunks al
  azar de cada base: "si un asistente solo pudiera leer este fragmento, ¿qué tan bien
  respondería?", de 1 a 5.

```bash
uv run labs/17-base-sucia/run.py --phase retrieval
uv run labs/17-base-sucia/run.py --phase rag
uv run labs/17-base-sucia/run.py --phase context
uv run labs/17-base-sucia/run.py --phase score
uv run labs/17-base-sucia/run.py --phase report
```

## 3. Resultados

Todo, pregunta por pregunta, en [`results.md`](results.md).

### Recuperación (62 preguntas con respuesta)

| Base | Chunks | Re-ranking: primero | Re-ranking: en el top 5 |
|---|---|---|---|
| Limpia | 1881 | 46 | 60 |
| Sin ruta | 1881 | 38 | 56 |
| Fijo | 1263 | 49 | 62 |
| Sucia | 1280 | 41 | 57 |

### Respuestas (mismo modelo y mismo juez)

| Base | Correctas | Parciales | Incorrectas | "No sé" teniendo el dato | Se abstiene sin respuesta |
|---|---|---|---|---|---|
| Limpia | 48 | 7 | 7 | 6 | 10/10 |
| Sucia | 49 | 9 | 4 | 3 | 10/10 |

Cambian 12 preguntas: 7 a favor de la base sucia y 5 de la limpia. En la base limpia, 5 de
las 7 incorrectas son "no sé"; de las 6 veces que dijo "no sé" teniendo respuesta en el
corpus, en 4 el fragmento correcto estaba entre los 5 recuperados ("los fragmentos hablan de la
Provincia" sobre un documento de la Ciudad).

**Diagnóstico de contexto.** Los chunks limpios tienen en promedio 588 caracteres y los sucios
976: con 5 chunks, el modelo lee casi la mitad en la base limpia. Repreguntando con 8 chunks
las 14 que la base limpia no tuvo correctas: 2 mejoran, 1 empeora, 11 quedan igual. El tamaño
del contexto explica poco.

### Score tipo Jev sobre 100 chunks al azar de cada base

| Base | Media (1 a 5) | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Limpia | 3,14 | 11 | 12 | 0 | 77 | 0 |
| Sucia | 2,94 | 13 | 31 | 1 | 55 | 0 |

Los chunks con menor puntaje de la base sucia son justo el ruido que la limpieza saca: el pie
de página con las redes sociales, el formulario de "¿te fue útil esta página?", una tabla de
códigos sin encabezado. El modelo usa casi solo tres niveles (1, 2 y 4).

**Primera corrida, descartada.** Con la cadena de modelos gratuitos (`runs/rag-cadena.jsonl`)
dio 50 contra 52 correctas, pero cuando un modelo se quedaba sin cuota respondía el siguiente,
y en 49 de las 72 preguntas cada base la respondió un modelo distinto.

## 4. Conclusión

1. **En este corpus, indexar el texto crudo casi no empeora las respuestas: 48 contra 49
   correctas.** La recuperación pierde algo (60 a 57 en el top 5, 46 a 41 en el primer
   lugar), pero el modelo responde igual. No contradice la regla general; la precisa.
2. **Por qué: el desorden de forma no es la basura que daña.** Son documentos públicos de texto
   nativo, sin escaneos. Al texto crudo el dato le sobrevive: el monto, la dirección, el plazo
   (en el lab 11, los dos parsers conservaron el 97 % de los montos, fechas y plazos). bge-m3,
   el re-ranker y un LLM toleran renglones cortados, menús y tablas aplanadas.
3. **Lo que sí cambió respuestas en estos labs es lo que no está en el texto, y eso no lo
   arregla ninguna limpieza.** Son pocos casos (uno por tipo), así que es una pista, no una
   medición: el
   significado que solo está en el color (lab 18: el asistente responde mal con el texto plano
   y con la tabla sin estilo), el dato que el documento no tiene (el emisor, R9 en el lab 16) y el dato que el
   parseo separa de su contexto (la fecha lejos del monto, v07 en el lab 16). Un semáforo útil
   busca eso, no prolijidad.
4. **En la recuperación, la ruta de títulos importa más que limpiar.** Sacarla pierde 4
   preguntas en el top 5 y 8 en el primer lugar: más que pasar a la base sucia, que conserva el
   título del documento. Las respuestas de la base sin ruta no se midieron.
5. **Para comparar bases hay que fijar el modelo.** Con la cadena de free tiers, el ruido de
   cambiar de modelo fue del mismo tamaño que la diferencia que se quería medir.
6. **Un Score barato separa el ruido.** La base sucia tiene casi el triple de chunks en 2
   ("datos sueltos sin saber a qué se refieren") y sus peores chunks son menús y formularios.
   No cambió las respuestas en este corpus. Podría servir para no indexar esos fragmentos;
   filtrar con este puntaje no se probó. Que use solo tres niveles de cinco indica que la rúbrica, o el modelo de 4B, no
   distingue matices: alcanza para filtrar, no para ordenar.
7. **Con el modelo fijo, la mayoría de las incorrectas son "no sé"** (5 de 7 en la limpia, 3
   de 4 en la sucia). En este corpus, pesa más cuánto se anima el modelo con lo que recupera
   que la base.

### Límites
- Corpus público de buena calidad de origen y PDFs de texto. Un corpus con escaneos, tablas
  complejas, versiones viejas y duplicados (lo que sube la gente a diario) puede dar otro
  resultado; este lab no lo prueba.
- 62 preguntas y una corrida: alcanza para descartar un efecto grande, no uno chico.
- La evidencia es casi siempre un monto o una dirección: un dato corto sobrevive al texto
  crudo. Preguntas que necesitan una tabla entera o la relación entre dos datos castigarían
  más a la base sucia.
