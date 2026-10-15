# RAG map: from a document to an answer with citations

One page to place each piece before building it. Each section says what it is, what
decision has to be made, what goes wrong and in which lab it is built and measured.

**RAG** (*Retrieval-Augmented Generation*): instead of hoping the model "knows" the
answer, you first **search** for the piece of the document that contains it and pass it to the model
along with the question. The model goes from remembering to reading.

```
INDEXING (once per document)                      QUERY (each question)

file                                              question
  │ 1. parsing                                      │ 6. embedding of the question
  ▼                                                 ▼
blocks (headings, paragraphs, tables)             question vector
  │ [traffic light: evaluate and fix]               │ 7. search (+ filters)
  │ 2. chunking                                     ▼
  ▼                                               top-k candidate chunks
chunks (pieces of ~300-800 tokens + metadata)       │ 8. re-ranking
  │ 3. embeddings                                   ▼
  ▼                                               top-n relevant chunks
vectors (lists of ~1000 numbers)                    │ 9. generation
  │ 4. indexing                                     ▼
  ▼                                               answer with citations
vector database ────────────────────────────────►   │ 10. evaluation
```

---

## 1. Parsing: from the file to blocks
- **What it is**: reading PDF, DOCX, HTML or MD and keeping the text **and its structure**: what is
  a heading, what is a table, which section each paragraph is in.
- **Why it matters**: a PDF has no "paragraphs". It has letters positioned on a page.
  Reconstructing the reading order, the tables and the headings is a problem in itself.
- **What goes wrong**: tables that turn into number soup, mixed-up columns, colored
  text that loses its emphasis, page headers and footers repeated in every chunk.
- **Lab**: 11.

## 2. Chunking: from blocks to retrievable pieces
- **What it is**: splitting the document into pieces (*chunks*). Each chunk is the unit that is
  searched for and passed to the model.
- **Why not index the whole document**: a vector sums up an entire text in a single
  "direction". A 20-page document talks about many things and its vector doesn't resemble
  any specific question. A small chunk talks about a single thing.
- **The decisions**:
  - **Size**: small is precise but loses context; large has context but dilutes the
    meaning and takes up more room in the prompt.
  - **Overlap**: repeating the end of one chunk at the start of the next, so as not to split
    an idea in half.
  - **Where to cut**: by number of tokens (simple), by sentences or by the structure of the
    document (section, table). We cut by structure, because we already have blocks.
  - **What to add**: each chunk carries its **heading path** ("Licencia > Renovación >
    Aranceles", i.e. License > Renewal > Fees) prepended to it. That way "el arancel es de $ 18.500" ("the fee is $ 18.500") knows which procedure it is about.
  - **Metadata**: document, version, page, section, permissions. Used for filtering and citing.
- **What goes wrong**: a table split in half, an answer spread over two chunks, chunks
  that say "see above".
- **Lab**: 03 (size and overlap, measured).

## 3. Embeddings: from text to vectors
- **What it is**: a model (different from the LLM that generates) that turns a text into a vector of,
  for example, 1024 numbers. Texts with similar meaning end up close together in that space:
  "¿cuánto sale renovar el registro?" ("how much does renewing the license cost?") ends up close to "arancel de renovación de la licencia de
  conducir" ("driver's license renewal fee"), even though they share no words.
- **How "close" is measured**: cosine similarity (the angle between the vectors) or inner
  product. With normalized vectors they are the same thing.
- **The decisions**: which model (it has to be multilingual for Spanish), which dimension, and
  whether to add **sparse** vectors (keyword-like) on top of the dense ones.
- **What goes wrong**: numbers, acronyms and proper names ("CIT", "ARBA", "F.931") are poorly
  represented in dense vectors. That's why hybrid search exists.
- **Lab**: 04.

## 4. Indexing: the vector database
- **What it is**: storing millions of vectors in a way that finding "the 10 closest" doesn't
  require comparing against all of them.
- **How it works**: exact search compares against all of them (O(n)) and is slow at scale. **ANN**
  indexes (*approximate nearest neighbors*) such as **HNSW** build a layered graph of neighbors
  and navigate it: much faster, at the cost of missing a neighbor every now and
  then (recall below 100 %).
- **Besides the vector**: each point stores a *payload* (the chunk's metadata). Filtering
  by payload **during** the search (for example, only chunks the user is allowed to see) is
  what sets a vector database apart from a numpy array.
- **Lab**: 12 (exact with numpy → home-made HNSW → Qdrant).

## 5. The traffic light (this project's own piece)
- It sits **between parsing and chunking**: if a block breaks a blocking rule, the
  document is not indexed until it is fixed. The hypothesis is that indexing better-written
  content improves everything that comes after.
- **Labs**: 13, 14 and 15.

## 6–7. Search: from the question to the candidate chunks
- The question is turned into a vector **with the same embedding model** and the
  *k* closest chunks are searched for.
- **Hybrid search**: vector search (meaning) is combined with word-based search
  (BM25: term frequency). One finds "cuánto sale" ("how much is it") ≈ "arancel" ("fee") and the other
  finds "F.931" exactly. The two rankings are fused (for example with RRF, *reciprocal
  rank fusion*).
- **Filters**: permissions, document type, validity. They go in the database query, never in
  the prompt.
- **Labs**: 04 and 12.

## 8. Re-ranking
- **What it is**: a second model (*cross-encoder*) that reads the question and each candidate chunk
  **together** and gives them a relevance score. It is much more precise than comparing vectors,
  but also slower, which is why it is only applied to the top-k (for example 30) to keep
  the top-n (for example 5).
- **Why it works better**: the embedding sums up question and chunk separately; the
  cross-encoder sees both at once and can notice that the chunk talks about the right
  procedure but the wrong year.
- **Lab**: 05.

## 9. Generation
- The final prompt has: instructions (answer only with what the fragments say, cite
  the source, if it's not there say you don't know), the top-n chunks with an identifier, and the
  question.
- **What goes wrong**: the model mixes what it read with what it "knows", cites a chunk that doesn't say
  that, or answers even though the chunks don't contain the answer.
- **Labs**: 06 (faithfulness and citations) and 07 (when to say "I don't know").

## 10. Evaluation
A RAG is evaluated in parts, because if the answer is wrong you need to know **where** it failed:

| Stage | Question | Metric |
|---|---|---|
| Retrieval | Is the chunk with the answer among the retrieved ones? | recall@k, MRR |
| Re-ranking | Did it end up on top? | MRR, nDCG |
| Generation | Is what the answer says backed by the cited chunks? | faithfulness |
| Generation | Does it answer what was asked? | relevance, accuracy against the expected answer |
| System | Does it say "I don't know" when the information isn't there? | correct abstention rate |

Everything is measured on a **fixed set of questions with their answer and their correct passage**, which is
built once and reused across all labs. Without that set, any change "looks better" and you don't
know whether it is.
- **Labs**: 06, 07 and 10.
