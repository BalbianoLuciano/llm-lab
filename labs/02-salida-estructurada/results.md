# Lab 02: resultados

Última corrida: 2026-10-13. 26 pasajes (20 con montos, 6 sin montos), 327 llamadas.

| Modelo | Modo | Rechazada | JSON válido | Cumple esquema | JSON rescatable* | Montos encontrados | Montos inventados | Moneda | Vigencia | Intentos | Latencia p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| groq/openai/gpt-oss-120b | prompt | 0/26 | 26/26 | 26/26 | 26/26 | 34/34 | 0 | 34/34 | 30/30 | 1.00 | 0.69 s |
| groq/openai/gpt-oss-120b | json_object | 0/26 | 26/26 | 26/26 | 26/26 | 33/34 | 1 | 33/33 | 30/30 | 1.00 | 0.69 s |
| groq/openai/gpt-oss-120b | json_schema | 0/26 | 26/26 | 26/26 | 26/26 | 34/34 | 0 | 34/34 | 30/30 | 1.00 | 0.93 s |
| groq/openai/gpt-oss-120b | retry | 0/26 | 26/26 | 26/26 | 26/26 | 34/34 | 0 | 34/34 | 30/30 | 1.00 | 0.77 s |
| groq/qwen/qwen3.8-27b | prompt | 0/26 | 26/26 | 26/26 | 26/26 | 34/34 | 0 | 34/34 | 30/30 | 1.00 | 0.50 s |
| groq/qwen/qwen3.8-27b | json_object | 0/26 | 26/26 | 26/26 | 26/26 | 34/34 | 0 | 34/34 | 30/30 | 1.00 | 0.42 s |
| groq/qwen/qwen3.8-27b | json_schema | 0/26 | 26/26 | 26/26 | 26/26 | 34/34 | 0 | 34/34 | 30/30 | 1.00 | 0.49 s |
| groq/qwen/qwen3.8-27b | retry | 0/26 | 26/26 | 26/26 | 26/26 | 34/34 | 0 | 34/34 | 30/30 | 1.00 | 0.45 s |
| nvidia/z-ai/glm-5.3 | prompt | 0/26 | 24/26 | 24/26 | 26/26 | 24/34 | 0 | 24/24 | 20/20 | 1.00 | 13.75 s |
| nvidia/z-ai/glm-5.3 | json_object | 0/26 | 26/26 | 26/26 | 26/26 | 34/34 | 0 | 34/34 | 30/30 | 1.00 | 11.23 s |
| nvidia/z-ai/glm-5.3 | json_schema | 0/26 | 26/26 | 22/26 | 26/26 | 27/34 | 0 | 27/27 | 27/27 | 1.00 | 26.50 s |
| nvidia/z-ai/glm-5.3 | retry | 0/26 | 26/26 | 26/26 | 26/26 | 34/34 | 0 | 34/34 | 30/30 | 1.00 | 16.24 s |

\* JSON rescatable: sería válido sacando ```json y el texto alrededor.

## Errores de ejemplo

- `gemini/gemini-3.5-flash` prompt: no es JSON (Expecting value)
- `nvidia/z-ai/glm-5.3` prompt: no es JSON (Expecting value)
- `nvidia/z-ai/glm-5.3` json_schema: no cumple el esquema: ('amounts', 0, 'effective_from') Input should be a valid date or datetime, input is too short
