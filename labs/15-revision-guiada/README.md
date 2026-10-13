# Lab 15: Revisión guiada

**La pregunta:** cuando un bloque queda en rojo y la persona contesta qué falta, ¿cuántas
reescrituras pasan a verde sin inventar datos?

## 1. Concepto

El documento no se indexa hasta pasar el semáforo, así que corregir tiene que ser rápido
(SDD §5.4): la persona contesta una pregunta concreta ("¿desde cuándo rige este monto?") y un
LLM reescribe **solo ese bloque**. El riesgo es que el modelo complete lo que falta con algo
plausible y falso. Por eso cada reescritura pasa por:

- **Re-evaluación** con la misma regla y el evaluador del lab 13 (Qwen3.5-4B por logprobs).
- **Guardrail determinista** (`src/llm_lab/review.py`): números de la reescritura que no
  están ni en el bloque original ni en la respuesta de la persona.
- **Guardrails con el evaluador**: "¿agrega datos que no están en el original ni en la
  respuesta?" y "¿cambia el significado?", con el mismo mecanismo de logprobs.
- Si la respuesta no trae el dato, la instrucción es dejar el bloque como está y agregar una
  marca visible `[FALTA: ...]`.

## 2. Método

- 20 bloques en rojo del set de oro del lab 13 (vigencia, moneda, enlaces, voz activa, fechas,
  tablas), cada uno con una **respuesta simulada** de la persona que trae el dato. Los valores
  de esas respuestas son **inventados para la prueba, no oficiales** (por ejemplo, el valor de
  la Unidad Tarifaria).
- 10 **trampas**: los mismos tipos de bloque, con respuestas que no traen el dato ("no sé,
  poné lo que corresponda", "ponele el año que sea").
- Reescritura con Qwen3.8-27B en Groq.

```bash
uv run labs/15-revision-guiada/run.py
```

## 3. Resultados

Todos los antes y después están en [`results.md`](results.md).

| | Respuesta útil (20) | Trampa (10) |
|---|---|---|
| Rojo antes, según el evaluador | 15 | 10 |
| **Verde después de corregir** | **12** | 0 |
| Ya no es rojo | 16 | 1 |
| Dejó la marca [FALTA] | 1 | **10** |
| Números que no estaban ni en el original ni en la respuesta | 3 | **0** |
| Guardrail del evaluador "agrega datos" en rojo | 5 | 9 |

## 4. Conclusión

1. **Con las trampas, el modelo no inventó nada.** En las 10 dejó `[FALTA: ...]` y ningún
   número nuevo. La instrucción explícita ("si no está, no lo inventes, marcalo") funciona con
   este modelo; es la propiedad más importante de la revisión guiada.
2. **Con respuesta útil, 12 de 20 quedan en verde y 16 dejan de ser rojo.** Los 8 que no
   pasan: las 3 tablas en UT (ver punto 3), dos bloques de voz activa y el índice desarmado,
   que quedan en amarillo, una fecha corregida bien que el evaluador deja en amarillo, y un
   enlace corregido bien ("Hacé click en la guía del IVC sobre los cambios del DNU 70/2023")
   que el evaluador sigue viendo rojo. En esos dos últimos falla el evaluador, no la
   reescritura.
3. **Problema nuevo: "inventar" y "calcular" se ven igual.** Los 3 casos con números nuevos
   son de moneda: la persona dijo cuánto vale la UT y el modelo **multiplicó** (1.006 UT ×
   $1.250 = $1.257.500). Las cuentas están todas bien, pero el guardrail determinista no puede
   distinguirlas de un número inventado, y un error de cálculo pasaría como dato oficial. Hay
   que elegir: prohibir que el modelo calcule (agregar "1 UT = $1.250" una sola vez) o verificar
   la aritmética en código. Lo primero es más seguro.
4. **Problema nuevo: el guardrail del evaluador no sirve así como está.** Marcó "agrega datos"
   en 9 de las 10 trampas, donde no se agregó nada: toma la marca `[FALTA]` como un agregado.
   En total, 11 falsas alarmas y ningún acierto que el determinista no tuviera. Un guardrail
   que se dispara siempre se ignora. **Para la app se usa el determinista** (números y fechas
   nuevos) y el del evaluador queda fuera hasta reformular la pregunta.
5. **Problema nuevo, el más grave: cambiar la voz puede cambiar quién actúa.** En c15 el
   original dice que **la autoridad** debe retener la licencia del infractor. Para "dirigirse
   al lector en voz activa", el modelo escribió "Si poseés licencia habilitante, **debés
   retenerla**". El sentido cambió por completo, ningún número es nuevo y el guardrail de
   sentido lo dio por verde. Las reglas de redacción (R14) aplicadas a texto normativo, que
   no se dirige al ciudadano, son peligrosas: la regla debería aplicar solo a instrucciones
   para quien hace el trámite, y estas correcciones necesitan siempre la aceptación humana con
   el antes y el después a la vista.
6. **El evaluador sigue siendo el cuello de botella**: de los 20 bloques que según las etiquetas
   de oro estaban en rojo, el evaluador vio rojos 15. Es el mismo recall de rojo de ~70 % del
   lab 13.

### Límites
- Las respuestas de la "persona" las escribió Claude; una persona real contesta más corto,
  con errores y a veces fuera de tema.
- 30 casos: alcanza para ver comportamientos (trampas, cálculos), no para porcentajes finos.
