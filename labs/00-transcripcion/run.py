"""Corta un tramo de un video y lo transcribe con mlx-whisper.

Uso:
    uv run labs/00-transcripcion/run.py VIDEO --desde 39:00 --hasta 49:00 --nombre entrevista

Genera, sin tocar el original:
    data/raw/<nombre>.mov              el recorte de video
    data/raw/<nombre>.wav              el audio mono 16 kHz que usa Whisper
    data/processed/<nombre>.txt        transcripción cruda, un segmento por línea con su tiempo
    data/processed/<nombre>.json       salida completa de Whisper (segmentos, tiempos, metadatos)
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

import mlx_whisper

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
MODELO = "mlx-community/whisper-large-v3-turbo"


def cortar(video: Path, desde: str, hasta: str, nombre: str) -> tuple[Path, Path]:
    clip = RAW / f"{nombre}.mov"
    audio = RAW / f"{nombre}.wav"
    # -ss/-to después de -i: corte exacto al segundo; se recodifica con el encoder de hardware
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-ss", desde, "-to", hasta,
         "-c:v", "h264_videotoolbox", "-b:v", "6M", "-c:a", "aac", str(clip)],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "16000",
         str(audio)],
        check=True,
    )
    return clip, audio


def mmss(segundos: float) -> str:
    m, s = divmod(int(segundos), 60)
    return f"{m:02d}:{s:02d}"


def transcribir(audio: Path, nombre: str) -> dict:
    inicio = time.perf_counter()
    resultado = mlx_whisper.transcribe(str(audio), path_or_hf_repo=MODELO, language="es")
    resultado["segundos_de_proceso"] = round(time.perf_counter() - inicio, 1)

    (PROCESSED / f"{nombre}.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
    lineas = [f"[{mmss(s['start'])}] {s['text'].strip()}" for s in resultado["segments"]]
    (PROCESSED / f"{nombre}.txt").write_text("\n".join(lineas) + "\n")
    return resultado


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("video", type=Path)
    p.add_argument("--desde", required=True, help="inicio del tramo, ej. 39:00")
    p.add_argument("--hasta", required=True, help="fin del tramo, ej. 49:00")
    p.add_argument("--nombre", required=True, help="nombre base de los archivos generados")
    args = p.parse_args()

    clip, audio = cortar(args.video, args.desde, args.hasta, args.nombre)
    print(f"recorte: {clip}\naudio:   {audio}")
    resultado = transcribir(audio, args.nombre)
    print(f"transcripción: {PROCESSED / f'{args.nombre}.txt'}")
    print(f"segmentos: {len(resultado['segments'])}, proceso: {resultado['segundos_de_proceso']} s")


if __name__ == "__main__":
    main()
