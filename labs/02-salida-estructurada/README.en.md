# Lab 02: Structured output

**The question:** when we ask a model for JSON, how many answers comply with the schema,
with and without validation, and what happens when they don't?

The task is real and the traffic light needs it (rules R6 and R8): from a passage of the corpus, extract
each amount of money with its concept, its currency and the date from which it is in force.

## 1. Concept

A model generates text, token by token. That this text is valid JSON and also has the
fields and types we expect is not guaranteed. There are four ways to ask for it, from less to more
control:

| Mode | What it does | What it guarantees |
|---|---|---|
| `prompt` | describes the format in the prompt | nothing |
| `json_object` | the provider's "JSON mode" | that it is valid JSON, not that it has the fields |
| `json_schema` | *structured outputs*: the provider constrains generation to the schema | that it complies with the schema the provider accepts |
| `retry` | `prompt` + validation with Pydantic; if it fails, the error is sent back to the model (up to 2 times) | that it complies with the Pydantic schema, or an explicit error |

The schema (`run.py`): a list of amounts with `concept`, `amount` (number), `currency`
(`ARS`, `USD`, `EUR` or null) and `effective_from` (date or null).

## 2. Method

- **Gold set** (`gold.jsonl`): 26 passages from the corpus, 20 with amounts (34 amounts in total) and 6
  without amounts that have numbers that are not money (percentages, years, phone numbers). Labeled by
  hand: amount, currency and effective date of each one.
- Each passage is **a block plus as many preceding ones as needed** and its heading path: on the
  fees page, the concept and the amount are in different blocks.
- Three free models: Qwen3.8-27B and gpt-oss-120b on Groq, GLM-5.3 on NVIDIA. Gemini
  was planned, but its free tier allows **20 requests per day** and it ran out at
  call 25.
- Network failures and usage limits (429) do not count as a result: the script
  retries them on the next run.

```bash
uv run labs/02-salida-estructurada/run.py
```

## 3. Results

Full numbers in [`results.md`](results.md).

| Model | prompt | json_object | json_schema | retry | p50 latency |
|---|---|---|---|---|---|
| Qwen3.8-27B (Groq) | 26/26 | 26/26 | 26/26 | 26/26 | 0.5 s |
| gpt-oss-120b (Groq) | 26/26 | 26/26 | 26/26 | 26/26 | 0.7–0.9 s |
| GLM-5.3 (NVIDIA) | **24/26** | 26/26 | **22/26** | 26/26 | 11–26 s |

(answers that comply with the Pydantic schema)

When the JSON is valid, the extraction is almost perfect: Qwen and gpt-oss find all 34
amounts in every mode, without inventing any in the passages without amounts, with the currency right
in all of them and the effective date right in 30 of 30. The only reading error: gpt-oss, in `json_object`,
read "$ 108.504-" as **108.504** (it took the thousands separator dot for a decimal point): an amount a thousand times
smaller, in a perfectly valid format.

## 4. Conclusion

1. **With good models, format is no longer the problem.** Qwen and gpt-oss comply with the schema
   100 % of the time even without any help. But a different model (GLM) wraps the
   answer in a markdown code block, with ```json, and breaks strict parsing in 2 of
   26. **`retry` is the only option that works the same with all three**, and it costs almost nothing: on
   average a single attempt was needed.
2. **`json_schema` is not what it seems.** Providers accept a subset of JSON
   Schema: strict mode does not support `format: date`. It had to be removed, and then the
   schema the provider enforces stopped being the one Pydantic validates. GLM returned
   "2026-04" and "diciembre 2025" (December 2025) in the date field: valid JSON for the provider, invalid
   for us.
3. **Problem for the traffic light: some dates are not days.** Those "invalid dates" were not
   model errors: the corpus says "a partir de abril de 2026" (from April 2026) or "a diciembre 2025" (as of December 2025).
   A `date` field forces you to invent the day. R8's effective-date schema has to accept
   partial dates (year and month) instead of forcing a full date.
4. **A valid JSON can have a value off by a factor of a thousand.** The Argentine thousands separator (dot)
   gets confused with the decimal one. No schema detects it: a content validation is needed
   (for example, that the number appears in the text in its original format).
5. **The cost of the choice is latency.** Groq answers in half a second; GLM on NVIDIA,
   between 11 and 26 seconds, because it reasons before answering. For the rule compiler
   (lab 14) and the rewriting (lab 15), Qwen on Groq is used with validation and retry.
6. **Free limits shape the design.** Gemini allows 20 requests per day: it is only useful
   as a last fallback. It ended up at the end of the chain in `src/llm_lab/models.py`.

### Limits
- Ceiling effect again: 26 short, well-written passages. The interesting part showed up at the
  edges (partial dates, amounts in "UT"), not in the average.
- The gold labels were set by Claude reading each passage, not by a person.
