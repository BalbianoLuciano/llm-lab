"""Lab 11: parse the corpus with both parsers and save the blocks.

    uv run labs/11-parseo/run.py                   # both parsers, whole corpus
    uv run labs/11-parseo/run.py --parser manual
    uv run labs/11-parseo/run.py --only caba-licencias-aranceles

Output: data/processed/blocks/<parser>/<id>.json. Already parsed files are skipped (--force).
"""

import argparse
import importlib
import subprocess
import sys
import time
from pathlib import Path

from llm_lab.blocks import Document

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "raw" / "corpus"
OUT = ROOT / "data" / "processed" / "blocks"
TMP = ROOT / "data" / "interim" / "converted"
# Each parser runs in its own process: with PyMuPDF imported in the same process, Docling
# took 459 s on a 14-page PDF that it parses in 9 s on its own (lab 11 finding).
PARSERS = {"manual": "manual_parser", "docling": "docling_parser"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--parser", choices=PARSERS, action="append")
    p.add_argument("--only", action="append", help="document id (repeatable)")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    files = sorted(f for f in CORPUS.iterdir() if f.suffix in (".pdf", ".html", ".doc", ".docx"))
    if args.only:
        files = [f for f in files if f.stem in args.only]

    names = args.parser or list(PARSERS)
    if len(names) > 1:
        for name in names:
            rest = [a for a in sys.argv[1:] if a not in names and a != "--parser"]
            subprocess.run([sys.executable, __file__, "--parser", name, *rest], check=True)
        return

    name = names[0]
    parse = importlib.import_module(PARSERS[name]).parse
    for file in files:
        dest = OUT / name / f"{file.stem}.json"
        if dest.exists() and not args.force:
            continue
        start = time.perf_counter()
        try:
            blocks, pages = parse(file, TMP)
        except Exception as e:  # noqa: BLE001 — report it and move on
            print(f"{name:8} ERROR {file.name}: {type(e).__name__}: {e}", flush=True)
            continue
        secs = round(time.perf_counter() - start, 2)
        Document(file.stem, file.suffix.lstrip("."), name, pages, secs, blocks).save(dest)
        kinds = {k: sum(b.kind == k for b in blocks) for k in ("heading", "list_item", "table")}
        print(f"{name:8} {secs:6.1f}s {file.name:55} {len(blocks):4} blocks {kinds}", flush=True)


if __name__ == "__main__":
    main()
