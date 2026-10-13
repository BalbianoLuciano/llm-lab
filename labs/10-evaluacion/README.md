# Lab 10: Evaluación

**La pregunta:** los labs 06, 07 y 16 confían en un juez automático para decir si una respuesta
es correcta. ¿Ese juez coincide con un set etiquetado a mano?

## 1. Concepto

Un **LLM como juez** compara la respuesta del sistema con la respuesta esperada y devuelve un
veredicto. Escala a miles de respuestas, pero tiene sus propios sesgos: puede ser más estricto
o más laxo que una persona, preferir respuestas largas, o favorecer a su propio modelo.

Antes de confiar en un número que sale de un juez, hay que medir al juez contra etiquetas de
referencia. Dos métricas:
- **Acuerdo**: qué fracción de veredictos coincide.
- **Kappa de Cohen**: el acuerdo descontando el que se daría por azar. Importa cuando una clase
  domina (acá, 56 de 62 respuestas son correctas: un juez que diga siempre "correcta" ya tiene
  90 % de acuerdo y kappa 0).

## 2. Método

- Las 62 respuestas del lab 06 a preguntas con respuesta en el corpus.
- **Etiquetas de referencia** (`labels.jsonl`): correcta / parcial / incorrecta, leyendo cada
  respuesta contra la esperada con un criterio: "¿responde lo que se preguntó?". **Las puso
  Claude, no una persona**; el archivo lo indica en cada fila y se puede corregir.
- Tres jueces:
  - gpt-oss-120b por API, el que usó el lab 06 (prompt en `labs/06-rag-completo/run.py`).
  - Qwen3.8-27B por API con el mismo prompt.
  - El **evaluador local por logprobs** del lab 13 (Qwen3.5-4B en la Mac): la misma pregunta
    como regla de tres niveles, sin generar texto.

```bash
uv run labs/10-evaluacion/run.py               # o --report-only para no llamar a las APIs
```

## 3. Resultados

| Juez | Respuestas | Acuerdo | Kappa |
|---|---|---|---|
| gpt-oss-120b (API) | 62 | 87 % | 0,51 |
| Qwen3.8-27B (API) | 15 * | 87 % | 0,62 |
| **Local por logprobs, Qwen3.5-4B** | 62 | **97 %** | **0,82** |

\* Qwen se quedó sin cuota diaria de Groq a las 15 respuestas (ver el lab 16).

Los desacuerdos están en [`results.md`](results.md).

## 4. Conclusión

1. **El juez local de 4B coincide más que el de 120B.** 97 % de acuerdo y kappa 0,82, contra
   87 % y 0,51. Lee las probabilidades de tres opciones y no genera texto, así que no puede
   "explayarse" ni cambiar de criterio entre respuestas.
2. **gpt-oss no se equivoca al azar: es más estricto.** Sus 7 desacuerdos son "parcial" en
   respuestas que contestan exactamente lo que se preguntó, pero no repiten un detalle extra
   que figura en la respuesta esperada (q15: se preguntó la dirección y la respuesta esperada
   también traía el horario). Con este juez, el número del lab 06 subestima la calidad real.
3. **El juez se valida contra el set, no contra la intuición.** Si en el lab 06 se hubiera
   tomado "50 de 62 correctas" al pie de la letra, el sistema parecería peor de lo que es.
   Para el lab 16 se usa un juez local, y la comparación entre corpus usa el mismo juez en
   los dos lados, así que su sesgo se cancela.
4. **Problema que queda abierto**: las etiquetas de referencia las puso el mismo agente que
   escribió las respuestas esperadas. Hace falta que una persona revise `labels.jsonl` (son 62
   filas, menos de media hora) para que estos números valgan como "juicio humano".
