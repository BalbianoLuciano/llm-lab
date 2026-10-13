# Lab 11: Parseo

**La pregunta:** ¿cuánto de la estructura de un documento real (títulos, listas, tablas,
enlaces) sobrevive al parseo, y qué se pierde según el formato? ¿Alcanza con heurísticas
hechas a mano o hace falta un modelo de layout como el de Docling?

Todo lo que viene después se apoya en esto. El semáforo evalúa **bloques**, el chunking corta
**por estructura** y la revisión guiada salta **de bloque en bloque**. Si el parseo confunde
una lista con una tabla o pierde un título, el resto hereda el error.

---

## 1. Concepto

### Un PDF no tiene párrafos
Un PDF es una lista de instrucciones de dibujo: "poné estas letras, en esta fuente, en esta
posición". No dice qué es título, qué es lista ni qué es tabla. Todo eso hay que **inferirlo**
del aspecto: el tamaño de la letra, la negrita, la sangría, la alineación en columnas.

HTML y Word son lo opuesto: la estructura viene escrita en etiquetas (`<h2>`, `<li>`,
`<table>`). El problema ahí es otro: separar el contenido del resto de la página (menú,
pie, "¿Te fue útil esta página?").

### El bloque
La salida del parseo es una lista ordenada de **bloques** (`src/llm_lab/blocks.py`):

| Campo | Qué guarda |
|---|---|
| `kind` | `heading`, `paragraph`, `list_item` o `table` |
| `text` | el texto del bloque (vacío en tablas) |
| `level` | nivel del título: 1 es el más alto |
| `rows` | las filas de la tabla; la primera es el encabezado |
| `links` | texto y URL de cada enlace |
| `path` | los títulos que contienen al bloque: `["Requisitos", "Documentación"]` |
| `page` | página de origen (solo PDF) |

El `path` es lo que después permite que un chunk diga de qué sección viene, y que una regla
del semáforo sepa si un párrafo está bajo "Requisitos" o bajo "Costos".

### Dos maneras de inferir la estructura de un PDF
- **Heurísticas** (`manual_parser.py`, con PyMuPDF): el tamaño de letra más frecuente es el
  cuerpo; lo que es más grande, o está en negrita y es corto, es título; lo que empieza con
  viñeta o número es ítem; las líneas que se repiten arriba o abajo en muchas páginas son
  encabezado o pie. Las tablas se detectan por líneas y alineación.
- **Modelo de layout** (`docling_parser.py`): Docling pasa cada página por un detector de
  objetos entrenado para reconocer regiones (título, texto, lista, tabla, encabezado de
  página) y otro modelo para reconstruir la grilla de las tablas. Corre en la GPU de la Mac
  (MPS).

## 2. Método

- **Corpus:** los 49 documentos de `corpus/urls.tsv` (29 PDF, 15 HTML, 4 DOC, 1 DOCX).
- **Dos parsers, mismo formato de salida:**
  - `manual_parser.py`: PyMuPDF para PDF, BeautifulSoup para HTML; DOC y DOCX se pasan a HTML
    con `textutil` (viene con macOS).
  - `docling_parser.py`: Docling 2.138 sin OCR, con la jerarquía de títulos activada (viene
    apagada y entonces todos los títulos salen con nivel 1). Los `.doc` se pasan a `.docx`.
  - Los dos parten del mismo HTML limpio (`html_main.py`: se queda con `<main>` y descarta
    menú, pie y formularios), así la comparación mide estructura y no limpieza de la página.
- **Set de oro** (`gold.json`): 6 documentos etiquetados a mano **mirando el original** (las
  páginas del PDF como imagen, el HTML como texto renderizado), no la salida de un parser.
  Cubren los tres formatos: un PDF de una página con tabla, un instructivo de 9 páginas con
  diseño, una resolución, dos páginas web y un formulario de Word.
- **Métricas:** recall y precisión de títulos, ítems de lista reconocidos como ítem, tablas
  encontradas y con todas sus filas, tablas de más, enlaces con su URL, datos clave (montos,
  fechas, plazos) presentes en el texto, ruido de la web que se coló y encabezados de página
  repetidos. La comparación ignora mayúsculas, tildes y puntuación.

```bash
uv run labs/11-parseo/run.py          # los dos parsers sobre todo el corpus
uv run labs/11-parseo/evaluate.py     # compara contra el set de oro y escribe results.md
```

## 3. Resultados

Los números completos, documento por documento, están en [`results.md`](results.md).

Corrida del 2026-10-12, set de oro de 6 documentos:

| Métrica | A mano | Docling |
|---|---|---|
| Títulos encontrados (recall) | 66 % | 63 % |
| Títulos correctos (precisión) | 83 % | **88 %** |
| Ítems de lista reconocidos | 86 % | **100 %** |
| Tablas con todas sus filas | 1 de 2 | **2 de 2** |
| Tablas de más | 3 | **1** |
| Enlaces con su URL | 90 % | **100 %** |
| Datos clave presentes | 97 % | 97 % |
| Encabezados de página repetidos | **2** | 12 |

Todo el corpus:

| | A mano | Docling |
|---|---|---|
| Tiempo total | **86 s** | 1.491 s |
| Segundos por página PDF (mediana) | **0,06** | 0,40 |
| Anexo de 269 páginas con tablas | **33 s** | 1.268 s (21 min) |

### Dónde gana cada uno
- **En PDF con diseño gana Docling.** En el instructivo de ARBA encuentra los 9 títulos y
  los 17 ítems; el parser a mano encuentra 6 y 12.
- **En HTML empatan.** En 12 de las 15 páginas los dos dan exactamente la misma cantidad de
  bloques. Con HTML limpio no hay nada que inferir: `<h2>` es título y `<li>` es ítem.
- **En Word gana el parser a mano**, por una sola regla: un párrafo entero en negrita y
  corto es un título. Docling no los reconoce y el formulario de SUBE queda sin títulos.
- **Encabezados de página: gana el parser a mano.** Docling marca como encabezado lo que
  el modelo reconoce como tal, pero las bandas de diseño (el título del trámite repetido arriba
  de cada página) las toma como títulos. La regla "si se repite en la mitad de las páginas, es
  encabezado" las saca casi todas.

### Lo que se aprendió en el camino
Cada hallazgo salió de una medición que dio mal, no de leer documentación:

1. **PyMuPDF ve las listas con viñetas como tablas.** `find_tables()` encuentra dos columnas
   alineadas (viñeta | texto) y arma una tabla. En el set de oro detectó 10 tablas y 8 eran
   falsas, casi todas listas. La regla "si la primera columna son solo viñetas, es una lista",
   junto con la del punto 2, bajó los ítems perdidos de 15 a 5 y las tablas falsas de 8 a 3.
2. **La viñeta puede venir sola.** En el PDF de ARBA cada `●` es una línea aparte, en otra
   fuente. Una regex que espera viñeta, espacio y texto no la ve nunca.
3. **Docling parte el texto inline en pedazos.** En HTML, cada negrita, enlace o coma es un
   ítem hijo aparte, y los ítems de lista quedan con el texto vacío y el contenido en un
   `InlineGroup`. Leyendo solo el texto de cada ítem, Docling reconocía 1 ítem de 9 en la página
   de aranceles. Recorriendo el árbol, 9 de 9.
4. **Docling no limpia páginas web.** Sin el paso de `html_main.py`, 6 de 8 marcas de ruido
   (menú, teléfonos útiles, "¿Te fue útil?") quedaban en el texto y la precisión de títulos
   bajaba a 65 %.
5. **Importar PyMuPDF en el mismo proceso que Docling lo vuelve unas 50 veces más lento.**
   Un PDF de 14 páginas tardó 459 s con `import pymupdf` y 9 s sin él. No se diagnosticó la
   causa; la solución fue correr cada parser en su propio proceso (`run.py`).
6. **El contenido escondido también es contenido.** En la página del Registro Civil, tres
   secciones están dentro de botones de acordeón. La primera versión descartaba los `<button>`
   como ruido y perdía esas secciones.
7. **Las tablas grandes cuestan caro en Docling.** El modelo de tablas corre página por página:
   el anexo arancelario (269 páginas, casi todas con tablas) tardó 21 minutos.

## 4. Conclusión

1. **Docling para PDF, reglas propias alrededor.** En los PDF con diseño (la mayoría del
   corpus) el modelo de layout reconoce listas, tablas y títulos que las heurísticas pierden.
   Pero no alcanza solo: hacen falta el filtro de encabezados repetidos y la regla de párrafo
   en negrita, que son baratos y los toma de la versión a mano.
2. **Para HTML no hace falta un modelo.** BeautifulSoup más una buena limpieza de la página da
   lo mismo en milisegundos. Lo difícil del HTML es la limpieza, no la estructura.
3. **El costo importa para la ingesta.** 0,4 s por página está bien para documentos de
   trámites, pero un anexo de 269 páginas tarda 21 minutos. La app (lab 16) va a necesitar
   procesar en segundo plano y mostrar el avance.
4. **Los datos sobreviven casi siempre; la estructura no.** Los dos parsers conservan el 97 %
   de los montos, fechas y plazos. Lo que se pierde es saber si un monto estaba en una tabla o
   en un párrafo, y bajo qué título. Eso es lo que necesitan el semáforo y el chunking.
5. **Para el pipeline:** Docling para PDF; parser propio para HTML y para Word (DOC y DOCX
   pasados por `textutil`), y en todos los casos el filtro de encabezados repetidos. Esa
   combinación se arma en `src/llm_lab/` cuando la use el lab 03 (chunking).

### Encontrado después, usando el corpus en los labs 02 y 03
- **Los comentarios HTML se colaban como texto.** BeautifulSoup trata `<!-- ... -->` como un
  string más; el parser a mano no los filtraba, y aparecían cosas como `.entry-meta` o un
  `<script>` entero comentado ("MODAL NO TOCAR"). El set de oro no lo detectó porque esas
  páginas no estaban en él. Corregido en `manual_parser.py`; las métricas no cambian.
- **Docling corta algunas resoluciones renglón por renglón.** Un monto y su fecha de vigencia
  quedaban en bloques distintos. `src/llm_lab/corpus.py` vuelve a unir dos párrafos seguidos
  cuando el primero no cierra la oración y el segundo empieza en minúscula; quedan sin unir
  los cortes que siguen en mayúscula y los que cruzan un salto de página con el membrete en
  el medio.
- **El calendario de vencimientos de ARBA no sirve como texto**: es una grilla de días y se
  parsea como una lista de números sueltos. Necesitaría un parser propio o leerse como imagen.

### Límites de esta medición
- El set de oro tiene 6 documentos. Alcanza para ver diferencias grandes (17 de 17 ítems
  contra 12 de 17), no para distinguir 63 % de 66 %.
- Las reglas del parser a mano se ajustaron mirando ese mismo set. Son reglas generales
  (viñetas, negrita, repetición), pero un set de oro más grande y separado las validaría mejor.
- El orden de lectura en páginas de dos columnas no se midió. El corpus casi no las tiene.
