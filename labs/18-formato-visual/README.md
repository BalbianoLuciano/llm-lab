# Lab 18: Cuando el dato está en el color

**La pregunta:** en una tabla donde algunas filas tienen fondo oscuro y texto rojo y nada
dice qué significa ese formato, ¿se puede detectar antes de indexar, preguntarle a quien subió
el documento y corregirlo? ¿Qué parte necesita un modelo y qué parte no?

## 1. Concepto

Una persona ve que una fila está resaltada y entiende que pasa algo con ese trámite. Después
de extraer el texto, esa fila es igual a las demás. El asistente responde con el dato como si
nada, y quien conoce el documento concluye que "el asistente no sirve" (SDD §2, riesgo 3, y la
regla R1, WCAG 1.4.1 "uso del color").

El laboratorio usa las tres primitivas de Jev (TypeSafe AI), implementadas con un modelo local
por logprobs en `src/llm_lab/system_one.py`, con las mismas formas de pregunta y de respuesta
que la API de Jev:

- **Noul**: ¿es cierto que el formato dice algo que el texto no dice? Devuelve una
  probabilidad.
- **Choice**: dos preguntas. Una, contrastada: el formato es *ninguno*, *decorativo*,
  *explicado* por el texto u *oculto*. La otra, la regla R1 en verde, amarillo o rojo.
- **Score**: de 1 a 5, ¿qué tan bien respondería un asistente con este texto?

Jev no acepta altas nuevas, así que no se probó Jev en sí: se probó la técnica abierta detrás
(lab 13) con Qwen3.5 de 4B y 9B. Cambiar `SystemOne` por el cliente de Jev es tocar una clase.

## 2. Método

- **8 tablas sintéticas** en PDF (`cases.py`), dibujadas con PyMuPDF, con un organismo y
  montos inventados. En 3 el formato dice algo que el texto no dice (filas suspendidas, montos
  que aumentaron, una celda de turno). En 5 no: solo el encabezado oscuro, una leyenda que lo
  explica, un total en negrita, filas alternadas en gris, una columna que ya lo dice.
- Cada tabla se lee de dos formas (`extract.py`):
  - **plain**: filas y celdas, como la da hoy el parser;
  - **styled**: lo mismo, con el estilo escrito al lado ("[fila: fondo oscuro, texto rojo]"),
    sacado de los rellenos vectoriales del PDF y del color de cada fragmento de texto.
- **El flujo completo** sobre el caso principal: detectar, armar la pregunta de la revisión,
  aplicar la respuesta de la persona, re-evaluar y preguntarle al asistente.

```bash
uv run labs/18-formato-visual/run.py --phase detect     # LAB18_MODEL=... para elegir modelo
uv run labs/18-formato-visual/run.py --phase demo
uv run labs/18-formato-visual/run.py --phase report
```

## 3. Resultados

Todo, tabla por tabla, en [`results.md`](results.md). Con el estilo anotado (styled):

| Pregunta | 4B: detecta (de 3) | 4B: falsas alarmas (de 5) | 9B: detecta | 9B: falsas alarmas |
|---|---|---|---|---|
| Noul ≥ 0,5 | 3 | 5 | 3 | 5 |
| Choice contrastado = oculto | 1 | 1 | **2** | **0** |
| Choice R1 = rojo | 3 | 3 | 3 | 3 |

Sin el estilo (plain), **ninguna pregunta detecta ninguno de los 3 casos**, con ningún modelo.

El flujo completo, caso principal (dos filas con fondo oscuro y texto rojo, sin leyenda), con
el 9B:

| Paso | Noul | R1 (Choice) | Score | Lo que responde el asistente a «¿Cuánto sale renovar la licencia y puedo hacerlo esta semana?» |
|---|---|---|---|---|
| Texto plano | 0,35 | verde (0,88) | 3,63 | "Te sale $35.000 y necesitás sacar turno previo" (**mal**) |
| Con el estilo anotado | 0,96 | **rojo (0,82)** | 3,22 | — |
| Corregido | 0,50 | verde (0,82) | 3,88 | "Cuesta $35.000, pero está suspendido hasta el 30/11/2026, así que no podés hacerlo esta semana" (**bien**) |

La pregunta de la revisión se arma con lo que vio el parser, sin LLM: *"Las filas «Renovación»
y «Duplicado» tienen fondo oscuro, texto rojo. ¿Qué indica ese formato?"*. La respuesta de la
persona ("Suspendido hasta el 30/11/2026 por cambio de sistema") se agrega como una columna
nueva, también sin LLM.

## 4. Conclusión

1. **Si el parser no anota el formato, ningún evaluador lo ve.** Con texto plano, las 8 tablas
   salen verdes y el asistente responde mal. El primer arreglo es del parser: PyMuPDF da el
   color de cada fragmento de texto y los rellenos de la página; con eso el estilo se escribe
   como texto. No cuesta nada y no usa modelos.
2. **Saber si hay formato distinto es código; saber si el texto lo explica es del modelo.** Qué
   filas tienen otro fondo o color se calcula exacto. La pregunta difícil es si la página dice
   con palabras qué significa, y ahí entra el modelo.
3. **Noul con un modelo chico no sirve: dice "verdadero" a todo.** Con estilo, 0,93 a 0,98 en
   las 8 tablas, también en las decorativas. Es sesgo de aquiescencia: el modelo tiende a
   aceptar la afirmación. Es exactamente el problema que promete resolver un modelo entrenado
   para dar probabilidades calibradas como Jev; no lo pudimos verificar.
4. **Un Choice con opciones contrastadas funciona mejor que la pregunta de sí o no.** Con el
   9B, *oculto* detecta 2 de 3 sin ninguna falsa alarma, y cuando el texto lo explica la
   confianza en *explicado* es alta (0,73 y 0,87) contra 0,47 a 0,57 en el resto. Con
   confianza baja, el bloque queda en amarillo y se le pregunta a la persona: preguntar cuesta
   menos que equivocarse.
5. **La regla R1 como Choice detecta todo pero exagera.** 3 de 3, y 3 falsas alarmas de 5:
   pone en rojo también la tabla con leyenda y la de filas alternadas. Para el semáforo, R1
   sola pintaría de rojo tablas que están bien, que es justo lo que no hay que hacer con quien
   sube muchos documentos.
6. **La corrección no necesita un LLM.** La pregunta sale de lo que vio el parser y la
   respuesta se escribe como una columna. Un solo dato de la persona cambió la respuesta del
   asistente de incorrecta a correcta.

### Límites
- 8 tablas sintéticas, hechas por quien escribió las preguntas: sirven para ver el mecanismo,
  no para porcentajes. Hace falta probarlo con documentos reales.
- La extracción de filas por línea de base alcanza para estas tablas; en documentos reales las
  celdas saldrían de la estructura de tablas de Docling, y la búsqueda del estilo es la misma.
- El flujo completo es un solo caso y una sola pregunta.
- Los umbrales de confianza se miraron sobre las mismas 8 tablas.
