# Lab 10: resultados

Última corrida: 2026-10-13. 62 respuestas del lab 06. Etiquetas de referencia: {'claude (sin revisión humana)': 62}; distribución {'incorrecta': 5, 'correcta': 56, 'parcial': 1}.

| Juez | Acuerdo | Kappa de Cohen | Correctas según el juez |
|---|---|---|---|
| gpt-oss-120b (lab 06) (62 respuestas) | 87% | 0.51 | 50/62 |
| groq/qwen/qwen3.8-27b (15 respuestas) | 87% | 0.62 | 11/15 |
| local logprobs Qwen3.5-4B-4bit (62 respuestas) | 97% | 0.82 | 56/62 |

## Desacuerdos con las etiquetas a mano

- q11 (a mano: parcial) gpt-oss-120b (lab 06): correcta, groq/qwen/qwen3.8-27b: None, local logprobs Qwen3.5-4B-4bit: correcta — «Para abonar la partida urgente podés usar tarjeta de crédito, débito, billeteras virtuales, Pago Mis Cuentas, Link o Interbanking [5]. No es necesario»
- q12 (a mano: correcta) gpt-oss-120b (lab 06): parcial, groq/qwen/qwen3.8-27b: None, local logprobs Qwen3.5-4B-4bit: correcta — «No, el trámite de solicitud de partidas no incluye legalización ni apostillado [2].»
- q15 (a mano: correcta) gpt-oss-120b (lab 06): parcial, groq/qwen/qwen3.8-27b: parcial, local logprobs Qwen3.5-4B-4bit: correcta — «La dirección de AGIP para este trámite es Viamonte 900 [2].»
- q32 (a mano: correcta) gpt-oss-120b (lab 06): parcial, groq/qwen/qwen3.8-27b: parcial, local logprobs Qwen3.5-4B-4bit: correcta — «El bono de consulta médica en la categoría C cuesta $7.000 [1].»
- q33 (a mano: correcta) gpt-oss-120b (lab 06): parcial, groq/qwen/qwen3.8-27b: None, local logprobs Qwen3.5-4B-4bit: correcta — «El bono de prácticas bioquímicas autoriza de forma automática hasta 13 prácticas al año [1].»
- q37 (a mano: correcta) gpt-oss-120b (lab 06): parcial, groq/qwen/qwen3.8-27b: None, local logprobs Qwen3.5-4B-4bit: correcta — «La clave CIT de ARBA debe tener una longitud mínima de 9 y máxima de 30 caracteres [1].»
- q53 (a mano: correcta) gpt-oss-120b (lab 06): parcial, groq/qwen/qwen3.8-27b: None, local logprobs Qwen3.5-4B-4bit: parcial — «El número gratuito del Ente es el 0800-222-(ENTE) 3683 [1].»
- q57 (a mano: correcta) gpt-oss-120b (lab 06): parcial, groq/qwen/qwen3.8-27b: None, local logprobs Qwen3.5-4B-4bit: correcta — «Según el contrato modelo, el alquiler se abona entre el 1 y el 10 de cada mes [1].»
