# Lab 07: When it doesn't know

**The question:** when the answer is not in the documents, does the system say "no tengo esa
información" (I don't have that information) instead of making something up? And at what cost to the questions that do have an answer?

## 1. Concept

There are two places where the system can decide not to answer:

- **Before generating**: if the best fragment the re-ranker found has a low score,
  the answer is probably not there. A threshold cuts it off at that point and the model is not called.
- **While generating**: the prompt asks the model to say so with an exact phrase
  if the fragments do not answer.

These are two errors with different costs: making up an answer (serious: someone pays a wrong
amount) or staying silent while having the fact (annoying: the person looks elsewhere).

## 2. Method

- The 72 answers from lab 06: 62 questions with an answer and 10 without (`u01`–`u10`: passport,
  VTV in the City (of Buenos Aires), minimum bus fare, etc.).
- The re-ranker threshold is chosen with leave-one-out validation: the threshold for each question is
  tuned with the other 71, so as not to measure on the same data it was tuned on.
- **Prompt variant (B)**: same instruction, plus a line clarifying that the question
  may use different words, synonyms or acronyms than the fragments, and that it should answer if any
  fragment has the fact. The questions are asked again over **the same fragments** from lab 06.

```bash
uv run labs/07-cuando-no-sabe/run.py
```

## 3. Results

Full numbers in [`results.md`](results.md).

| Strategy | Abstains with no answer | Abstains **with** an answer | Makes things up |
|---|---|---|---|
| Model only (prompt A) | **10/10** | 5/62 | 0 |
| Re-ranker threshold only | 4/10 | 1/62 | — |
| Model + threshold | 10/10 | 5/62 | 0 |
| Prompt B (partial: 58 of 72) | 6/6 | 3/52 | 0 |

Score of the best fragment according to the re-ranker: median 0.89 on questions with an answer and
**0.56** on those without, with maximums of 1.00 and **0.99**.

## 4. Conclusion

1. **The re-ranker threshold does not work for detecting questions with no answer.** "¿Cuánto cuesta
   la VTV en la Ciudad?" (how much is the VTV in the City?) has a score of 0.99: the corpus has the VTV of the Province (of Buenos Aires). The
   re-ranker measures whether the fragment talks about the same topic, not whether it answers the question. With the
   threshold alone only 4 of 10 are detected, and adding it to the model adds nothing.
2. **The model does tell them apart**: it reads the fragment and sees that it is from another jurisdiction. 10 of 10.
   This contradicts the SDD design (§5.5 and §9), which used the re-ranker threshold as the
   guardrail against answers without evidence. **Problem for the design**: the guardrail has
   to be the model (or a classifier over question + fragment), not a similarity score.
3. **The cost is over-abstention**: 5 of 62 questions with an answer, 3 of them with the
   evidence in the fragments. Prompt B, which clarifies that the words may not match,
   brings it down to 3 of 52 without starting to make things up on the questions with no answer (6 of 6).
4. **Incomplete measurement.** Variant B stopped at 58 of 72 questions: the daily Groq
   quota (200,000 tokens per model, see lab 16) ran out. The trend is clear, but it is not
   enough to change the production prompt without completing the run.

### Limits
- 10 questions with no answer: too few to estimate a rate; enough to see that the threshold does not
  separate them.
