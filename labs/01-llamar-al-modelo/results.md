# Lab 01: resultados

Última corrida: 2026-10-11. 458 llamadas, costo US$ 0 (free tiers).

## A. Modelos (temperatura 0, con system prompt)

| modelo | n | aciertos | latencia p50 (s) | tokens salida p50 |
|---|---|---|---|---|
| gemini/gemini-3.5-flash | 20 | 100% | 2.25 | 1 |
| groq/openai/gpt-oss-120b | 20 | 100% | 0.57 | 102 |
| groq/qwen/qwen3.8-27b | 20 | 100% | 0.23 | 2 |
| nvidia/moonshotai/kimi-k3 | 20 | 100% | 6.34 | 50 |
| nvidia/z-ai/glm-5.3 | 20 | 100% | 1.89 | 62 |
| openrouter/nvidia/nemotron-3-super-120b-a12b:free | 20 | 100% | 1.13 | 68 |

Por tipo de pregunta:

| modelo | tipo | n | aciertos | latencia p50 (s) | tokens salida p50 |
|---|---|---|---|---|---|
| gemini/gemini-3.5-flash | extraccion | 5 | 100% | 2.30 | 5 |
| gemini/gemini-3.5-flash | razonamiento | 2 | 100% | 2.21 | 3 |
| gemini/gemini-3.5-flash | regla | 10 | 100% | 2.25 | 1 |
| gemini/gemini-3.5-flash | sin_dato | 3 | 100% | 1.90 | 3 |
| groq/openai/gpt-oss-120b | extraccion | 5 | 100% | 0.56 | 98 |
| groq/openai/gpt-oss-120b | razonamiento | 2 | 100% | 0.61 | 130 |
| groq/openai/gpt-oss-120b | regla | 10 | 100% | 0.59 | 106 |
| groq/openai/gpt-oss-120b | sin_dato | 3 | 100% | 0.44 | 75 |
| groq/qwen/qwen3.8-27b | extraccion | 5 | 100% | 0.24 | 6 |
| groq/qwen/qwen3.8-27b | razonamiento | 2 | 100% | 0.23 | 4 |
| groq/qwen/qwen3.8-27b | regla | 10 | 100% | 0.23 | 2 |
| groq/qwen/qwen3.8-27b | sin_dato | 3 | 100% | 0.23 | 3 |
| nvidia/moonshotai/kimi-k3 | extraccion | 5 | 100% | 3.42 | 25 |
| nvidia/moonshotai/kimi-k3 | razonamiento | 2 | 100% | 9.01 | 54 |
| nvidia/moonshotai/kimi-k3 | regla | 10 | 100% | 9.00 | 68 |
| nvidia/moonshotai/kimi-k3 | sin_dato | 3 | 100% | 4.19 | 43 |
| nvidia/z-ai/glm-5.3 | extraccion | 5 | 100% | 1.95 | 47 |
| nvidia/z-ai/glm-5.3 | razonamiento | 2 | 100% | 1.60 | 78 |
| nvidia/z-ai/glm-5.3 | regla | 10 | 100% | 2.17 | 88 |
| nvidia/z-ai/glm-5.3 | sin_dato | 3 | 100% | 1.67 | 51 |
| openrouter/nvidia/nemotron-3-super-120b-a12b:free | extraccion | 5 | 100% | 1.11 | 67 |
| openrouter/nvidia/nemotron-3-super-120b-a12b:free | razonamiento | 2 | 100% | 1.18 | 78 |
| openrouter/nvidia/nemotron-3-super-120b-a12b:free | regla | 10 | 100% | 1.19 | 68 |
| openrouter/nvidia/nemotron-3-super-120b-a12b:free | sin_dato | 3 | 100% | 0.91 | 58 |

Errores:


## B. Temperatura (groq/qwen/qwen3.8-27b, 3 repeticiones)

| temperatura | n | aciertos | latencia p50 (s) | tokens salida p50 |
|---|---|---|---|---|
| 0.0 | 58 | 100% | 0.26 | 2 |
| 0.7 | 60 | 95% | 0.26 | 2 |
| 1.5 | 60 | 82% | 0.27 | 2 |

| temperatura | preguntas con la misma respuesta en las 3 repeticiones |
|---|---|
| 0.0 | 20/20 |
| 0.7 | 17/20 |
| 1.5 | 12/20 |

## C. System prompt (temperatura 0)

| modelo | con_system | n | aciertos | latencia p50 (s) | tokens salida p50 |
|---|---|---|---|---|---|
| groq/openai/gpt-oss-120b | False | 20 | 100% | 0.56 | 102 |
| groq/openai/gpt-oss-120b | True | 20 | 100% | 0.56 | 102 |
| groq/qwen/qwen3.8-27b | False | 20 | 100% | 0.23 | 2 |
| groq/qwen/qwen3.8-27b | True | 20 | 100% | 0.26 | 2 |

## D. Largo máximo (groq/openai/gpt-oss-120b)

| max_tokens | n | aciertos | latencia p50 (s) | tokens salida p50 |
|---|---|---|---|---|
| 16 | 20 | 0% | 0.35 | 16 |
| 512 | 20 | 100% | 0.55 | 102 |
| 64 | 20 | 0% | 0.45 | 64 |
| None | 20 | 100% | 0.56 | 102 |

Respuestas vacías por max_tokens:

- max_tokens=16: 20/20
- max_tokens=64: 20/20
- max_tokens=512: 0/20
- max_tokens=None: 0/20
