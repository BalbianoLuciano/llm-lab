"""Descarga el corpus listado en corpus/urls.tsv a data/raw/corpus/.

Uso:
    uv run corpus/descargar.py            # baja lo que falte
    uv run corpus/descargar.py --forzar   # vuelve a bajar todo

Los archivos no se versionan (son de sus organismos). Lo que se versiona es la lista de URLs
y el manifiesto con el hash de cada descarga, para saber si un documento cambió en la fuente.
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
MANIFIESTO = ROOT / "corpus" / "manifiesto.json"
DESTINO = ROOT / "data" / "raw" / "corpus"
# Los sitios de la Provincia piden Crawl-delay 10 en su robots.txt
PAUSA_S = {"gba.gob.ar": 10, "gba.gov.ar": 10}
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) llm-lab/0.1 (investigacion)"


def bajar(url: str) -> tuple[bytes, str]:
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=60) as resp:
        return resp.read(), resp.headers.get_content_type()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--forzar", action="store_true", help="volver a bajar aunque exista")
    args = p.parse_args()

    DESTINO.mkdir(parents=True, exist_ok=True)
    manifiesto = json.loads(MANIFIESTO.read_text()) if MANIFIESTO.exists() else {}
    with URLS.open(newline="") as f:
        filas = list(csv.DictReader(f, delimiter="\t"))

    errores = []
    for fila in filas:
        archivo = DESTINO / f"{fila['id']}.{fila['formato']}"
        if archivo.exists() and not args.forzar:
            continue
        try:
            contenido, tipo = bajar(fila["url"])
        except Exception as e:  # noqa: BLE001 — se reporta y se sigue con el resto
            errores.append(f"{fila['id']}: {e}")
            continue
        archivo.write_bytes(contenido)
        manifiesto[fila["id"]] = {
            "url": fila["url"],
            "sha256": hashlib.sha256(contenido).hexdigest(),
            "bytes": len(contenido),
            "content_type": tipo,
            "descargado": date.today().isoformat(),
        }
        print(f"ok  {archivo.name} ({len(contenido) // 1024} KB)")
        host = urlparse(fila["url"]).hostname or ""
        time.sleep(next((s for d, s in PAUSA_S.items() if host.endswith(d)), 1))

    MANIFIESTO.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"\n{len(filas) - len(errores)}/{len(filas)} documentos en {DESTINO}")
    for e in errores:
        print(f"error  {e}")


if __name__ == "__main__":
    main()
