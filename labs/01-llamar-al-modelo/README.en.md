# Lab 01: Calling the model

**The question:** what changes when you vary the model, the system prompt, the temperature and the max
length, measured on the same 20 questions? Which free model do we use in the rest of the
lab?

Everything that comes after (compiling rules, rewriting blocks, answering in the RAG) is a
call to a model. Before building on top of it, you need to understand what happens in that call.

---

## 1. Concept

### What an LLM call is
An LLM is a function that takes a sequence of **tokens** and returns a probability
distribution over what the **next token** is. Generating text means repeating that: pick a
token, append it to the sequence, ask for the next one again, until the model emits an
end token or the max length is reached.

A **token** is a piece of a word. "Arancel" ("fee") can be one token or two, depending on the
model's vocabulary. Everything is measured in tokens: cost, usage limits and the maximum
context length.

### The chat protocol
APIs don't take loose text but a list of **messages**, each with a role:

```python
[
    {"role": "system", "content": "Sos un asistente que responde usando solo el texto dado."},
    {"role": "user", "content": "Texto: ...\n\nPregunta: ¿cuánto cuesta?"},
]
```

- **system**: background instructions. Defines how the model behaves throughout the whole
  conversation.
- **user**: what the person (or our program) asks for.
- **assistant**: what the model answered before. Used to keep a conversation going or to
  give examples.

Under the hood, the provider flattens that list into a single text with special markers (the *chat
template*) and passes it to the model. The model doesn't "know" what a role is: it learned during
training to give more weight to what comes marked as system.

### The parameters we are going to move
- **temperature**: how the next token is chosen from the probabilities. At 0 the
  most likely one is always chosen (almost deterministic output). With high values the
  distribution flattens and less likely tokens come out: more variety, more errors.
- **max_tokens**: the cap on output tokens. If it is reached, the answer is cut off wherever it is.
- **The model**: size, training and whether it **reasons** before answering.

### Reasoning models
Some models (gpt-oss, GLM, Kimi) first write an internal reasoning that is not
shown in the answer, and then answer. Those tokens **count as output** and
**consume max_tokens**. In the initial test, GLM-5.3 used 107 output tokens to
answer "NO". This has consequences for cost, latency and truncation (experiment D).

### A single client for all providers
Groq, NVIDIA, Gemini and OpenRouter expose the same protocol as OpenAI (`/chat/completions`).
That's why `src/llm_lab/models.py` uses the `openai` SDK and only changes the base URL and the key. If
a provider answers 429 (rate limit) or 5xx, it moves on to the next one in the chain.

## 2. Method

- **20 fixed questions** in `questions.jsonl`, about short texts on government procedures written for
  this lab: data extraction (amounts, dates, deadlines), traffic light rule checks
  (R3, R5, R6, R7, R14), questions whose answer **is not** in the text (to see whether the
  model makes things up) and two simple reasoning ones.
- Each question asks for an exact format (a number, SI/NO, a date, `NO_INFO`), so
  grading is automatic: the normalized answer is compared with the expected one.
- Four experiments:

| | What varies | What is fixed |
|---|---|---|
| A | 6 free models | temperature 0, with system prompt |
| B | temperature 0 / 0.7 / 1.5, with 3 repetitions | fast model (Qwen3.8-27B on Groq) |
| C | with and without system prompt | one non-reasoning model and one reasoning model |
| D | max_tokens 16 / 64 / 512 / no cap | gpt-oss-120b (reasons) |

Each call is saved to `runs.jsonl` as soon as it finishes, so an interrupted run resumes
without repeating calls (and without spending quota). The script respects a per-provider pause so as not to
exceed the per-minute limit.

```bash
uv run labs/01-llamar-al-modelo/run.py
```

## 3. Results

The numbers from each run are in [`results.md`](results.md).

Run of 2026-10-11: 458 calls, US$ 0.

**A. Models.** All 6 get 20/20. What separates them is speed and how much they spend:

| Model | Correct | p50 latency | p50 output tokens | Reasons |
|---|---|---|---|---|
| Groq · qwen3.8-27b | 100 % | **0.23 s** | 2 | no |
| Groq · gpt-oss-120b | 100 % | 0.57 s | 102 | yes |
| OpenRouter · nemotron-3-super | 100 % | 1.13 s | 68 | yes |
| NVIDIA · glm-5.3 | 100 % | 1.89 s | 62 | yes |
| Gemini · 3.5-flash | 100 % | 2.25 s | 1 | not visible |
| NVIDIA · kimi-k3 | 100 % | 6.34 s | 50 | yes |

**B. Temperature** (qwen3.8-27b, 3 repetitions per question):

| Temperature | Correct | Same answer in all 3 repetitions |
|---|---|---|
| 0 | 100 % | 20/20 |
| 0.7 | 95 % | 17/20 |
| 1.5 | 82 % | 12/20 |

At 0.7 the errors are judgment errors: it swaps SI for NO on the most subjective rules (active voice,
acronyms). At 1.5 it also breaks the format: "18.500" instead of "18500", made-up JSON, text
in Portuguese, "DO" instead of "NO".

**C. System prompt.** No measurable effect: 100 % with and without. The questions already ask for the exact
format, so the background instruction adds nothing in tasks like these.

**D. Max length** (gpt-oss-120b, which reasons):

| max_tokens | Correct | Empty answers |
|---|---|---|
| 16 | 0 % | 20/20 |
| 64 | 0 % | 20/20 |
| 512 | 100 % | 0/20 |
| no cap | 100 % | 0/20 |

The model spends about 100 tokens reasoning before writing "NO". With a cap of 16 or 64 it gets
cut off mid-reasoning and **the answer arrives empty**, with no error. This is the most
important result of the lab.

## 4. Conclusion

1. **The set is too easy.** All 6 models score 100 %, so it can't be used to choose based on
   quality: there is a *ceiling effect*. That's expected with one-sentence texts written to order. The
   hard questions will come from the real corpus (confusing tables, acronyms, relative
   dates), and the quality comparison is repeated in labs 02 and 13.
2. **Temperature 0 for everything that is evaluated or extracted.** Raising it adds nothing in these
   tasks: it lowers accuracy and makes the result irreproducible. It is reserved for when
   variety is needed (for example, proposing several rewrites of a block).
3. **With reasoning models, never a small max_tokens.** The reasoning consumes the cap and
   the answer arrives empty with no error. In `models.py` the cap defaults to `None`, and
   an empty answer has to be treated as a failure.
4. **Reasoning tokens cost.** gpt-oss uses 50 times more output tokens than Qwen
   for the same "NO". When it's free that doesn't matter, but with daily token limits it shows:
   the Groq quota runs out faster.
5. **The choice, for now:** qwen3.8-27b on Groq as the default model for short tasks
   (the fastest and the cheapest in tokens), and gpt-oss-120b or glm-5.3 as fallback and for
   tasks that need reasoning. Kimi K3 is too slow to use in a loop.
6. **The free limits are felt.** 25 calls got 429 and recovered when the run was
   re-run. The script needs to be able to resume where it left off, plus the fallback chain.
