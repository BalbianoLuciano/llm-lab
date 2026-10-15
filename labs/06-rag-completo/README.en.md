# Lab 06: Full RAG

**The question:** with the whole pipeline in place, are the answers correct, are they backed
by what was retrieved, and do they cite the right fragment?

## 1. Concept

The pipeline (`src/llm_lab/rag.py`), with what won in each previous lab:

1. Structure-based chunks of 1000 characters with the heading path (lab 03).
2. Dense search with bge-m3, top 10 (lab 04: hybrid did not help).
3. Re-ranking with bge-reranker-v2-m3, top 5 (lab 05).
4. Generation with Qwen3.8-27B: answer **only** from the fragments, cite each fact with its
   number `[n]`, and if it is not there, say exactly "No tengo esa información en los documentos"
   (I don't have that information in the documents).
   The fragments are marked as data, not as instructions (basic defense against
   prompt injection, SDD §9).

Three different things to measure:
- **Correct**: does it have the expected fact?
- **Faithful** (*faithfulness*): is everything it states in the fragments it cites? An answer
  can be correct and not faithful (it knows the fact "from memory") or faithful and incorrect (it correctly cites a
  fragment that does not answer).
- **Correct citation**: does the cited fragment contain the evidence? This is measured **without an LLM**:
  exact string of the evidence inside the cited chunk.

## 2. Method

- 72 questions (`evals/questions.jsonl`): 62 with an answer in the corpus and 10 without.
- Correctness and faithfulness are judged by **another model** (gpt-oss-120b) with a written criterion
  (`run.py`), so as not to add the bias of a model grading itself. Lab 10 measures
  how far that judge can be trusted.

```bash
uv run labs/06-rag-completo/run.py
```

## 3. Results

Numbers and every failed answer in [`results.md`](results.md).

| Metric | Result |
|---|---|
| Correct passage among the 5 retrieved | 60/62 |
| Correct answer (judge) | 50/62 (+7 partial) |
| Incorrect answer (judge) | 5/62, **all 5 are "no tengo esa información"** |
| Answers backed by what they cite | 55/57, 0 unbacked |
| Cites the fragment that has the evidence | 55/62 |
| Abstains on questions with no answer | **10/10** |
| p50 latency (retrieval + generation) | 2.2 s |

## 4. Conclusion

1. **The system does not make things up.** No answer states anything that is not in what it cites, and on
   the 10 questions with no answer in the corpus it says it does not know. The cost of that caution is
   the 5 incorrect ones: all of them are abstentions.
2. **Two retrieval failures and three of excess caution.** In q01 and q27 the passage did not
   reach the top 5. In q03, q20 and q59 **the evidence was in the fragments** and the model said
   it did not know (for example, it did not connect "la obra social de la Ciudad" (the City's health insurance) with "ObSBA"). That is
   addressed in lab 07.
3. **Bug found: citations from another model were not counted.** When Qwen returns 429, the answer comes from
   gpt-oss, which cites with full-width brackets (`【1】`). The parser only recognized `[1]`,
   and the judge marked those answers as "unbacked" (there were 2). Fixed in `rag.py`.
   A fallback chain between models changes the output format, not just the quality.
4. **The "partial" ones are, for the most part, correct answers to what was asked** that do not
   repeat an extra detail from the expected answer (the opening hours when the address
   was asked). Lab 10 shows that this judge is stricter than a human reading.

### Limits
- Judge and answerer are different models, but the judge is not validated against real
  people: see lab 10.
- 62 questions written by someone who knows the corpus.
