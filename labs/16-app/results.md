# Lab 16: experimento final

Última corrida: 2026-10-13. Documentos en juego: 35. Evaluador: `mlx-community/Qwen3.5-4B-4bit`; respuestas y juez: `mlx-community/Qwen3.5-9B-4bit` local, con los prompts del lab 06.

## 1. Semáforo (R6 moneda, R8 vigencia) sobre bloques con montos

| Regla | Verde | Amarillo | Rojo |
|---|---|---|---|
| r6-moneda | 4 | 56 | 0 |
| r8-vigencia | 16 | 1 | 43 |

## 2. Revisión guiada automática

- Bloques rojos revisados: 40
- Reescritos: 33 (siguen en rojo después: 0)
- Solo marcados con [FALTA] (el documento no tiene el dato): 3
- Sin cambios (el autor no tenía el dato o se rechazó por números nuevos): 4
- Rechazos del guardrail determinista: 1

## 3. RAG sobre el corpus original (A) y el corregido (B)

| Preguntas | Corpus | Correctas | Parciales | Incorrectas | Se abstuvo |
|---|---|---|---|---|---|
| 8 del set general (evidencia en un documento corregido) | A | 7 | 0 | 1 | 1 |
| 8 del set general (evidencia en un documento corregido) | B | 7 | 0 | 1 | 1 |
| 7 de vigencia | A | 6 | 0 | 1 | 0 |
| 7 de vigencia | B | 6 | 0 | 1 | 1 |

Preguntas sin respuesta en el corpus: se abstuvo en 10/10 (A) y 10/10 (B).

## Preguntas cuyo veredicto cambió de A a B

- v02: correcta → **incorrecta** — B respondió: No tengo esa información en los documentos.
- v07: incorrecta → **correcta** — B respondió: La cuota de afiliado voluntario individual pasa a $105.037 a partir del 1° de junio de 2026 [1].

## Ejemplos de reescritura

**caba-canales-lugares-pago|4** (r8-vigencia) → {'r8-vigencia': 'green'}

Antes:

```
Además si pagas con Buepp, la billetera del Banco Ciudad, accedés a un 20% de descuento por única vez con tope de $10 mil pesos
```

Después:

```
Además si pagas con Buepp, la billetera del Banco Ciudad, accedés a un 20% de descuento por única vez con tope de $10 mil pesos, vigente desde el 08/05/2025 hasta el 31/12/2026.
```

**caba-obsba-copagos|16** (r8-vigencia) → {'r8-vigencia': 'green'}

Antes:

```
Los copagos pueden tener un valor de hasta $4000.
```

Después:

```
Los copagos pueden tener un valor de hasta $4000, vigentes a partir del 16 de junio de 2026.
```

**pba-ioma-aumento-cuota-avi-2026|10** (r8-vigencia) → {'r8-vigencia': 'green'}

Antes:

```
$ 100.900
```

Después:

```
$ 100.900 a partir del 1° de abril de 2026.
```

**pba-ioma-aumento-cuota-avi-2026|12** (r8-vigencia) → {'r8-vigencia': 'green'}

Antes:

```
$ 105.037
```

Después:

```
A partir del 01/06/2026 la cuota será de $ 105.037
```

**pba-ioma-aumento-cuota-avi-2026|14** (r8-vigencia) → {'r8-vigencia': 'green'}

Antes:

```
$ 108.504
```

Después:

```
$ 108.504 a partir del 1° de agosto de 2026
```

**pba-ioma-aumento-cuota-avi-2026|15** (r8-vigencia) → {'r8-vigencia': 'green'}

Antes:

```
El incremento inicial de $ 7.724 se verá impactado en la cuota del mes de abril 2026.
```

Después:

```
El incremento inicial de $ 7.724 se verá impactado en la cuota a partir del 1 de abril de 2026.
```

