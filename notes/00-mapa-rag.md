# Mapa del RAG: de un documento a una respuesta con citas

Una página para ubicar cada pieza antes de construirla. Cada sección dice qué es, qué
decisión hay que tomar, qué sale mal y en qué lab se construye y se mide.

**RAG** (*Retrieval-Augmented Generation*): en vez de esperar que el modelo "sepa" la
respuesta, se **busca** primero el pedazo de documento que la contiene y se le pasa al modelo
junto con la pregunta. El modelo pasa de recordar a leer.

```
INDEXACIÓN (una vez por documento)                CONSULTA (cada pregunta)

archivo                                           pregunta
  │ 1. parseo                                       │ 6. embedding de la pregunta
  ▼                                                 ▼
bloques (títulos, párrafos, tablas)               vector de la pregunta
  │ [semáforo: evaluar y corregir]                  │ 7. búsqueda (+ filtros)
  │ 2. chunking                                     ▼
  ▼                                               top-k chunks candidatos
chunks (pedazos de ~300-800 tokens + metadatos)     │ 8. re-ranking
  │ 3. embeddings                                   ▼
  ▼                                               top-n chunks relevantes
vectores (listas de ~1000 números)                  │ 9. generación
  │ 4. indexación                                   ▼
  ▼                                               respuesta con citas
base vectorial ─────────────────────────────────►   │ 10. evaluación
```

---

## 1. Parseo: del archivo a bloques
- **Qué es**: leer PDF, DOCX, HTML o MD y quedarse con el texto **y su estructura**: qué es
  título, qué es tabla, en qué sección está cada párrafo.
- **Por qué importa**: un PDF no tiene "párrafos". Tiene letras posicionadas en una página.
  Reconstruir el orden de lectura, las tablas y los títulos es un problema en sí mismo.
- **Qué sale mal**: tablas que se convierten en sopa de números, columnas mezcladas, texto
  en color que pierde su énfasis, encabezados y pies de página repetidos en cada chunk.
- **Lab**: 11.

## 2. Chunking: de bloques a pedazos recuperables
- **Qué es**: partir el documento en pedazos (*chunks*). Cada chunk es la unidad que se
  busca y se le pasa al modelo.
- **Por qué no indexar el documento entero**: un vector resume un texto entero en una sola
  "dirección". Un documento de 20 páginas habla de muchas cosas y su vector no se parece a
  ninguna pregunta concreta. Un chunk chico habla de una sola cosa.
- **Las decisiones**:
  - **Tamaño**: chico es preciso pero pierde contexto; grande tiene contexto pero diluye el
    significado y ocupa más lugar en el prompt.
  - **Solapamiento**: repetir el final de un chunk al principio del siguiente, para no partir
    una idea al medio.
  - **Dónde cortar**: por cantidad de tokens (simple), por oraciones o por la estructura del
    documento (sección, tabla). Nosotros cortamos por estructura, porque ya tenemos bloques.
  - **Qué agregar**: cada chunk lleva su **ruta de títulos** ("Licencia > Renovación >
    Aranceles") pegada adelante. Así "el arancel es de $ 18.500" sabe de qué trámite habla.
  - **Metadatos**: documento, versión, página, sección, permisos. Sirven para filtrar y citar.
- **Qué sale mal**: una tabla partida al medio, una respuesta repartida en dos chunks, chunks
  que dicen "ver arriba".
- **Lab**: 03 (tamaño y solapamiento, medido).

## 3. Embeddings: de texto a vectores
- **Qué es**: un modelo (distinto del LLM que genera) que convierte un texto en un vector de,
  por ejemplo, 1024 números. Textos con significado parecido quedan cerca en ese espacio:
  "¿cuánto sale renovar el registro?" queda cerca de "arancel de renovación de la licencia de
  conducir", aunque no compartan palabras.
- **Cómo se mide "cerca"**: similitud coseno (el ángulo entre los vectores) o producto
  interno. Con vectores normalizados son lo mismo.
- **Las decisiones**: qué modelo (tiene que ser multilingüe para español), qué dimensión, y
  si se agregan vectores **dispersos** (tipo palabras clave) además de los densos.
- **Qué sale mal**: números, siglas y nombres propios ("CIT", "ARBA", "F.931") se representan
  mal en vectores densos. Por eso existe la búsqueda híbrida.
- **Lab**: 04.

## 4. Indexación: la base vectorial
- **Qué es**: guardar millones de vectores de forma que encontrar "los 10 más cercanos" no
  requiera comparar contra todos.
- **Cómo funciona**: la búsqueda exacta compara contra todos (O(n)) y es lenta a escala. Los
  índices **ANN** (*approximate nearest neighbors*) como **HNSW** arman un grafo de vecinos
  por capas y navegan por él: mucho más rápido, a cambio de perder algún vecino de vez en
  cuando (recall menor a 100 %).
- **Además del vector**: cada punto guarda un *payload* (los metadatos del chunk). Filtrar
  por payload **durante** la búsqueda (por ejemplo, solo chunks que el usuario puede ver) es
  lo que distingue a una base vectorial de un array de numpy.
- **Lab**: 12 (exacto con numpy → HNSW propio → Qdrant).

## 5. El semáforo (lo propio de este proyecto)
- Se mete **entre el parseo y el chunking**: si un bloque incumple una regla bloqueante, el
  documento no se indexa hasta corregirlo. La hipótesis es que indexar contenido mejor
  escrito mejora todo lo que viene después.
- **Labs**: 13, 14 y 15.

## 6–7. Búsqueda: de la pregunta a los chunks candidatos
- La pregunta se convierte en vector **con el mismo modelo de embeddings** y se buscan los
  *k* chunks más cercanos.
- **Búsqueda híbrida**: se combina la búsqueda por vectores (significado) con una por
  palabras (BM25: frecuencia de términos). Una encuentra "cuánto sale" ≈ "arancel" y la otra
  encuentra "F.931" exacto. Los dos rankings se fusionan (por ejemplo con RRF, *reciprocal
  rank fusion*).
- **Filtros**: permisos, tipo de documento, vigencia. Van en la consulta a la base, nunca en
  el prompt.
- **Labs**: 04 y 12.

## 8. Re-ranking
- **Qué es**: un segundo modelo (*cross-encoder*) que lee la pregunta y cada chunk candidato
  **juntos** y les pone un puntaje de relevancia. Es mucho más preciso que comparar vectores,
  pero también más lento, por eso solo se aplica a los top-k (por ejemplo 30) para quedarse
  con los top-n (por ejemplo 5).
- **Por qué funciona mejor**: el embedding resume pregunta y chunk por separado; el
  cross-encoder ve las dos cosas a la vez y puede notar que el chunk habla del trámite
  correcto pero del año equivocado.
- **Lab**: 05.

## 9. Generación
- El prompt final tiene: instrucciones (respondé solo con lo que dicen los fragmentos, citá
  la fuente, si no está decí que no sabés), los top-n chunks con un identificador, y la
  pregunta.
- **Qué sale mal**: el modelo mezcla lo que leyó con lo que "sabe", cita un chunk que no dice
  eso, o contesta aunque los chunks no tengan la respuesta.
- **Labs**: 06 (fidelidad y citas) y 07 (cuándo decir "no sé").

## 10. Evaluación
Un RAG se evalúa por partes, porque si la respuesta está mal hay que saber **dónde** falló:

| Etapa | Pregunta | Métrica |
|---|---|---|
| Recuperación | ¿El chunk con la respuesta está entre los recuperados? | recall@k, MRR |
| Re-ranking | ¿Quedó arriba? | MRR, nDCG |
| Generación | ¿Lo que dice la respuesta está respaldado por los chunks citados? | fidelidad |
| Generación | ¿Responde lo que se preguntó? | relevancia, exactitud contra la respuesta esperada |
| Sistema | ¿Dice "no sé" cuando la información no está? | tasa de abstención correcta |

Todo se mide sobre un **set fijo de preguntas con su respuesta y su pasaje correcto**, que se
arma una vez y se reusa en todos los labs. Sin ese set, cualquier cambio "se ve mejor" y no
se sabe si lo es.
- **Labs**: 06, 07 y 10.
