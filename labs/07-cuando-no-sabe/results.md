# Lab 07: resultados

Última corrida: 2026-10-13. 62 preguntas con respuesta y 10 sin respuesta (respuestas del lab 06).

| Estrategia | Se abstiene cuando no hay respuesta | Se abstiene teniendo la respuesta | Responde mal (juez) | Umbral |
|---|---|---|---|---|
| Solo el modelo | 10/10 | 5/62 | 0 | — |
| Solo umbral del re-ranker (validación dejando uno afuera) | 4/10 | 1/62 | 5 | 0.06 |
| Modelo + umbral del re-ranker (validación dejando uno afuera) | 10/10 | 5/62 | 0 | -inf |

## Variante del prompt: "respondé aunque la pregunta use otras palabras"

| Prompt | Se abstiene cuando no hay respuesta | Se abstiene teniendo la respuesta | Responde mal (juez) |
|---|---|---|---|
| A (lab 06) | 10/10 | 5/62 | 0 |
| B | 6/6 | 3/52 | 0 |

Preguntas sin respuesta que el prompt B contestó igual:

- ninguna

## Puntaje del mejor fragmento según el re-ranker

| Preguntas | Mínimo | Mediana | Máximo |
|---|---|---|---|
| con respuesta | 0.06 | 0.89 | 1.00 |
| sin respuesta | 0.00 | 0.56 | 0.99 |

## Preguntas sin respuesta: qué hizo el sistema

- u03 ¿Cuánto sale el boleto mínimo de colectivo en la Ciudad en julio de 2026? — puntaje 0.92 — se abstuvo
- u04 ¿En qué horario atiende el centro de servicios de ARBA de La Plata? — puntaje 0.04 — se abstuvo
- u08 ¿Dónde me inscribo en el monotributo social? — puntaje 0.02 — se abstuvo
- u09 ¿Cuál es la cuota de IOMA para un grupo familiar de cuatro personas? — puntaje 0.56 — se abstuvo
- u10 ¿Cuánto cuesta la habilitación exprés de un local comercial en CABA? — puntaje 0.55 — se abstuvo
- u07 ¿Cuánto cuesta inscribir una SAS en Ingresos Brutos de ARBA? — puntaje 0.88 — se abstuvo
- u01 ¿Cuánto cuesta sacar el pasaporte? — puntaje 0.00 — se abstuvo
- u02 ¿Cuánto cuesta la VTV en la Ciudad de Buenos Aires? — puntaje 0.99 — se abstuvo
- u05 ¿Cuánto cuesta renovar el DNI? — puntaje 0.00 — se abstuvo
- u06 ¿Cuánto tarda ARBA en resolver una solicitud de exención? — puntaje 0.76 — se abstuvo
