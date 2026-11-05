#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["mlx-whisper==0.4.3"]
# ///
# ABOUTME: Transcribes the memorial audio locally with Whisper large-v3 on Apple Silicon (mlx-whisper).
# ABOUTME: Writes segments with word-level timestamps and confidence to a JSON file.

import argparse
import json
from pathlib import Path

import mlx_whisper

MODEL = "mlx-community/whisper-large-v3-mlx"

# Names and terms established for this service; only confirmed spellings belong here.
VOCABULARY_PROMPT = (
    "Memorial service for Doug MacDonald (Norman Douglas MacDonald). "
    "Speakers include Sharon, Joe Cosgrove, Ray, Alex, and Amy. "
    "Family: Amy, Alex, Hazel, Ted, Lisa. "
    "Normandale Community College, geography and geology, the Coast Guard reserve, "
    "Semper Paratus, Yorktown, Canyonlands, Confluence Overlook, "
    "Tennyson, Crossing the Bar."
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--clip", default="0", help="seconds to transcribe, e.g. '2620,2690'")
    args = parser.parse_args()

    result = mlx_whisper.transcribe(
        str(args.audio),
        path_or_hf_repo=MODEL,
        language="en",
        initial_prompt=VOCABULARY_PROMPT,
        word_timestamps=True,
        condition_on_previous_text=True,
        hallucination_silence_threshold=2.0,
        clip_timestamps=args.clip,
        verbose=False,
    )

    segments = [
        {
            "start": round(s["start"], 2),
            "end": round(s["end"], 2),
            "text": s["text"].strip(),
            "avg_logprob": round(s["avg_logprob"], 3),
            "no_speech_prob": round(s["no_speech_prob"], 3),
            "words": [
                {
                    "word": w["word"],
                    "start": round(w["start"], 2),
                    "end": round(w["end"], 2),
                    "probability": round(w["probability"], 3),
                }
                for w in s.get("words", [])
            ],
        }
        for s in result["segments"]
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"model": MODEL, "segments": segments}, indent=1))
    print(f"wrote {len(segments)} segments to {args.output}")


if __name__ == "__main__":
    main()
