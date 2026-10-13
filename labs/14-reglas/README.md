# Lab 14: Reglas en lenguaje natural

**La pregunta:** una persona escribe una regla de calidad como la diría ("los links tienen que
decir a dónde llevan"). ¿Cuántas compila bien un LLM, sin intervención humana, a una regla
tipada que el semáforo pueda evaluar? ¿Detecta las que son demasiado vagas para evaluarse?

## 1. Concepto

Las reglas son **datos, no código** (SDD §5.2). Un compilador (`src/llm_lab/compiler.py`)
convierte el texto en una `Rule` de Pydantic (`src/llm_lab/rules.py`):

- `kind`: `semantic` (la evalúa un modelo) o `deterministic` (se chequea con código).
- `scope`: cada bloque o el documento entero. `applies_to`: qué tipos de bloque.
- `question` y `levels`: la pregunta al evaluador y qué significa verde, amarillo y rojo (es
  también la explicación que ve la persona en la revisión).
- `blocking`, `source` (la norma de la que sale) y dos `examples`.

Si la regla es vaga ("que sea claro"), el compilador no tiene que inventar un criterio: devuelve
`ambiguous` y pide un ejemplo o un criterio concreto. Usa salida JSON validada con Pydantic y
reintento con el error (lo que funcionó en el lab 02).

## 2. Método

- **30 reglas en lenguaje natural** (`rules_nl.jsonl`), redactadas como las escribiría alguien
  del organismo: las 14 del SDD, 10 nuevas y 6 vagas a propósito.
- **Compilación de referencia** de las 24 compilables, escrita a mano: R1–R14 en
  `rules/reference.yaml` (la que usa el semáforo) y las otras 10 en `extra_reference.yaml`.
- Se compara campo por campo: `kind`, `scope`, `blocking`, `applies_to` (índice de Jaccard
  entre conjuntos), y si `source` cita la misma norma (mismo código: 1.4.1, 4217, 24495-1).
- Tres modelos gratuitos: Qwen3.8-27B y gpt-oss-120b en Groq, GLM-5.3 en NVIDIA.

```bash
uv run labs/14-reglas/run.py
```

## 3. Resultados

Números completos y cada diferencia con la referencia en [`results.md`](results.md).

| Modelo | Esquema válido | Vagas detectadas | Buenas marcadas como vagas | `kind` | `scope` | `blocking` | Norma | Bien sin editar |
|---|---|---|---|---|---|---|---|---|
| **Qwen3.8-27B** | 30/30 | **6/6** | 0/24 | 96 % | 92 % | 100 % | 100 % | **14/24** |
| gpt-oss-120b | 30/30 | 6/6 | 0/24 | **46 %** | 92 % | 100 % | 100 % | 2/24 |
| GLM-5.3 (parcial) | 12/12 | 6/6 | 0/6 | 100 % | 83 % | 100 % | 100 % | 4/6 |

GLM quedó en 12 de 30: NVIDIA empezó a responder con 429 a los pedidos largos y se cortó la
corrida para no frenar el resto.

## 4. Conclusión

1. **Detectar reglas vagas funciona.** Los tres modelos devolvieron `ambiguous` en las 6 vagas
   ("que sea claro", "evitar textos aburridos", "que no tenga errores"), con una pregunta útil
   ("¿a qué tipo de errores te referís?"), y ninguno marcó como vaga una regla buena.
2. **El formato tampoco es problema**: 100 % de esquemas válidos al primer intento.
3. **Lo que falla es el criterio, no la sintaxis.** Qwen compila 14 de 24 reglas exactamente
   como la referencia. Los desvíos son de interpretación: reglas que aplican a un bloque las
   pone a nivel documento (pasos numerados, horarios), deja afuera las tablas de una regla de
   enlaces. `blocking` y la norma salen siempre bien, porque la persona los dice.
4. **Problema nuevo: "determinista" no tiene límite.** gpt-oss marca como `deterministic` todo
   lo que en teoría se podría chequear con código: siglas, fechas, "los requisitos van antes
   que los pasos", tablas sin encabezado. Qwen hace lo mismo con las fechas. Pero una regla
   determinista necesita que alguien escriba el código, y el compilador no lo genera: en la app
   esas reglas quedarían sin evaluar. Hay que cerrar el concepto: `deterministic` solo para un
   catálogo de chequeos implementados (contar palabras, porcentaje de mayúsculas, formato de
   mail, largo de un título), con sus parámetros; todo lo demás, `semantic`.
5. **La compilación no reemplaza la revisión humana**, pero la acorta: 14 de 24 quedan listas y
   el resto necesita tocar uno o dos campos. Es lo que prevé el SDD: la persona revisa y
   guarda.

### Lo que no se llegó a medir
El plan incluía correr el evaluador del lab 13 sobre las reglas compiladas: sobre sus propios
ejemplos y sobre el set de oro del lab 13 comparando contra la regla de referencia
(`run.py --evaluate`). Quedó pendiente por tiempo de GPU; el código está.

### Límites
- 30 reglas, escritas por quien diseñó la referencia: las reglas de una persona real serían más
  desprolijas.
- La "referencia" también es una opinión: en algunos desvíos (fechas como determinista) el
  compilador tiene un argumento.
