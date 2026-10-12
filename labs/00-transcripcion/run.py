"""Cut a segment out of a video and transcribe it with mlx-whisper.

Usage:
    uv run labs/00-transcripcion/run.py VIDEO --start 39:00 --end 49:00 --name interview

Produces, without touching the original:
    data/raw/<name>.mov              the video clip
    data/raw/<name>.wav              the 16 kHz mono audio Whisper uses
    data/processed/<name>.txt        raw transcript, one timestamped segment per line
    data/processed/<name>.json       full Whisper output (segments, timings, metadata)
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
MODEL = "mlx-community/whisper-large-v3-turbo"


def cut(video: Path, start: str, end: str, name: str) -> tuple[Path, Path]:
    clip = RAW / f"{name}.mov"
    audio = RAW / f"{name}.wav"
    # -ss/-to after -i: frame-accurate cut; re-encoded with the hardware encoder
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-ss", start, "-to", end,
         "-c:v", "h264_videotoolbox", "-b:v", "6M", "-c:a", "aac", str(clip)],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "16000",
         str(audio)],
        check=True,
    )
    return clip, audio


def mmss(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def transcribe(audio: Path, name: str) -> dict:
    start = time.perf_counter()
    result = mlx_whisper.transcribe(str(audio), path_or_hf_repo=MODEL, language="es")
    result["processing_seconds"] = round(time.perf_counter() - start, 1)

    (PROCESSED / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    lines = [f"[{mmss(s['start'])}] {s['text'].strip()}" for s in result["segments"]]
    (PROCESSED / f"{name}.txt").write_text("\n".join(lines) + "\n")
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("video", type=Path)
    p.add_argument("--start", required=True, help="segment start, e.g. 39:00")
    p.add_argument("--end", required=True, help="segment end, e.g. 49:00")
    p.add_argument("--name", required=True, help="base name for the generated files")
    args = p.parse_args()

    clip, audio = cut(args.video, args.start, args.end, args.name)
    print(f"clip:  {clip}\naudio: {audio}")
    result = transcribe(audio, args.name)
    print(f"transcript: {PROCESSED / f'{args.name}.txt'}")
    print(f"segments: {len(result['segments'])}, processing: {result['processing_seconds']} s")


if __name__ == "__main__":
    main()
