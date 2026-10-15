# llm-lab

A lab for understanding LLMs and RAG by doing, not by reading. Each lab is a
small experiment with a question, a measured result and a written conclusion.

The rule of the repo: **nothing is accepted because it "looks good"**. Every lab ends
with a number: retrieval precision, correct answers on a fixed set of
questions, token cost, latency. If it can't be measured, no conclusion is drawn.

## Structure

| Folder | What goes there |
|---|---|
| `labs/` | One lab per folder: `01-<tema>/`, `02-<tema>/`, … |
| `src/llm_lab/` | Code shared by the labs: model client, chunking, embeddings, evaluation |
| `data/raw/` | Input documents, as they are |
| `data/processed/` | Generated chunks, embeddings and indexes (they are regenerated; the heavy ones are not versioned) |
| `evals/` | Question sets with their expected answer, shared across labs |
| `docs/` | Design of the capstone project ([traffic light SDD](docs/sdd-semaforo.md)) |
| `notes/` | What was learned, written up cleanly |

## How each lab is laid out

```
labs/03-chunking/
  README.md      the question, the method, the result and the conclusion
  run.py         the experiment, reproducible with one command
  results.md     the numbers from each run, with date
```

## Lab plan

In the order they were done. Labs 11 to 16 are the capstone project: a **document quality
traffic light** that reviews documents before indexing them in a RAG
([full design](docs/sdd-semaforo.md)). 08 and 09 were left optional.

| # | Lab | The question | Status |
|---|---|---|---|
| 01 | [Calling the model](labs/01-llamar-al-modelo/) | What changes across model, system prompt, temperature and max length? | done |
| 02 | [Structured output](labs/02-salida-estructurada/) | How many answers conform to a schema with and without validation, and what happens when they don't? | done |
| 11 | [Parsing](labs/11-parseo/) | How much structure survives going from PDF, HTML and Word to blocks? | done |
| 03 | [Chunking](labs/03-chunking/) | Which way of splitting best retrieves the correct passage? | done |
| 04 | [Embeddings and search](labs/04-embeddings-busqueda/) | Dense, BM25 or hybrid: which one finds the correct passage most often? | done |
| 12 | [Vector database](labs/12-base-vectorial/) | Exact numpy, home-made HNSW and Qdrant: how much recall is lost for speed? And with filters? | done |
| 05 | [Re-ranking](labs/05-reranking/) | How much does reordering the top results improve things, and how much does it cost? | done |
| 13 | [Decisions via logprobs](labs/13-logprobs/) | Read the probabilities of A/B/C or ask for JSON? Accuracy and calibration | done |
| 14 | [Natural-language rules](labs/14-reglas/) | How many rules does an LLM compile correctly without human intervention? | done |
| 15 | [Guided review](labs/15-revision-guiada/) | How many rewrites turn green without making up data? | done |
| 06 | [Full RAG](labs/06-rag-completo/) | Is the answer backed by what was retrieved? Faithfulness and citations | done |
| 07 | [When it doesn't know](labs/07-cuando-no-sabe/) | Does it say "no tengo esa información" ("I don't have that information") instead of making something up? | done |
| 10 | [Evaluation](labs/10-evaluacion/) | Does an automatic judge agree with the hand labels? | done |
| 16 | [App and final experiment](labs/16-app/) | Does fixing before indexing improve the answers? | done |
| 08 | Tool use and agents | How many steps does an agent take and when does it pick the wrong tool? | optional |
| 09 | Cost and caching | How much does each answer cost and how can it be lowered? | optional |

Each lab has a README with the question, the method, the results and what is concluded
(including the problems it opened up for the following stages) and a `results.md` with the numbers.

**About the labels.** The gold sets (labs 02, 11, 13, 14, 15, 10) were labeled by Claude
reading each case against a written criterion, not by a person. They are in `gold.jsonl` /
`labels.jsonl` files so that anyone can review and correct them.

## The app

```bash
uv run uvicorn app.main:app      # http://localhost:8000
```

Upload a PDF, HTML or Word file → parsing → traffic light per block → guided review (jumps to the next
red, the person answers, an LLM rewrites only that block, it is re-evaluated and you see the before and
after) → index → chat with citations. Shortcuts in the review: `n`, `p`, `Enter`, `Esc`.
Tests: `uv run pytest`.

## Installation

```bash
uv sync
cp .env.example .env     # and fill in the keys
uv run python corpus/download.py   # downloads the public corpus (49 documents)
uv run labs/11-parseo/run.py         # parses it
```

## Data

Only public or own documents. Nothing from clients, nothing private.
