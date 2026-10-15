"""Turn podcast/guion.md into an MP3 with the macOS voices (`say`) and ffmpeg. Free, local.

    uv run podcast/render.py
    uv run podcast/render.py --ana Isabela --tomas Diego    # Argentine voices, if installed
                                                            # (System Settings > Accessibility
                                                            #  > Spoken Content > Manage voices)
Output: data/podcast/semaforo-podcast.mp3
"""

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "podcast" / "guion.md"
OUT = ROOT / "data" / "podcast" / "semaforo-podcast.mp3"
TURN_PAUSE_S = 0.35
SECTION_PAUSE_S = 1.2


def turns(text: str) -> list[tuple[str, str]]:
    """(speaker, line) pairs; ("PAUSA", "") for section breaks."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line == "[pausa]":
            out.append(("PAUSA", ""))
        elif m := re.match(r"(ANA|TOMÁS):\s*(.+)", line):
            out.append((m.group(1), m.group(2)))
    return out


def silence(seconds: float, path: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=22050:cl=mono", "-t", str(seconds), str(path)], check=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ana", default="Paulina")
    p.add_argument("--tomas", default="Eddy (Spanish (Mexico))")
    p.add_argument("--rate", type=int, default=182, help="words per minute")
    args = p.parse_args()
    voices = {"ANA": args.ana, "TOMÁS": args.tomas}

    tmp = Path(tempfile.mkdtemp())
    pieces: list[Path] = []
    silence(TURN_PAUSE_S, tmp / "turn.wav")
    silence(SECTION_PAUSE_S, tmp / "section.wav")
    for i, (speaker, line) in enumerate(turns(SCRIPT.read_text())):
        if speaker == "PAUSA":
            pieces.append(tmp / "section.wav")
            continue
        aiff, wav = tmp / f"{i:03}.aiff", tmp / f"{i:03}.wav"
        subprocess.run(["say", "-v", voices[speaker], "-r", str(args.rate), "-o", str(aiff),
                        line], check=True)
        # same format for every piece so the concat demuxer can join them
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(aiff), "-ar", "22050",
                        "-ac", "1", str(wav)], check=True)
        pieces += [wav, tmp / "turn.wav"]
        print(f"{i:3} {speaker:6} {line[:60]}", flush=True)

    playlist = tmp / "list.txt"
    playlist.write_text("".join(f"file '{p}'\n" for p in pieces))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i",
                    str(playlist), "-ar", "44100", "-ac", "1", "-b:a", "96k", str(OUT)],
                   check=True)
    shutil.rmtree(tmp)
    duration = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                               "-of", "csv=p=0", str(OUT)], capture_output=True, text=True,
                              check=False)
    minutes = float(duration.stdout or 0) / 60
    print(f"\n{OUT} · {minutes:.1f} minutos")


if __name__ == "__main__":
    main()
