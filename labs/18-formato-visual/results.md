# Lab 18: resultados

Última corrida: 2026-10-20. Qwen3.5 en 4 bits por logprobs con dos órdenes, a través de `src/llm_lab/system_one.py`.

- `noul`: probabilidad de que sea cierto que el formato dice algo que el texto no dice.
- `format`: Choice entre ninguno, decorativo, explicado y oculto, con su confianza.
- `r1`: el color de la regla R1 (Choice verde, amarillo o rojo).

## Detección en 8 tablas: Qwen3.5-4B-4bit

| Caso | ¿El formato dice algo que el texto no? | Vista | noul | format | r1 |
|---|---|---|---|---|---|
| c1: solo el encabezado oscuro | no | plain | 0.79 | explicado (0.40) | green |
| c1: solo el encabezado oscuro | no | styled | 0.97 | explicado (0.50) | green |
| c2: dos filas con fondo oscuro y texto rojo, sin leyenda | sí | plain | 0.79 | explicado (0.40) | green |
| c2: dos filas con fondo oscuro y texto rojo, sin leyenda | sí | styled | 0.97 | oculto (0.50) | red |
| c3: las mismas filas, con una leyenda que lo explica | no | plain | 0.71 | explicado (0.55) | green |
| c3: las mismas filas, con una leyenda que lo explica | no | styled | 0.97 | explicado (0.69) | red |
| c4: dos montos en rojo, sin leyenda (aumentaron) | sí | plain | 0.79 | explicado (0.40) | green |
| c4: dos montos en rojo, sin leyenda (aumentaron) | sí | styled | 0.98 | explicado (0.46) | red |
| c5: última fila en negrita | no | plain | 0.79 | explicado (0.40) | green |
| c5: última fila en negrita | no | styled | 0.97 | explicado (0.52) | green |
| c6: filas alternadas en gris claro | no | plain | 0.79 | explicado (0.40) | green |
| c6: filas alternadas en gris claro | no | styled | 0.98 | oculto (0.41) | red |
| c7: una celda de turno con fondo oscuro y texto rojo, sin leyenda | sí | plain | 0.79 | explicado (0.40) | green |
| c7: una celda de turno con fondo oscuro y texto rojo, sin leyenda | sí | styled | 0.98 | explicado (0.47) | red |
| c8: montos en rojo y una columna que dice que aumentaron | no | plain | 0.83 | explicado (0.51) | green |
| c8: montos en rojo y una columna que dice que aumentaron | no | styled | 0.98 | explicado (0.56) | red |

- **plain**: Noul ≥ 0,5: detecta 3/3, falsas alarmas 5/5. format = oculto: detecta 0/3, falsas alarmas 0/5. R1 en rojo: detecta 0/3, falsas alarmas 0/5.
- **styled**: Noul ≥ 0,5: detecta 3/3, falsas alarmas 5/5. format = oculto: detecta 1/3, falsas alarmas 1/5. R1 en rojo: detecta 3/3, falsas alarmas 3/5.

## Detección en 8 tablas: Qwen3.5-9B-4bit

| Caso | ¿El formato dice algo que el texto no? | Vista | noul | format | r1 |
|---|---|---|---|---|---|
| c1: solo el encabezado oscuro | no | plain | 0.35 | ninguno (0.48) | green |
| c1: solo el encabezado oscuro | no | styled | 0.93 | explicado (0.57) | green |
| c2: dos filas con fondo oscuro y texto rojo, sin leyenda | sí | plain | 0.35 | ninguno (0.48) | green |
| c2: dos filas con fondo oscuro y texto rojo, sin leyenda | sí | styled | 0.96 | oculto (0.50) | red |
| c3: las mismas filas, con una leyenda que lo explica | no | plain | 0.41 | explicado (0.44) | green |
| c3: las mismas filas, con una leyenda que lo explica | no | styled | 0.95 | explicado (0.87) | red |
| c4: dos montos en rojo, sin leyenda (aumentaron) | sí | plain | 0.35 | ninguno (0.48) | green |
| c4: dos montos en rojo, sin leyenda (aumentaron) | sí | styled | 0.95 | explicado (0.47) | red |
| c5: última fila en negrita | no | plain | 0.35 | ninguno (0.48) | green |
| c5: última fila en negrita | no | styled | 0.94 | explicado (0.52) | green |
| c6: filas alternadas en gris claro | no | plain | 0.35 | ninguno (0.48) | green |
| c6: filas alternadas en gris claro | no | styled | 0.96 | explicado (0.54) | red |
| c7: una celda de turno con fondo oscuro y texto rojo, sin leyenda | sí | plain | 0.35 | ninguno (0.48) | green |
| c7: una celda de turno con fondo oscuro y texto rojo, sin leyenda | sí | styled | 0.94 | oculto (0.42) | red |
| c8: montos en rojo y una columna que dice que aumentaron | no | plain | 0.56 | explicado (0.46) | green |
| c8: montos en rojo y una columna que dice que aumentaron | no | styled | 0.96 | explicado (0.73) | red |

- **plain**: Noul ≥ 0,5: detecta 0/3, falsas alarmas 1/5. format = oculto: detecta 0/3, falsas alarmas 0/5. R1 en rojo: detecta 0/3, falsas alarmas 0/5.
- **styled**: Noul ≥ 0,5: detecta 3/3, falsas alarmas 5/5. format = oculto: detecta 2/3, falsas alarmas 0/5. R1 en rojo: detecta 3/3, falsas alarmas 3/5.


## El flujo completo: dos filas con fondo oscuro y texto rojo, sin leyenda

### 1. Lo que extrae un pipeline ingenuo (`get_text`)

```
Registro de ejemplo: aranceles 2026
Valores vigentes para los trámites presenciales del registro.
Trámite
Arancel
Turno
Licencia nueva
$42.230
Con turno previo
Renovación
$35.000
Con turno previo
Duplicado
$23.460
Sin turno
Cambio de domicilio
$8.900
Sin turno
Certificado de antecedentes
$5.100
Sin turno
```

### 2. La tabla como la da el parser hoy, y con el estilo anotado

```
| Trámite | Arancel | Turno |
| Licencia nueva | $42.230 | Con turno previo |
| Renovación | $35.000 | Con turno previo |
| Duplicado | $23.460 | Sin turno |
| Cambio de domicilio | $8.900 | Sin turno |
| Certificado de antecedentes | $5.100 | Sin turno |
```

```
| Trámite | Arancel | Turno |  [fila: fondo oscuro, texto blanco, negrita]
| Licencia nueva | $42.230 | Con turno previo |
| Renovación | $35.000 | Con turno previo |  [fila: fondo oscuro, texto rojo]
| Duplicado | $23.460 | Sin turno |  [fila: fondo oscuro, texto rojo]
| Cambio de domicilio | $8.900 | Sin turno |
| Certificado de antecedentes | $5.100 | Sin turno |
```

### 3. Pregunta de la revisión guiada y respuesta de la persona

> Las filas «Renovación» y «Duplicado» tienen fondo oscuro, texto rojo. ¿Qué indica ese formato?
>
> Suspendido hasta el 30/11/2026 por cambio de sistema

### 4. La tabla corregida (sin LLM: se agrega una columna)

```
| Trámite | Arancel | Turno | Observación |
| Licencia nueva | $42.230 | Con turno previo |  |
| Renovación | $35.000 | Con turno previo | Suspendido hasta el 30/11/2026 por cambio de sistema |
| Duplicado | $23.460 | Sin turno | Suspendido hasta el 30/11/2026 por cambio de sistema |
| Cambio de domicilio | $8.900 | Sin turno |  |
| Certificado de antecedentes | $5.100 | Sin turno |  |
```

### 5. Las tres preguntas tipo Jev en cada paso

| Vista | visual (Noul) | r1 (Choice) | useful (Score) |
|---|---|---|---|
| plain | 0.35 | green | 3.63 |
| styled | 0.96 | red | 3.22 |
| fixed | 0.50 | green | 3.88 |

### 6. Lo que responde el asistente: «¿Cuánto sale renovar la licencia y puedo hacerlo esta semana?»

Cada modelo responde las tres versiones (modelo fijo por fila):

| Modelo | Texto plano (get_text) | Tabla sin estilo | Tabla corregida |
|---|---|---|---|
| groq/qwen/qwen3.8-27b | Renovar la licencia te sale $35.000 y necesitás sacar turno previo [1]. | Renovar la licencia te sale $35.000 y necesitás sacar turno previo [1]. | Renovar la licencia cuesta $35.000, pero no podés hacerlo esta semana porque el trámite está suspendido hasta el 30/11/2026 por cambio de sistema [1]. |
| groq/openai/gpt-oss-120b | Renovar la licencia cuesta $35.000 y se hace con turno previo【1】. | Renovar la licencia cuesta $35.000 y necesitás sacarte un turno previo [1]. | Renovar la licencia cuesta $35.000, pero está suspendido hasta el 30/11/2026, por lo que no podés hacerlo esta semana [1]. |
| local/mlx-community/Qwen3.5-9B-4bit | Renovar la licencia cuesta $35.000 y tenés que agendar turno previo [1]. No tengo esa información en los documentos si querés saber si podés hacerlo esta semana. | Renovar la licencia cuesta $35.000 y tenés que agendar turno previo [1]. No tengo esa información en los documentos si querés saber si podés hacerlo esta semana. | Renovar la licencia cuesta $35.000, pero no podés hacerlo esta semana porque está suspendido hasta el 30/11/2026 por cambio de sistema [1]. |
