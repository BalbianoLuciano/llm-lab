# Lab 13: resultados

Última corrida: 2026-10-13. 115 pares (bloque, regla) etiquetados: {'yellow': 43, 'red': 29, 'green': 43}.

| Evaluador | Accuracy | Recall de rojo | Rojos que pasan como verde | ECE crudo | ECE calibrado (T) | Confianza media | Latencia p50 | Errores |
|---|---|---|---|---|---|---|---|---|
| qwen4b, orden dado | 65.2% | 69% | 1 | 0.075 | 0.052 (T=1.30) | 0.73 | 4.83 s | 0 |
| qwen4b, dos órdenes | 70.4% | 69% | 2 | 0.057 | 0.071 (T=0.72) | 0.67 | 4.83 s | 0 |
| qwen9b, orden dado | 66.1% | 72% | 2 | 0.048 | 0.017 (T=1.38) | 0.71 | 6.23 s | 0 |
| qwen9b, dos órdenes | 69.6% | 72% | 2 | 0.034 | 0.039 (T=0.95) | 0.68 | 6.23 s | 0 |
| qwen9b-json | 73.9% | 72% | 2 | 0.242 | — (sin logits) | 0.98 | 4.56 s | 0 |

## Accuracy por regla

| Evaluador | R2 | R3 | R6 | R7 | R8 | R14 |
|---|---|---|---|---|---|---|
| qwen4b, orden dado | 13/26 | 10/15 | 19/21 | 8/14 | 17/21 | 8/18 |
| qwen4b, dos órdenes | 13/26 | 11/15 | 18/21 | 9/14 | 17/21 | 13/18 |
| qwen9b, orden dado | 15/26 | 4/15 | 14/21 | 9/14 | 20/21 | 14/18 |
| qwen9b, dos órdenes | 15/26 | 5/15 | 16/21 | 11/14 | 19/21 | 14/18 |
| qwen9b-json | 16/26 | 8/15 | 18/21 | 10/14 | 20/21 | 13/18 |

## Matriz de confusión del mejor evaluador (filas: oro, columnas: predicho)

Mejor por recall de rojo y después accuracy: **qwen9b-json**

| | green | yellow | red |
|---|---|---|---|
| green | 30 | 8 | 5 |
| yellow | 6 | 34 | 3 |
| red | 2 | 6 | 21 |
