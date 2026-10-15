# Lab 03: Chunking

**The question:** which way of cutting the documents retrieves the correct passage most often,
with the same embedding model and the same questions?

## 1. Concept

A **chunk** is the piece of a document that is turned into a vector, searched, and passed to the
model to answer. It is the unit of everything that follows: if the fact got split between two
chunks, neither of them brings it complete; if the chunk is huge, its vector "averages" many
topics and does not resemble any concrete question.

Two families:
- **Fixed size**: cut the text every N characters, with an overlap so as not to split
  sentences at the edge. It knows nothing about the structure.
- **Structure-based** (`src/llm_lab/chunking.py`): group consecutive blocks from the same section
  up to a cap, never splitting a block; tables are not cut (if they are long, they are split
  by rows, repeating the header), and each chunk is prefixed with **the document title
  and the heading path**. That way a chunk that says "$42.230,00" also says "Costos de los
  trámites (licencias de conducir) > Aranceles > Costos de los trámites".

## 2. Method

- Corpus: the 49 documents, parsed with what won in lab 11 (`src/llm_lab/corpus.py`).
- **Question set** (`evals/questions.jsonl`): 62 questions written by hand while reading the
  corpus, with words different from those in the text ("¿cuánto sale sacar la licencia por primera
  vez?" (how much does it cost to get a license for the first time?) for a text that says "Otorgamiento de Licencia de Conducir"). Each one has the
  exact evidence: a text fragment and the document where it is. Plus 10 questions with no
  answer in the corpus for lab 07. Each piece of evidence was verified to appear verbatim.
- **Hit**: a retrieved chunk is a hit if it is from the correct document and **contains the complete
  evidence**. If it cuts it in half, it does not count.
- Embeddings: `BAAI/bge-m3` local, cosine. Metrics: recall@k and MRR@10.

```bash
uv run labs/03-chunking/run.py
```

## 3. Results

Full numbers in [`results.md`](results.md).

| Strategy | Chunks | Recall@1 | Recall@5 | Recall@10 | MRR@10 | Characters in the top 5 |
|---|---|---|---|---|---|---|
| fixed 300 | 3,330 | 40 % | 65 % | 71 % | 0.50 | 1,488 |
| fixed 1000 / 200 | 1,263 | 58 % | **95 %** | **100 %** | 0.74 | 4,880 |
| fixed 2000 / 400 | 647 | 60 % | **95 %** | 98 % | 0.75 | 9,488 |
| one block per chunk | 4,254 | 65 % | 87 % | 90 % | 0.75 | 1,489 |
| structure 1000 | 1,881 | **66 %** | 92 % | 98 % | **0.77** | 2,940 |
| structure 1000 **without path** | 1,881 | 55 % | 81 % | 92 % | 0.66 | 2,665 |

## 4. Conclusion

1. **The heading path is what weighs the most.** Same cuts, with and without the path prepended:
   recall@1 from 55 % to 66 % and recall@5 from 81 % to 92 %. A block that says "$ 17540,00" does not
   resemble "¿cuánto cuesta la partida urgente?" (how much does the urgent certificate cost?); with "Solicitud de partidas urgentes > Costos
   del trámite" in front, it does.
2. **Small chunks cut the evidence.** With fixed 300 characters, 18 questions are not
   found even in the top 10: the fact got split or separated from what names it.
3. **Structure wins at the top, large fixed size wins at the bottom.** Structure 1000 has
   the best recall@1 and MRR; fixed 1000 reaches 100 % in the top 10, but each chunk is almost
   twice as long. For RAG it matters more that the right one comes first (the model reads the top 5)
   and that there is less text to read: **structure 1000** is the choice, and lab 05 (re-ranking)
   tackles precisely the ordering.
4. **One block per chunk falls short**: good recall@1, but it loses context (q01 and q02 are not
   found: the amount is in one block and what is being paid for, in another, the same thing seen in
   lab 02).

### Limits
- 62 questions: differences of 2 or 3 points (one or two questions) are not conclusive.
- The questions were written by someone who knows the corpus; real users ask worse questions.
