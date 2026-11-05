#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# ABOUTME: Turns Whisper word timings and diarization turns into a draft Markdown transcript of timed Lines.
# ABOUTME: Also reports diarized speech that has no transcribed words, to catch passages Whisper dropped.

import argparse
import json
from pathlib import Path

PARAGRAPH_GAP_SECONDS = 2.0
SENTENCE_END = (".", "?", "!")


def load_words(whisper_paths: list[Path]) -> list[dict]:
    """Loads words from the main pass plus any clip passes; a clip pass replaces the main pass's words in its span."""
    main, *clips = [json.loads(p.read_text())["segments"] for p in whisper_paths]
    words = [w for s in main for w in s["words"]]
    for clip in clips:
        clip_words = [w for s in clip for w in s["words"]]
        if not clip_words:
            continue
        lo, hi = clip_words[0]["start"], clip_words[-1]["end"]
        words = [w for w in words if w["end"] < lo or w["start"] > hi] + clip_words
    return sorted(words, key=lambda w: w["start"])


def split_sentences(words: list[dict]) -> list[dict]:
    sentences, current = [], []
    for w in words:
        current.append(w)
        if w["word"].strip().endswith(SENTENCE_END):
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    return [
        {
            "start": s[0]["start"],
            "end": s[-1]["end"],
            "text": "".join(w["word"] for w in s).strip(),
            "min_probability": min(w["probability"] for w in s),
        }
        for s in sentences
    ]


def speaker_for(sentence: dict, turns: list[dict]) -> str:
    overlap: dict[str, float] = {}
    for t in turns:
        o = min(sentence["end"], t["end"]) - max(sentence["start"], t["start"])
        if o > 0:
            overlap[t["speaker"]] = overlap.get(t["speaker"], 0.0) + o
    return max(overlap, key=overlap.get) if overlap else "UNKNOWN"


def timestamp(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"[{seconds // 60:02d}:{seconds % 60:02d}]"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diarization", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("whisper", type=Path, nargs="+", help="main pass first, then clip passes")
    args = parser.parse_args()

    turns = json.loads(args.diarization.read_text())["segments"]
    words = load_words(args.whisper)
    sentences = split_sentences(words)

    out, previous_speaker, previous_end = [], None, None
    for s in sentences:
        speaker = speaker_for(s, turns)
        if speaker != previous_speaker:
            out.append(f"\n<!-- {speaker} -->")
        elif previous_end is not None and s["start"] - previous_end > PARAGRAPH_GAP_SECONDS:
            out.append("")
        flag = " <!-- low -->" if s["min_probability"] < 0.3 else ""
        out.append(f"{timestamp(s['start'])} {s['text']}{flag}")
        previous_speaker, previous_end = speaker, s["end"]
    args.output.write_text("\n".join(out).lstrip() + "\n")
    print(f"wrote {len(sentences)} lines to {args.output}")

    for t in turns:
        if t["end"] - t["start"] < 3:
            continue
        covered = sum(
            max(0.0, min(t["end"], w["end"]) - max(t["start"], w["start"])) for w in words
        )
        if covered / (t["end"] - t["start"]) < 0.25:
            print(f"untranscribed speech: {timestamp(t['start'])}-{timestamp(t['end'])} {t['speaker']}")


if __name__ == "__main__":
    main()
