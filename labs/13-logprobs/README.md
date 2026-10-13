# Lab 13: Decisiones por logprobs

**La pregunta:** para decidir si un bloque cumple una regla (verde, amarillo o rojo), ¿conviene
leer las probabilidades de los tokens A/B/C en una sola pasada, o pedirle al modelo un JSON?
¿Cuál acierta más, cuál está mejor calibrado, cuánto ayuda el *temperature scaling*?

## 1. Concepto

Antes de escribir cada token, un LLM calcula una probabilidad para **todos** los tokens
posibles. Si la pregunta termina en "Respondé A, B o C", se puede leer la probabilidad de esos
tres tokens en la primera posición de la respuesta y **no generar nada** (`src/llm_lab/evaluator.py`,
`LogprobsEvaluator`, con `mlx-lm` en la Mac). Se obtiene:

- una respuesta que siempre es una de las opciones (no hay JSON roto ni texto de más);
- una distribución de probabilidad, de la que sale la **confianza**;
- una sola pasada hacia adelante.

**Calibración.** Una confianza sirve si es honesta: de las veces que dice 90 %, acierta 90 %. Se
mide con el **ECE** (error de calibración esperado: la diferencia promedio entre la confianza y
el acierto real, por tramos de confianza). El *temperature scaling* divide los logits por un T
ajustado sobre datos etiquetados: T > 1 baja la confianza, T < 1 la sube.

**Sesgo de posición.** Un modelo que responde con una letra puede preferir una posición ("A")
más allá del contenido. El remedio: preguntar dos veces, con las opciones en orden normal e
invertido, y promediar (como `permutations=2` de open-alternative-jev).

En el semáforo la confianza importa: con confianza baja, el bloque queda en **amarillo dudoso**
en vez de verde (SDD §5.3).

## 2. Método

- **Set de oro** (`gold.jsonl`): 115 pares (bloque, regla) del corpus, para 6 reglas que se
  pueden juzgar mirando un bloque: R2 tablas, R3 enlaces, R6 moneda, R7 fechas, R8 vigencia,
  R14 voz activa. Muestreados al azar con semilla fija (máximo 3 bloques por documento) y
  etiquetados con el criterio escrito en `rules/reference.yaml` y una nota por caso.
  **Las etiquetas las puso Claude, no una persona.** Distribución: 43 verdes, 43 amarillos, 29
  rojos.
- **Estado** que ve el evaluador: título del documento, ruta de títulos, bloque anterior y
  siguiente recortados, y el bloque marcado.
- **Evaluadores**:
  - Qwen3.5-4B y Qwen3.5-9B en 4 bits con mlx-lm, por logprobs, con uno y dos órdenes.
  - **Qwen3.5-9B pidiéndole JSON** `{"opcion", "confianza"}` (el mismo modelo, la otra forma de
    preguntar): la comparación justa.
  - Estaban previstos dos jueces por API (Qwen3.8-27B y gpt-oss) y la librería
    open-alternative-jev (`so1`). Los de API no llegaron a correr por la cuota diaria de Groq.
    `so1` con el backend de Hugging Face hizo **segfault dos veces** al cargar Qwen3.5-4B sin
    cuantizar en la GPU de la Mac, probablemente por memoria (había otro modelo cargado).
- Calibración con validación cruzada de dos mitades: el T de cada mitad se ajusta en la otra.

```bash
uv run labs/13-logprobs/run.py
```

## 3. Resultados

Números completos, por regla y matriz de confusión en [`results.md`](results.md).

| Evaluador | Accuracy | Recall de rojo | Rojos como verde | ECE | ECE con T | Confianza media | Latencia |
|---|---|---|---|---|---|---|---|
| 4B, orden dado | 65 % | 69 % | 1 | 0,075 | 0,052 | 0,73 | 4,8 s |
| **4B, dos órdenes** | 70 % | 69 % | 2 | 0,057 | 0,071 | 0,67 | 4,8 s |
| 9B, orden dado | 66 % | 72 % | 2 | 0,048 | **0,017** | 0,71 | 6,2 s |
| 9B, dos órdenes | 70 % | 72 % | 2 | **0,034** | 0,039 | 0,68 | 6,2 s |
| 9B, pidiendo JSON | **74 %** | 72 % | 2 | **0,242** | — | **0,98** | 4,6 s |

(latencia por evaluación en la Mac, con las dos pasadas en los de "dos órdenes")

Por regla, lo más difícil son las tablas (R2: 13–16 de 26) y la voz activa con el 4B. Lo más
fácil, la vigencia (R8: 17–20 de 21).

## 4. Conclusión

1. **Pedir JSON acierta un poco más, pero su confianza no sirve.** El 9B con JSON acierta 74 %
   contra 70 % por logprobs, pero dice "confianza 0,98" casi siempre y acierta 74 %: un ECE de
   0,24. No se puede usar para el amarillo dudoso. Por logprobs, el ECE es de 0,03 a 0,07: la
   confianza dice algo real.
2. **Dos órdenes suman 4 o 5 puntos de accuracy.** El sesgo de posición es real, sobre todo en
   el 4B (voz activa: de 8 a 13 aciertos de 18). Promediar los dos órdenes también mejora la
   calibración.
3. **El 4B con dos órdenes rinde como el 9B.** Por eso la app y los labs 14–16 usan el 4B: la
   mitad de memoria y un 20 % más rápido.
4. **El *temperature scaling* ayuda con un solo orden y no con dos.** Con un orden baja el ECE
   del 9B de 0,048 a 0,017. Con dos, ya está calibrado: ajustar T sobre 57 ejemplos agrega más
   ruido que corrección.
5. **Problema para el semáforo: 70 % no alcanza para bloquear documentos.** Un 28 % de los rojos
   no se detecta y 2 rojos pasan como verdes. Para las reglas bloqueantes hace falta más (un
   modelo más grande, ejemplos en el prompt o reglas más acotadas), o tratar el amarillo como
   "a revisar" y no como "aprobado".
6. **Problema que no es del evaluador: algunos rojos son del parser.** De los 8 rojos de tablas
   (R2), la mitad son índices o filas que el parseo desarmó, no tablas mal hechas por el
   organismo. El semáforo no puede distinguirlos, y la revisión le pediría a la persona que
   arregle algo que en el original estaba bien.

### Límites
- 115 casos etiquetados por un solo anotador (Claude): faltan una segunda opinión y personas
  reales.
- Las seis reglas evaluadas son las que se pueden juzgar en un bloque; las de documento entero
  (R5, R9, R10) quedan para otra medición.
