# Lab 10: Evaluation

**The question:** labs 06, 07 and 16 rely on an automatic judge to say whether an answer
is correct. Does that judge agree with a hand-labeled set?

## 1. Concept

An **LLM as a judge** compares the system's answer with the expected answer and returns a
verdict. It scales to thousands of answers, but it has its own biases: it can be stricter
or more lenient than a person, prefer long answers, or favor its own model.

Before trusting a number that comes from a judge, the judge has to be measured against reference
labels. Two metrics:
- **Agreement**: what fraction of verdicts match.
- **Cohen's kappa**: agreement discounting the agreement that would occur by chance. It matters when one class
  dominates (here, 56 of 62 answers are correct: a judge that always says "correct" already has
  90 % agreement and kappa 0).

## 2. Method

- The 62 answers from lab 06 to questions with an answer in the corpus.
- **Reference labels** (`labels.jsonl`): correct / partial / incorrect, reading each
  answer against the expected one with one criterion: "does it answer what was asked?". **They were assigned by
  Claude, not by a person**; the file states this on every row and it can be corrected.
- Three judges:
  - gpt-oss-120b via API, the one lab 06 used (prompt in `labs/06-rag-completo/run.py`).
  - Qwen3.8-27B via API with the same prompt.
  - The **local logprobs evaluator** from lab 13 (Qwen3.5-4B on the Mac): the same question
    as a three-level rule, without generating text.

```bash
uv run labs/10-evaluacion/run.py               # or --report-only to skip the API calls
```

## 3. Results

| Judge | Answers | Agreement | Kappa |
|---|---|---|---|
| gpt-oss-120b (API) | 62 | 87 % | 0.51 |
| Qwen3.8-27B (API) | 15 * | 87 % | 0.62 |
| **Local via logprobs, Qwen3.5-4B** | 62 | **97 %** | **0.82** |

\* Qwen ran out of daily Groq quota at 15 answers (see lab 16).

The disagreements are in [`results.md`](results.md).

## 4. Conclusion

1. **The local 4B judge agrees more than the 120B one.** 97 % agreement and kappa 0.82, versus
   87 % and 0.51. It reads the probabilities of three options and does not generate text, so it cannot
   "ramble on" or change criteria between answers.
2. **gpt-oss does not err at random: it is stricter.** Its 7 disagreements are "partial" on
   answers that reply exactly to what was asked, but do not repeat an extra detail
   that appears in the expected answer (q15: the address was asked and the expected answer
   also included the opening hours). With this judge, the lab 06 number underestimates the real quality.
3. **The judge is validated against the set, not against intuition.** If in lab 06
   "50 of 62 correct" had been taken at face value, the system would look worse than it is.
   Lab 16 uses a local judge, and the comparison between corpora uses the same judge on
   both sides, so its bias cancels out.
4. **Problem left open**: the reference labels were assigned by the same agent that
   wrote the expected answers. A person needs to review `labels.jsonl` (it is 62
   rows, less than half an hour) for these numbers to count as "human judgment".
