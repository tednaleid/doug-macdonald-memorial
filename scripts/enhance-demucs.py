#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["demucs==4.0.1", "torch<2.9", "torchaudio<2.9", "soundfile"]
# ///
# ABOUTME: Separates voices from background sound with Demucs (htdemucs), keeping the vocals stem.
# ABOUTME: Usage: enhance-demucs.py INPUT.wav OUTPUT.wav

import shutil
import sys
import tempfile
from pathlib import Path

import demucs.separate


def main() -> None:
    source, destination = Path(sys.argv[1]), Path(sys.argv[2])
    with tempfile.TemporaryDirectory() as tmp:
        demucs.separate.main(
            ["--two-stems", "vocals", "-n", "htdemucs", "-d", "cpu", "-o", tmp, str(source)]
        )
        shutil.move(Path(tmp) / "htdemucs" / source.stem / "vocals.wav", destination)


if __name__ == "__main__":
    main()
