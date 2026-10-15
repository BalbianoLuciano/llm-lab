# Lab 15: Guided review

**The question:** when a block is red and the person answers what is missing, how many
rewrites turn green without inventing data?

## 1. Concept

The document is not indexed until it passes the traffic light, so correcting has to be fast
(SDD §5.4): the person answers a concrete question ("¿desde cuándo rige este monto?", since when is this amount in force?) and an
LLM rewrites **only that block**. The risk is that the model fills in what is missing with something
plausible and false. That is why each rewrite goes through:

- **Re-evaluation** with the same rule and the lab 13 evaluator (Qwen3.5-4B via logprobs).
- **Deterministic guardrail** (`src/llm_lab/review.py`): numbers in the rewrite that are
  neither in the original block nor in the person's answer.
- **Evaluator guardrails**: "does it add data that is not in the original or in the
  answer?" and "does it change the meaning?", with the same logprobs mechanism.
- If the answer does not contain the fact, the instruction is to leave the block as it is and add a
  visible `[FALTA: ...]` marker.

## 2. Method

- 20 red blocks from the lab 13 gold set (effective date, currency, links, active voice, dates,
  tables), each one with a **simulated answer** from the person that contains the fact. The values
  in those answers are **made up for the test, not official** (for example, the value of
  the Unidad Tarifaria).
- 10 **traps**: the same kinds of block, with answers that do not contain the fact ("no sé,
  poné lo que corresponda" (I don't know, put whatever applies), "ponele el año que sea" (just put any year)).
- Rewriting with Qwen3.8-27B on Groq.

```bash
uv run labs/15-revision-guiada/run.py
```

## 3. Results

All the befores and afters are in [`results.md`](results.md).

| | Useful answer (20) | Trap (10) |
|---|---|---|
| Red before, according to the evaluator | 15 | 10 |
| **Green after correcting** | **12** | 0 |
| No longer red | 16 | 1 |
| Left the [FALTA] marker | 1 | **10** |
| Numbers that were neither in the original nor in the answer | 3 | **0** |
| Evaluator "adds data" guardrail in red | 5 | 9 |

## 4. Conclusion

1. **With the traps, the model invented nothing.** In all 10 it left `[FALTA: ...]` and no
   new number. The explicit instruction ("si no está, no lo inventes, marcalo", if it isn't there, don't invent it, mark it) works with
   this model; it is the most important property of the guided review.
2. **With a useful answer, 12 of 20 end up green and 16 stop being red.** The 8 that do not
   pass: the 3 tables in UT (see point 3), two active-voice blocks and the broken-apart index,
   which stay yellow, a correctly fixed date that the evaluator leaves yellow, and a
   correctly fixed link ("Hacé click en la guía del IVC sobre los cambios del DNU 70/2023", click on the IVC guide about the changes of DNU 70/2023)
   that the evaluator still sees as red. In those last two, the evaluator fails, not the
   rewrite.
3. **New problem: "inventing" and "calculating" look the same.** The 3 cases with new numbers
   are currency ones: the person said how much the UT is worth and the model **multiplied** (1,006 UT ×
   $1,250 = $1,257,500). The calculations are all correct, but the deterministic guardrail cannot
   tell them apart from an invented number, and a calculation error would pass as official data. A
   choice has to be made: forbid the model from calculating (add "1 UT = $1.250" just once) or verify
   the arithmetic in code. The first is safer.
4. **New problem: the evaluator guardrail is useless as it stands.** It flagged "adds data"
   in 9 of the 10 traps, where nothing was added: it takes the `[FALTA]` marker as an addition.
   In total, 11 false alarms and no hit that the deterministic one did not already have. A guardrail
   that always fires gets ignored. **The app uses the deterministic one** (new numbers and
   dates) and the evaluator one is left out until the question is reworded.
5. **New problem, the most serious: changing the voice can change who acts.** In c15 the
   original says that **the authority** must retain the offender's license. To "address
   the reader in active voice", the model wrote "Si poseés licencia habilitante, **debés
   retenerla**" (If you hold a valid license, **you must retain it**). The meaning changed completely, no number is new and the meaning
   guardrail rated it green. Writing rules (R14) applied to regulatory text, which
   does not address the citizen, are dangerous: the rule should apply only to instructions
   for whoever carries out the procedure, and these corrections always need human acceptance with
   the before and after in view.
6. **The evaluator is still the bottleneck**: of the 20 blocks that according to the gold
   labels were red, the evaluator saw 15 as red. It is the same ~70 % red recall as in
   lab 13.

### Limits
- The "person's" answers were written by Claude; a real person answers more briefly,
  with errors and sometimes off topic.
- 30 cases: enough to see behaviors (traps, calculations), not for fine-grained percentages.
