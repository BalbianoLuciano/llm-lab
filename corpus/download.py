"""Download the corpus listed in corpus/urls.tsv into data/raw/corpus/.

Usage:
    uv run corpus/download.py           # download what's missing
    uv run corpus/download.py --force   # download everything again

The files themselves are not versioned (they belong to their agencies). What gets versioned is
the URL list and the manifest with each download's hash, to tell whether a document changed at
the source.
"""

import argparse
import csv
import hashlib
import json
import time
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
URLS = ROOT / "corpus" / "urls.tsv"
MANIFEST = ROOT / "corpus" / "manifest.json"
DEST = ROOT / "data" / "raw" / "corpus"
# The Province sites ask for Crawl-delay 10 in their robots.txt
DELAY_S = {"gba.gob.ar": 10, "gba.gov.ar": 10}
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) llm-lab/0.1 (research)"


def fetch(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as resp:
        return resp.read(), resp.headers.get_content_type()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="download again even if it exists")
    args = p.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    with URLS.open(newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    errors = []
    for row in rows:
        file = DEST / f"{row['id']}.{row['format']}"
        if file.exists() and not args.force:
            continue
        try:
            content, content_type = fetch(row["url"])
        except Exception as e:  # noqa: BLE001 — report it and move on
            errors.append(f"{row['id']}: {e}")
            continue
        file.write_bytes(content)
        manifest[row["id"]] = {
            "url": row["url"],
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
            "content_type": content_type,
            "downloaded": date.today().isoformat(),
        }
        print(f"ok  {file.name} ({len(content) // 1024} KB)")
        host = urlparse(row["url"]).hostname or ""
        time.sleep(next((s for d, s in DELAY_S.items() if host.endswith(d)), 1))

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"\n{len(rows) - len(errors)}/{len(rows)} documents in {DEST}")
    for e in errors:
        print(f"error  {e}")


if __name__ == "__main__":
    main()
