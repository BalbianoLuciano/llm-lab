# Lab 01: Llamar al modelo

**La pregunta:** ¿qué cambia al variar el modelo, el system prompt, la temperatura y el largo
máximo, medido sobre las mismas 20 preguntas? ¿Qué modelo gratuito usamos en el resto del
laboratorio?

Todo lo que viene después (compilar reglas, reescribir bloques, responder en el RAG) es una
llamada a un modelo. Antes de construir encima, hay que entender qué pasa en esa llamada.

---

## 1. Concepto

### Qué es una llamada a un LLM
Un LLM es una función que recibe una secuencia de **tokens** y devuelve una distribución de
probabilidad sobre cuál es el **siguiente token**. Generar texto es repetir eso: elegir un
token, agregarlo a la secuencia, volver a pedir el siguiente, hasta que el modelo emite un
token de fin o se llega al largo máximo.

Un **token** es un pedazo de palabra. "Arancel" puede ser un token o dos, según el
vocabulario del modelo. Todo se mide en tokens: el costo, los límites de uso y el largo
máximo del contexto.

### El protocolo de chat
Las APIs no reciben texto suelto sino una lista de **mensajes** con un rol:

```python
[
    {"role": "system", "content": "Sos un asistente que responde usando solo el texto dado."},
    {"role": "user", "content": "Texto: ...\n\nPregunta: ¿cuánto cuesta?"},
]
```

- **system**: instrucciones de fondo. Define cómo se comporta el modelo en toda la
  conversación.
- **user**: lo que pide la persona (o nuestro programa).
- **assistant**: lo que respondió el modelo antes. Sirve para mantener una conversación o para
  dar ejemplos.

Por dentro, el proveedor aplana esa lista en un solo texto con marcas especiales (la *chat
template*) y se lo pasa al modelo. El modelo no "sabe" qué es un rol: aprendió en el
entrenamiento a darle más peso a lo que viene marcado como system.

### Los parámetros que vamos a mover
- **temperature**: cómo se elige el siguiente token a partir de las probabilidades. Con 0 se
  elige siempre el más probable (salida casi determinista). Con valores altos se aplana la
  distribución y salen tokens menos probables: más variedad, más errores.
- **max_tokens**: el tope de tokens de salida. Si se alcanza, la respuesta se corta donde esté.
- **El modelo**: tamaño, entrenamiento y si **razona** antes de contestar.

### Modelos que razonan
Algunos modelos (gpt-oss, GLM, Kimi) escriben primero un razonamiento interno que no se
muestra en la respuesta, y después contestan. Esos tokens **se cuentan como salida** y
**consumen el max_tokens**. En la prueba inicial, GLM-5.3 usó 107 tokens de salida para
contestar "NO". Esto tiene consecuencias de costo, de latencia y de cortes (experimento D).

### Un solo cliente para todos los proveedores
Groq, NVIDIA, Gemini y OpenRouter exponen el mismo protocolo que OpenAI (`/chat/completions`).
Por eso `src/llm_lab/models.py` usa el SDK `openai` y solo cambia la URL base y la clave. Si
un proveedor contesta 429 (límite de uso) o 5xx, se pasa al siguiente de la cadena.

## 2. Método

- **20 preguntas fijas** en `questions.jsonl`, sobre textos cortos de trámites escritos para
  este lab: extracción de datos (montos, fechas, plazos), chequeo de reglas del semáforo
  (R3, R5, R6, R7, R14), preguntas cuya respuesta **no está** en el texto (para ver si el
  modelo inventa) y dos de razonamiento simple.
- Cada pregunta pide un formato exacto (un número, SI/NO, una fecha, `NO_INFO`), así la
  corrección es automática: se compara la respuesta normalizada con la esperada.
- Cuatro experimentos:

| | Qué varía | Qué se fija |
|---|---|---|
| A | 6 modelos gratuitos | temperatura 0, con system prompt |
| B | temperatura 0 / 0,7 / 1,5, con 3 repeticiones | modelo rápido (Qwen3.8-27B en Groq) |
| C | con y sin system prompt | un modelo que no razona y uno que sí |
| D | max_tokens 16 / 64 / 512 / sin tope | gpt-oss-120b (razona) |

Cada llamada se guarda en `runs.jsonl` apenas termina, así una corrida cortada se retoma
sin repetir llamadas (y sin gastar cupo). El script respeta una pausa por proveedor para no
pasar el límite por minuto.

```bash
uv run labs/01-llamar-al-modelo/run.py
```

## 3. Resultados

Los números de cada corrida están en [`results.md`](results.md).

Corrida del 2026-10-11: 458 llamadas, US$ 0.

**A. Modelos.** Los 6 aciertan 20/20. Lo que los separa es la velocidad y lo que gastan:

| Modelo | Aciertos | Latencia p50 | Tokens de salida p50 | Razona |
|---|---|---|---|---|
| Groq · qwen3.8-27b | 100 % | **0,23 s** | 2 | no |
| Groq · gpt-oss-120b | 100 % | 0,57 s | 102 | sí |
| OpenRouter · nemotron-3-super | 100 % | 1,13 s | 68 | sí |
| NVIDIA · glm-5.3 | 100 % | 1,89 s | 62 | sí |
| Gemini · 3.5-flash | 100 % | 2,25 s | 1 | no visible |
| NVIDIA · kimi-k3 | 100 % | 6,34 s | 50 | sí |

**B. Temperatura** (qwen3.8-27b, 3 repeticiones por pregunta):

| Temperatura | Aciertos | Misma respuesta en las 3 repeticiones |
|---|---|---|
| 0 | 100 % | 20/20 |
| 0,7 | 95 % | 17/20 |
| 1,5 | 82 % | 12/20 |

Con 0,7 los errores son de juicio: cambia SI por NO en las reglas más subjetivas (voz activa,
siglas). Con 1,5 además rompe el formato: "18.500" en vez de "18500", JSON inventado, texto
en portugués, "DO" en vez de "NO".

**C. System prompt.** Sin efecto medible: 100 % con y sin. Las preguntas ya piden el formato
exacto, así que la instrucción de fondo no agrega nada en tareas así.

**D. Largo máximo** (gpt-oss-120b, que razona):

| max_tokens | Aciertos | Respuestas vacías |
|---|---|---|
| 16 | 0 % | 20/20 |
| 64 | 0 % | 20/20 |
| 512 | 100 % | 0/20 |
| sin tope | 100 % | 0/20 |

El modelo gasta unos 100 tokens razonando antes de escribir "NO". Con un tope de 16 o 64 se
corta en medio del razonamiento y **la respuesta llega vacía**, sin error. Es el resultado más
importante del lab.

## 4. Conclusión

1. **El set es demasiado fácil.** Los 6 modelos sacan 100 %, así que no sirve para elegir por
   calidad: hay *efecto techo*. Es esperable con textos de una oración escritos a medida. Las
   preguntas difíciles van a salir del corpus real (tablas confusas, siglas, fechas
   relativas), y la comparación de calidad se repite en los labs 02 y 13.
2. **Temperatura 0 para todo lo que se evalúa o se extrae.** Subirla no aporta nada en estas
   tareas: baja los aciertos y vuelve irreproducible el resultado. Se reserva para cuando
   haga falta variedad (por ejemplo, proponer varias reescrituras de un bloque).
3. **Con modelos que razonan, nunca un max_tokens chico.** El razonamiento consume el tope y
   la respuesta llega vacía sin error. En `models.py` el tope queda en `None` por defecto, y
   una respuesta vacía se tiene que tratar como falla.
4. **Los tokens de razonamiento cuestan.** gpt-oss usa 50 veces más tokens de salida que Qwen
   para el mismo "NO". Gratis no importa, pero con los límites diarios por tokens se nota:
   el cupo de Groq se gasta más rápido.
5. **La elección, por ahora:** qwen3.8-27b en Groq como modelo por defecto para tareas cortas
   (el más rápido y el más barato en tokens), y gpt-oss-120b o glm-5.3 como respaldo y para
   tareas que necesiten razonar. Kimi K3 es demasiado lento para usarlo en un bucle.
6. **Los límites gratuitos se sienten.** 25 llamadas recibieron 429 y se recuperaron al volver a
   correr. Hace falta que el script pueda retomar donde quedó, y la cadena de respaldo.
