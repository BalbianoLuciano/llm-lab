# Lab 06: resultados

Última corrida: 2026-10-13. Respuesta: groq/qwen/qwen3.8-27b; juez: groq/openai/gpt-oss-120b. Recuperación: densa + re-ranking, top 5.

## Preguntas con respuesta en el corpus

| Métrica | Valor |
|---|---|
| El pasaje correcto está entre los 5 recuperados | 60/62 |
| Respuesta correcta (juez) | 50/62 |
| Respuesta parcial (juez) | 7/62 |
| Respuesta incorrecta (juez) | 5/62 |
| Dijo que no sabe teniendo el dato | 5/62 |
| Cita el fragmento que tiene la evidencia | 55/62 |
| Respuestas sin ninguna cita | 0/62 |

## Fidelidad (todas las respuestas que no se abstuvieron)

| Veredicto del juez | Respuestas |
|---|---|
| respaldada | 55/57 |
| parcial | 2/57 |
| no_respaldada | 0/57 |

## Preguntas sin respuesta en el corpus

Se abstuvo en 10/10.

Latencia p50 por respuesta (recuperación + generación): 2.2 s.

## Respuestas incorrectas o no respaldadas

- **q01** ¿Cuánto sale sacar la licencia de conducir por primera vez en la Ciudad? — esperado: $42.230 — respondió: No tengo esa información en los documentos. — juez: incorrecta / -
- **q03** ¿Qué precio tiene el certificado nacional de antecedentes de tránsito en la Ciudad? — esperado: $10.150 — respondió: No tengo esa información en los documentos. — juez: incorrecta / -
- **q20** ¿Cuánto es lo máximo que me pueden cobrar de copago en la obra social de la Ciudad? — esperado: Hasta $4000 — respondió: No tengo esa información en los documentos. — juez: incorrecta / -
- **q27** ¿Cuántas cuotas de carencia tengo que pagar al afiliarme voluntariamente a IOMA? — esperado: Tres; el alta definitiva es el primer día del cuarto mes — respondió: No tengo esa información en los documentos. — juez: incorrecta / -
- **q59** ¿Hasta qué edad puedo tener a mi hijo estudiante en la ObSBA? — esperado: De 21 a 25 años, con constancia de alumno regular — respondió: No tengo esa información en los documentos. — juez: incorrecta / -
