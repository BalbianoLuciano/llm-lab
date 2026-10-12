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

Ordenados de lo básico a lo que se usa en producción. Cada uno responde una pregunta.

| # | Lab | La pregunta |
|---|---|---|
| 01 | Llamar al modelo | ¿Qué cambia entre system prompt, temperatura y largo máximo, medido sobre las mismas 20 preguntas? |
| 02 | Salida estructurada | ¿Cuántas respuestas cumplen un schema con y sin validación, y qué pasa cuando no? |
| 03 | Chunking | ¿Qué tamaño y solapamiento de chunk recupera mejor sobre un set de preguntas fijo? |
| 04 | Embeddings y búsqueda | Densa, por palabras (BM25) o híbrida: ¿cuál encuentra el pasaje correcto más seguido? |
| 05 | Re-ranking | ¿Cuánto mejora la precisión reordenar los top-k, y cuánto cuesta en latencia? |
| 06 | RAG completo | ¿La respuesta está respaldada por lo recuperado? Fidelidad y citas, medidas |
| 07 | Cuándo no sabe | ¿El sistema dice "no tengo esa información" en vez de inventar? |
| 08 | Tool use y agentes | Un agente con herramientas: ¿cuántos pasos usa y cuándo se equivoca de herramienta? |
| 09 | Costo y caché | Tokens, prompt caching y latencia: ¿cuánto cuesta cada respuesta y cómo se baja? |
| 10 | Evaluación | Un evaluador automático: ¿coincide con el juicio humano en un set etiquetado a mano? |
| 11 | Parseo | ¿Cuánta estructura (títulos, listas, tablas, enlaces) sobrevive al pasar de PDF, HTML y Word a bloques? |

## Instalación

```bash
uv sync
cp .env.example .env     # y completar las claves
uv run python labs/01-llamar-al-modelo/run.py
```

## Datos

Solo documentos públicos o propios. Nada de clientes, nada privado.
