# llm-lab

Un laboratorio para entender LLMs y RAG haciendo, no leyendo. Cada lab es un
experimento chico con una pregunta, un resultado medido y una conclusión escrita.

La regla del repo: **nada se da por bueno porque "se ve bien"**. Cada lab termina
con un número: precisión de la recuperación, respuestas correctas sobre un set de
preguntas fijo, costo en tokens, latencia. Si no se puede medir, no se concluye.

## Estructura

| Carpeta | Qué va |
|---|---|
| `labs/` | Un lab por carpeta: `01-<tema>/`, `02-<tema>/`, … |
| `src/llm_lab/` | Código que comparten los labs: cliente del modelo, chunking, embeddings, evaluación |
| `data/raw/` | Documentos de entrada, tal cual |
| `data/processed/` | Chunks, embeddings e índices generados (se regeneran, no se versionan los pesados) |
| `evals/` | Sets de preguntas con su respuesta esperada, compartidos entre labs |
| `docs/` | Diseño del proyecto integrador ([SDD del semáforo](docs/sdd-semaforo.md)) |
| `notes/` | Lo aprendido, en limpio |

## Cómo está armado cada lab

```
labs/03-chunking/
  README.md      la pregunta, el método, el resultado y la conclusión
  run.py         el experimento, reproducible con un comando
  results.md     los números de cada corrida, con fecha
```

## Plan de labs

En el orden en que se hicieron. Los labs 11 a 16 son el proyecto integrador: un **semáforo de
calidad documental** que revisa los documentos antes de indexarlos en un RAG
([diseño completo](docs/sdd-semaforo.md)). 08 y 09 quedaron opcionales.

| # | Lab | La pregunta | Estado |
|---|---|---|---|
| 01 | [Llamar al modelo](labs/01-llamar-al-modelo/) | ¿Qué cambia entre modelo, system prompt, temperatura y largo máximo? | hecho |
| 02 | [Salida estructurada](labs/02-salida-estructurada/) | ¿Cuántas respuestas cumplen un esquema con y sin validación, y qué pasa cuando no? | hecho |
| 11 | [Parseo](labs/11-parseo/) | ¿Cuánta estructura sobrevive al pasar de PDF, HTML y Word a bloques? | hecho |
| 03 | [Chunking](labs/03-chunking/) | ¿Qué forma de cortar recupera mejor el pasaje correcto? | hecho |
| 04 | [Embeddings y búsqueda](labs/04-embeddings-busqueda/) | Densa, BM25 o híbrida: ¿cuál encuentra el pasaje correcto más seguido? | hecho |
| 12 | [Base vectorial](labs/12-base-vectorial/) | numpy exacto, HNSW propio y Qdrant: ¿cuánto recall se pierde por velocidad? ¿Y con filtros? | hecho |
| 05 | [Re-ranking](labs/05-reranking/) | ¿Cuánto mejora reordenar los primeros resultados y cuánto cuesta? | hecho |
| 13 | [Decisiones por logprobs](labs/13-logprobs/) | ¿Leer las probabilidades de A/B/C o pedir JSON? Accuracy y calibración | hecho |
| 14 | [Reglas en lenguaje natural](labs/14-reglas/) | ¿Cuántas reglas compila bien un LLM sin intervención humana? | hecho |
| 15 | [Revisión guiada](labs/15-revision-guiada/) | ¿Cuántas reescrituras pasan a verde sin inventar datos? | hecho |
| 06 | [RAG completo](labs/06-rag-completo/) | ¿La respuesta está respaldada por lo recuperado? Fidelidad y citas | hecho |
| 07 | [Cuándo no sabe](labs/07-cuando-no-sabe/) | ¿Dice "no tengo esa información" en vez de inventar? | hecho |
| 10 | [Evaluación](labs/10-evaluacion/) | ¿Un juez automático coincide con las etiquetas a mano? | hecho |
| 16 | [App y experimento final](labs/16-app/) | ¿Corregir antes de indexar mejora las respuestas? | hecho |
| 08 | Tool use y agentes | ¿Cuántos pasos usa un agente y cuándo se equivoca de herramienta? | opcional |
| 09 | Costo y caché | ¿Cuánto cuesta cada respuesta y cómo se baja? | opcional |

Cada lab tiene un README con la pregunta, el método, los resultados y lo que se concluye
(incluidos los problemas que abrió para las etapas siguientes) y un `results.md` con los números.

**Sobre las etiquetas.** Los sets de oro (lab 02, 11, 13, 14, 15, 10) los etiquetó Claude
leyendo cada caso con un criterio escrito, no una persona. Están en archivos `gold.jsonl` /
`labels.jsonl` para que cualquiera los revise y los corrija.

## La app

```bash
uv run uvicorn app.main:app      # http://localhost:8000
```

Subir un PDF, HTML o Word → parseo → semáforo por bloque → revisión guiada (salta al próximo
rojo, la persona contesta, un LLM reescribe solo ese bloque, se re-evalúa y se ve el antes y
el después) → indexar → chat con citas. Atajos en la revisión: `n`, `p`, `Enter`, `Esc`.
Tests: `uv run pytest`.

## Instalación

```bash
uv sync
cp .env.example .env     # y completar las claves
uv run python corpus/download.py   # baja el corpus público (49 documentos)
uv run labs/11-parseo/run.py         # lo parsea
```

## Datos

Solo documentos públicos o propios. Nada de clientes, nada privado.
