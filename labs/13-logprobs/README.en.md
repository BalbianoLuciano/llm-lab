# Lab 13: Decisions via logprobs

**The question:** to decide whether a block complies with a rule (green, yellow or red), is it better
to read the probabilities of the A/B/C tokens in a single pass, or to ask the model for a JSON?
Which one is more accurate, which one is better calibrated, how much does *temperature scaling* help?

## 1. Concept

Before writing each token, an LLM computes a probability for **all** possible
tokens. If the question ends with "Respondé A, B o C" (Answer A, B or C), you can read the probability of those
three tokens at the first position of the answer and **generate nothing** (`src/llm_lab/evaluator.py`,
`LogprobsEvaluator`, with `mlx-lm` on the Mac). You get:

- an answer that is always one of the options (no broken JSON or extra text);
- a probability distribution, from which the **confidence** comes;
- a single forward pass.

**Calibration.** A confidence is useful if it is honest: of the times it says 90 %, it is right 90 %. It is
measured with the **ECE** (expected calibration error: the average difference between confidence and
actual accuracy, per confidence bin). *Temperature scaling* divides the logits by a T
fitted on labeled data: T > 1 lowers the confidence, T < 1 raises it.

**Position bias.** A model that answers with a letter may prefer a position ("A")
regardless of the content. The remedy: ask twice, with the options in normal and
reversed order, and average (like `permutations=2` in open-alternative-jev).

In the traffic light, confidence matters: with low confidence, the block stays **doubtful yellow**
instead of green (SDD §5.3).

## 2. Method

- **Gold set** (`gold.jsonl`): 115 (block, rule) pairs from the corpus, for 6 rules that
  can be judged by looking at a block: R2 tables, R3 links, R6 currency, R7 dates, R8 effective date,
  R14 active voice. Sampled at random with a fixed seed (at most 3 blocks per document) and
  labeled with the criterion written in `rules/reference.yaml` and a note per case.
  **The labels were set by Claude, not by a person.** Distribution: 43 green, 43 yellow, 29
  red.
- **State** the evaluator sees: document title, heading path, previous and
  next block trimmed, and the marked block.
- **Evaluators**:
  - Qwen3.5-4B and Qwen3.5-9B in 4 bits with mlx-lm, via logprobs, with one and two orders.
  - **Qwen3.5-9B asked for JSON** `{"opcion", "confianza"}` (the same model, the other way of
    asking): the fair comparison.
  - Two API judges (Qwen3.8-27B and gpt-oss) and the open-alternative-jev library
    (`so1`) were planned. The API ones did not get to run because of Groq's daily quota.
    `so1` with the Hugging Face backend **segfaulted twice** while loading unquantized Qwen3.5-4B
    on the Mac's GPU, probably due to memory (another model was loaded).
- Calibration with two-half cross-validation: each half's T is fitted on the other.

```bash
uv run labs/13-logprobs/run.py
```

## 3. Results

Full numbers, per rule and confusion matrix in [`results.md`](results.md).

| Evaluator | Accuracy | Red recall | Reds as green | ECE | ECE with T | Mean confidence | Latency |
|---|---|---|---|---|---|---|---|
| 4B, given order | 65 % | 69 % | 1 | 0.075 | 0.052 | 0.73 | 4.8 s |
| **4B, two orders** | 70 % | 69 % | 2 | 0.057 | 0.071 | 0.67 | 4.8 s |
| 9B, given order | 66 % | 72 % | 2 | 0.048 | **0.017** | 0.71 | 6.2 s |
| 9B, two orders | 70 % | 72 % | 2 | **0.034** | 0.039 | 0.68 | 6.2 s |
| 9B, asking for JSON | **74 %** | 72 % | 2 | **0.242** | — | **0.98** | 4.6 s |

(latency per evaluation on the Mac, with both passes for the "two orders" ones)

Per rule, the hardest are tables (R2: 13–16 of 26) and active voice with the 4B. The
easiest, effective date (R8: 17–20 of 21).

## 4. Conclusion

1. **Asking for JSON is slightly more accurate, but its confidence is useless.** The 9B with JSON is right 74 %
   versus 70 % via logprobs, but it says "confianza 0,98" (confidence 0.98) almost always and is right 74 %: an ECE of
   0.24. It cannot be used for the doubtful yellow. Via logprobs, the ECE is 0.03 to 0.07: the
   confidence says something real.
2. **Two orders add 4 or 5 points of accuracy.** Position bias is real, especially in
   the 4B (active voice: from 8 to 13 correct out of 18). Averaging the two orders also improves
   calibration.
3. **The 4B with two orders performs like the 9B.** That is why the app and labs 14–16 use the 4B: half
   the memory and 20 % faster.
4. ***Temperature scaling* helps with a single order and not with two.** With one order it lowers the 9B's ECE
   from 0.048 to 0.017. With two, it is already calibrated: fitting T on 57 examples adds more
   noise than correction.
5. **Problem for the traffic light: 70 % is not enough to block documents.** 28 % of the reds
   go undetected and 2 reds pass as green. The blocking rules need more (a
   larger model, examples in the prompt or narrower rules), or treating yellow as
   "to review" and not as "approved".
6. **A problem that is not the evaluator's: some reds come from the parser.** Of the 8 table reds
   (R2), half are indexes or rows that parsing broke apart, not tables badly made by the
   agency. The traffic light cannot tell them apart, and the review would ask the person to
   fix something that was fine in the original.

### Limits
- 115 cases labeled by a single annotator (Claude): a second opinion and real people
  are missing.
- The six rules evaluated are those that can be judged on a block; whole-document ones
  (R5, R9, R10) are left for another measurement.
