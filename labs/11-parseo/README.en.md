# Lab 11: Parsing

**The question:** how much of the structure of a real document (headings, lists, tables,
links) survives parsing, and what is lost depending on the format? Are hand-made
heuristics enough, or is a layout model like Docling's needed?

Everything that comes after rests on this. The traffic light evaluates **blocks**, chunking cuts
**by structure** and the guided review jumps **from block to block**. If parsing confuses
a list with a table or loses a heading, the rest inherits the error.

---

## 1. Concept

### A PDF has no paragraphs
A PDF is a list of drawing instructions: "put these letters, in this font, at this
position". It doesn't say what is a heading, what is a list or what is a table. All of that has to be **inferred**
from appearance: font size, bold, indentation, column alignment.

HTML and Word are the opposite: the structure is written in tags (`<h2>`, `<li>`,
`<table>`). The problem there is a different one: separating the content from the rest of the page (menu,
footer, "¿Te fue útil esta página?" ("Was this page helpful?")).

### The block
The output of parsing is an ordered list of **blocks** (`src/llm_lab/blocks.py`):

| Field | What it holds |
|---|---|
| `kind` | `heading`, `paragraph`, `list_item` or `table` |
| `text` | the block's text (empty for tables) |
| `level` | heading level: 1 is the highest |
| `rows` | the table's rows; the first one is the header |
| `links` | text and URL of each link |
| `path` | the headings that contain the block: `["Requisitos", "Documentación"]` |
| `page` | source page (PDF only) |

The `path` is what later lets a chunk say which section it comes from, and lets a traffic light
rule know whether a paragraph is under "Requisitos" ("Requirements") or under "Costos" ("Costs").

### Two ways to infer the structure of a PDF
- **Heuristics** (`manual_parser.py`, with PyMuPDF): the most frequent font size is the
  body; whatever is larger, or is bold and short, is a heading; whatever starts with a
  bullet or a number is an item; lines that repeat at the top or bottom across many pages are
  header or footer. Tables are detected by lines and alignment.
- **Layout model** (`docling_parser.py`): Docling runs each page through an object
  detector trained to recognize regions (heading, text, list, table, page
  header) and another model to reconstruct the grid of the tables. It runs on the Mac's GPU
  (MPS).

## 2. Method

- **Corpus:** the 49 documents in `corpus/urls.tsv` (29 PDF, 15 HTML, 4 DOC, 1 DOCX).
- **Two parsers, same output format:**
  - `manual_parser.py`: PyMuPDF for PDF, BeautifulSoup for HTML; DOC and DOCX are converted to HTML
    with `textutil` (ships with macOS).
  - `docling_parser.py`: Docling 2.138 without OCR, with heading hierarchy enabled (it comes
    disabled, and then all headings come out at level 1). `.doc` files are converted to `.docx`.
  - Both start from the same clean HTML (`html_main.py`: keeps `<main>` and discards
    menu, footer and forms), so the comparison measures structure and not page cleanup.
- **Gold set** (`gold.json`): 6 documents labeled by hand **looking at the original** (the
  PDF pages as images, the HTML as rendered text), not at a parser's output.
  They cover the three formats: a one-page PDF with a table, a 9-page designed
  instruction guide, a resolution, two web pages and a Word form.
- **Metrics:** heading recall and precision, list items recognized as items, tables
  found and with all their rows, extra tables, links with their URL, key data (amounts,
  dates, deadlines) present in the text, web noise that slipped in, and repeated page
  headers. The comparison ignores case, accents and punctuation.

```bash
uv run labs/11-parseo/run.py          # both parsers over the whole corpus
uv run labs/11-parseo/evaluate.py     # compares against the gold set and writes results.md
```

## 3. Results

The full numbers, document by document, are in [`results.md`](results.md).

Run of 2026-10-12, gold set of 6 documents:

| Metric | By hand | Docling |
|---|---|---|
| Headings found (recall) | 66 % | 63 % |
| Correct headings (precision) | 83 % | **88 %** |
| List items recognized | 86 % | **100 %** |
| Tables with all their rows | 1 of 2 | **2 of 2** |
| Extra tables | 3 | **1** |
| Links with their URL | 90 % | **100 %** |
| Key data present | 97 % | 97 % |
| Repeated page headers | **2** | 12 |

Whole corpus:

| | By hand | Docling |
|---|---|---|
| Total time | **86 s** | 1,491 s |
| Seconds per PDF page (median) | **0.06** | 0.40 |
| 269-page annex with tables | **33 s** | 1,268 s (21 min) |

### Where each one wins
- **On designed PDFs Docling wins.** In the ARBA instruction guide it finds all 9 headings and
  all 17 items; the hand-made parser finds 6 and 12.
- **On HTML they tie.** On 12 of the 15 pages both give exactly the same number of
  blocks. With clean HTML there is nothing to infer: `<h2>` is a heading and `<li>` is an item.
- **On Word the hand-made parser wins**, thanks to a single rule: a whole paragraph in bold and
  short is a heading. Docling doesn't recognize them and the SUBE form ends up with no headings.
- **Page headers: the hand-made parser wins.** Docling marks as a header what
  the model recognizes as such, but the design bands (the procedure's title repeated at the top
  of every page) it takes as headings. The rule "if it repeats on half the pages, it's a
  header" removes almost all of them.

### What was learned along the way
Each finding came from a measurement that came out wrong, not from reading documentation:

1. **PyMuPDF sees bulleted lists as tables.** `find_tables()` finds two aligned columns
   (bullet | text) and builds a table. In the gold set it detected 10 tables and 8 were
   false, almost all of them lists. The rule "if the first column is only bullets, it's a list",
   together with the one in point 2, brought missed items down from 15 to 5 and false tables from 8 to 3.
2. **The bullet can come on its own.** In the ARBA PDF each `●` is a separate line, in a different
   font. A regex that expects bullet, space and text never sees it.
3. **Docling splits inline text into pieces.** In HTML, every bold, link or comma is a separate
   child item, and list items end up with empty text and the content in an
   `InlineGroup`. Reading only each item's text, Docling recognized 1 item out of 9 on the fees
   page. Walking the tree, 9 out of 9.
4. **Docling doesn't clean web pages.** Without the `html_main.py` step, 6 of 8 noise markers
   (menu, useful phone numbers, "¿Te fue útil?" ("Was it helpful?")) stayed in the text and heading precision
   dropped to 65 %.
5. **Importing PyMuPDF in the same process as Docling makes it about 50 times slower.**
   A 14-page PDF took 459 s with `import pymupdf` and 9 s without it. The cause was not
   diagnosed; the fix was to run each parser in its own process (`run.py`).
6. **Hidden content is content too.** On the Registro Civil page, three
   sections are inside accordion buttons. The first version discarded `<button>` elements
   as noise and lost those sections.
7. **Large tables are expensive in Docling.** The table model runs page by page:
   the fee schedule annex (269 pages, almost all with tables) took 21 minutes.

## 4. Conclusion

1. **Docling for PDF, with our own rules around it.** On designed PDFs (most of the
   corpus) the layout model recognizes lists, tables and headings that the heuristics miss.
   But it's not enough on its own: the repeated-header filter and the bold-paragraph
   rule are needed, which are cheap and are taken from the hand-made version.
2. **HTML doesn't need a model.** BeautifulSoup plus good page cleanup gives
   the same result in milliseconds. The hard part of HTML is the cleanup, not the structure.
3. **Cost matters for ingestion.** 0.4 s per page is fine for procedure
   documents, but a 269-page annex takes 21 minutes. The app (lab 16) will need to
   process in the background and show progress.
4. **The data almost always survives; the structure doesn't.** Both parsers keep 97 %
   of the amounts, dates and deadlines. What gets lost is knowing whether an amount was in a table or
   in a paragraph, and under which heading. That's what the traffic light and chunking need.
5. **For the pipeline:** Docling for PDF; our own parser for HTML and for Word (DOC and DOCX
   run through `textutil`), and in every case the repeated-header filter. That
   combination is assembled in `src/llm_lab/` when lab 03 (chunking) uses it.

### Found later, while using the corpus in labs 02 and 03
- **HTML comments were slipping in as text.** BeautifulSoup treats `<!-- ... -->` as just
  another string; the hand-made parser didn't filter them, and things like `.entry-meta` or an
  entire commented-out `<script>` ("MODAL NO TOCAR", i.e. "MODAL DO NOT TOUCH") showed up. The gold set didn't catch it because those
  pages weren't in it. Fixed in `manual_parser.py`; the metrics don't change.
- **Docling splits some resolutions line by line.** An amount and its effective date
  ended up in different blocks. `src/llm_lab/corpus.py` re-joins two consecutive paragraphs
  when the first doesn't close the sentence and the second starts in lowercase; breaks
  followed by an uppercase letter, and those that cross a page break with the letterhead in
  between, are left unjoined.
- **ARBA's due-date calendar is useless as text**: it's a grid of days and it
  parses as a list of loose numbers. It would need its own parser or to be read as an image.

### Limits of this measurement
- The gold set has 6 documents. That's enough to see large differences (17 of 17 items
  versus 12 of 17), not to tell 63 % from 66 %.
- The hand-made parser's rules were tuned looking at that same set. They are general rules
  (bullets, bold, repetition), but a larger, separate gold set would validate them better.
- Reading order on two-column pages was not measured. The corpus has almost none.
