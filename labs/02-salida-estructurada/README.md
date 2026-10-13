# Lab 02: Salida estructurada

**La pregunta:** cuando le pedimos JSON a un modelo, ¿cuántas respuestas cumplen el esquema,
con y sin validación, y qué pasa cuando no?

La tarea es real y la necesita el semáforo (reglas R6 y R8): de un pasaje del corpus, sacar
cada monto de dinero con su concepto, su moneda y la fecha desde la que rige.

## 1. Concepto

Un modelo genera texto, token a token. Que ese texto sea un JSON válido y además tenga los
campos y tipos que esperamos no está garantizado. Hay cuatro formas de pedirlo, de menos a más
control:

| Modo | Qué hace | Qué garantiza |
|---|---|---|
| `prompt` | describe el formato en el prompt | nada |
| `json_object` | "modo JSON" del proveedor | que sea JSON válido, no que tenga los campos |
| `json_schema` | *structured outputs*: el proveedor restringe la generación al esquema | que cumpla el esquema que el proveedor acepta |
| `retry` | `prompt` + validación con Pydantic; si falla, se le devuelve el error al modelo (hasta 2 veces) | que cumpla el esquema de Pydantic, o un error explícito |

El esquema (`run.py`): una lista de montos con `concept`, `amount` (número), `currency`
(`ARS`, `USD`, `EUR` o null) y `effective_from` (fecha o null).

## 2. Método

- **Set de oro** (`gold.jsonl`): 26 pasajes del corpus, 20 con montos (34 montos en total) y 6
  sin montos que tienen números que no son dinero (porcentajes, años, teléfonos). Etiquetados a
  mano: monto, moneda y fecha de vigencia de cada uno.
- Cada pasaje es un **bloque más los anteriores que hagan falta** y su ruta de títulos: en la
  página de aranceles, el concepto y el monto están en bloques distintos.
- Tres modelos gratuitos: Qwen3.8-27B y gpt-oss-120b en Groq, GLM-5.3 en NVIDIA. Gemini
  estaba previsto, pero su tier gratuito permite **20 pedidos por día** y se agotó en la
  llamada 25.
- Las fallas de red y los límites de uso (429) no cuentan como resultado: el script las
  reintenta en la corrida siguiente.

```bash
uv run labs/02-salida-estructurada/run.py
```

## 3. Resultados

Números completos en [`results.md`](results.md).

| Modelo | prompt | json_object | json_schema | retry | Latencia p50 |
|---|---|---|---|---|---|
| Qwen3.8-27B (Groq) | 26/26 | 26/26 | 26/26 | 26/26 | 0,5 s |
| gpt-oss-120b (Groq) | 26/26 | 26/26 | 26/26 | 26/26 | 0,7–0,9 s |
| GLM-5.3 (NVIDIA) | **24/26** | 26/26 | **22/26** | 26/26 | 11–26 s |

(respuestas que cumplen el esquema de Pydantic)

Cuando el JSON es válido, la extracción es casi perfecta: Qwen y gpt-oss encuentran los 34
montos en todos los modos, sin inventar ninguno en los pasajes sin montos, con la moneda bien
en todos y la vigencia bien en 30 de 30. El único error de lectura: gpt-oss, en `json_object`,
leyó "$ 108.504-" como **108,504** (tomó el punto de miles por coma decimal): un monto mil veces
menor, con un formato perfectamente válido.

## 4. Conclusión

1. **Con modelos buenos, el formato ya no es el problema.** Qwen y gpt-oss cumplen el esquema
   el 100 % de las veces aun sin ninguna ayuda. Pero un modelo distinto (GLM) envuelve la
   respuesta en un bloque de código markdown, con ```json, y rompe el parseo estricto en 2 de
   26. **`retry` es la única opción que funciona igual con los tres**, y casi no cuesta: en
   promedio hizo falta un solo intento.
2. **`json_schema` no es lo que parece.** Los proveedores aceptan un subconjunto de JSON
   Schema: el modo estricto no admite `format: date`. Hubo que sacarlo, y entonces el
   esquema que el proveedor obliga a cumplir dejó de ser el que valida Pydantic. GLM devolvió
   "2026-04" y "diciembre 2025" en el campo fecha: JSON válido para el proveedor, inválido
   para nosotros.
3. **Problema para el semáforo: hay fechas que no son días.** Esas "fechas inválidas" no
   eran errores del modelo: el corpus dice "a partir de abril de 2026" o "a diciembre 2025".
   Un campo `date` obliga a inventar el día. El esquema de vigencia de R8 tiene que aceptar
   fechas parciales (año y mes) en vez de forzar una fecha completa.
4. **Un JSON válido puede tener un dato mil veces mal.** El separador de miles argentino (punto)
   se confunde con el decimal. Ningún esquema lo detecta: hace falta una validación de
   contenido (por ejemplo, que el número aparezca en el texto con su formato original).
5. **El costo de la elección es la latencia.** Groq responde en medio segundo; GLM en NVIDIA,
   entre 11 y 26 segundos, porque razona antes de contestar. Para el compilador de reglas
   (lab 14) y la reescritura (lab 15) se usa Qwen en Groq con validación y reintento.
6. **Los límites gratuitos condicionan el diseño.** Gemini permite 20 pedidos por día: sirve
   solo como último respaldo. Quedó al final de la cadena en `src/llm_lab/models.py`.

### Límites
- Otra vez efecto techo: 26 pasajes cortos y bien escritos. Lo interesante apareció en los
  bordes (fechas parciales, montos en "UT"), no en el promedio.
- Las etiquetas de oro las puso Claude leyendo cada pasaje, no una persona.
