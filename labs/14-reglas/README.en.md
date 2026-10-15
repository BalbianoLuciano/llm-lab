# Lab 14: Natural-language rules

**The question:** a person writes a quality rule the way they would say it ("los links tienen que
decir a dónde llevan" — links must say where they lead). How many of them does an LLM compile correctly, with no human intervention, into a typed
rule that the traffic light can evaluate? Does it detect the ones that are too vague to be evaluated?

## 1. Concept

Rules are **data, not code** (SDD §5.2). A compiler (`src/llm_lab/compiler.py`)
turns the text into a Pydantic `Rule` (`src/llm_lab/rules.py`):

- `kind`: `semantic` (evaluated by a model) or `deterministic` (checked with code).
- `scope`: each block or the whole document. `applies_to`: which block types.
- `question` and `levels`: the question for the evaluator and what green, yellow and red mean (this is
  also the explanation the person sees in the review).
- `blocking`, `source` (the standard it comes from) and two `examples`.

If the rule is vague ("que sea claro" — make it clear), the compiler must not invent a criterion: it returns
`ambiguous` and asks for an example or a concrete criterion. It uses JSON output validated with Pydantic and
a retry with the error (what worked in lab 02).

## 2. Method

- **30 natural-language rules** (`rules_nl.jsonl`), worded the way someone
  from the agency would write them: the 14 from the SDD, 10 new ones and 6 deliberately vague ones.
- **Reference compilation** of the 24 compilable ones, written by hand: R1–R14 in
  `rules/reference.yaml` (the one the traffic light uses) and the other 10 in `extra_reference.yaml`.
- They are compared field by field: `kind`, `scope`, `blocking`, `applies_to` (Jaccard index
  between sets), and whether `source` cites the same standard (same code: 1.4.1, 4217, 24495-1).
- Three free models: Qwen3.8-27B and gpt-oss-120b on Groq, GLM-5.3 on NVIDIA.

```bash
uv run labs/14-reglas/run.py
```

## 3. Results

Full numbers and every difference from the reference in [`results.md`](results.md).

| Model | Valid schema | Vague ones detected | Good ones flagged as vague | `kind` | `scope` | `blocking` | Standard | Correct without editing |
|---|---|---|---|---|---|---|---|---|
| **Qwen3.8-27B** | 30/30 | **6/6** | 0/24 | 96 % | 92 % | 100 % | 100 % | **14/24** |
| gpt-oss-120b | 30/30 | 6/6 | 0/24 | **46 %** | 92 % | 100 % | 100 % | 2/24 |
| GLM-5.3 (partial) | 12/12 | 6/6 | 0/6 | 100 % | 83 % | 100 % | 100 % | 4/6 |

GLM stopped at 12 of 30: NVIDIA started responding with 429 to the long requests and the
run was cut so as not to hold up the rest.

## 4. Conclusion

1. **Detecting vague rules works.** All three models returned `ambiguous` for the 6 vague ones
   ("que sea claro", "evitar textos aburridos", "que no tenga errores" — make it clear, avoid boring texts, no errors), with a useful question
   ("¿a qué tipo de errores te referís?" — what kind of errors do you mean?), and none flagged a good rule as vague.
2. **Format is not a problem either**: 100 % valid schemas on the first attempt.
3. **What fails is judgment, not syntax.** Qwen compiles 14 of 24 rules exactly
   like the reference. The deviations are about interpretation: rules that apply to a block
   it puts at document level (numbered steps, opening hours), and it leaves tables out of a link
   rule. `blocking` and the standard always come out right, because the person states them.
4. **New problem: "deterministic" has no boundary.** gpt-oss marks as `deterministic` everything
   that in theory could be checked with code: acronyms, dates, "requirements go before
   the steps", tables without a header. Qwen does the same with dates. But a deterministic
   rule needs someone to write the code, and the compiler does not generate it: in the app
   those rules would go unevaluated. The concept has to be pinned down: `deterministic` only for a
   catalog of implemented checks (word count, percentage of uppercase, email
   format, length of a title), with their parameters; everything else, `semantic`.
5. **Compilation does not replace human review**, but it shortens it: 14 of 24 come out ready and
   the rest need one or two fields touched. This is what the SDD anticipates: the person reviews and
   saves.

### What was not measured
The plan included running the lab 13 evaluator on the compiled rules: on their own
examples and on the lab 13 gold set, comparing against the reference rule
(`run.py --evaluate`). It was left pending due to GPU time; the code is there.

### Limits
- 30 rules, written by the person who designed the reference: a real person's rules would be
  messier.
- The "reference" is also an opinion: in some deviations (dates as deterministic) the
  compiler has a point.
