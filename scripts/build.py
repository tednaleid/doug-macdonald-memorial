#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# ABOUTME: Parses the Markdown Transcript into Talks, paragraphs, verse, and timed Lines, and writes the page.
# ABOUTME: Each Line gets Whisper's mean word confidence for review mode; the data is embedded in the HTML template.

import argparse
import json
import re
import sys
from pathlib import Path

TIMED = re.compile(r"^\[(\d+):(\d{2})\]\s+(.*)$")
PLACEHOLDER = "/*TRANSCRIPT_DATA*/null"


def fail(number: int, message: str) -> None:
    sys.exit(f"line {number}: {message}")


def parse(markdown: str) -> dict:
    markdown = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), markdown, flags=re.S)
    title, talks = "", []
    block = None  # the paragraph or verse block currently being filled

    def close_block() -> None:
        nonlocal block
        block = None

    for number, raw in enumerate(markdown.splitlines(), start=1):
        line = raw.rstrip()
        if line.count("{?") != line.count("?}"):
            fail(number, "a {?guess?} marker is not closed with ?}")
        if not line:
            close_block()
        elif line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            close_block()
            talks.append({"speaker": line[3:].strip(), "blocks": []})
        elif line.startswith("### "):
            close_block()
            talks[-1]["blocks"].append({"type": "heading", "text": line[4:].strip()})
        elif line.startswith(">"):
            text = line[1:].strip()
            if block is None or block["type"] != "verse":
                block = {"type": "verse", "lines": []}
                talks[-1]["blocks"].append(block)
            if not text:
                block["lines"].append(None)  # stanza break
            elif m := TIMED.match(text):
                block["lines"].append({"start": int(m[1]) * 60 + int(m[2]), "text": m[3]})
            elif block["lines"] and block["lines"][-1] is not None:
                block["lines"][-1]["text"] += "\n" + text
            else:
                fail(number, "a verse stanza must start with a [mm:ss] timestamp")
        elif m := TIMED.match(line):
            if not talks:
                fail(number, "a Line appears before the first ## Talk heading")
            if block is None or block["type"] != "paragraph":
                block = {"type": "paragraph", "lines": []}
                talks[-1]["blocks"].append(block)
            block["lines"].append({"start": int(m[1]) * 60 + int(m[2]), "text": m[3]})
        else:
            fail(number, f"expected a [mm:ss] Line, a heading, or verse: {line!r}")
    return {"title": title, "talks": talks}


def all_lines(data: dict) -> list[dict]:
    return [
        l
        for talk in data["talks"]
        for b in talk["blocks"]
        for l in b.get("lines", [])
        if l is not None
    ]


def add_confidence(data: dict, whisper_paths: list[Path]) -> None:
    words = sorted(
        (w for p in whisper_paths for s in json.loads(p.read_text())["segments"] for w in s["words"]),
        key=lambda w: w["start"],
    )
    lines = all_lines(data)
    for i, line in enumerate(lines):
        end = lines[i + 1]["start"] if i + 1 < len(lines) else float("inf")
        probabilities = [w["probability"] for w in words if line["start"] <= w["start"] < end]
        if probabilities:
            line["confidence"] = round(sum(probabilities) / len(probabilities), 2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("whisper", type=Path, nargs="*", help="Whisper JSON files for review-mode confidence")
    args = parser.parse_args()

    data = parse(args.transcript.read_text())
    starts = [l["start"] for l in all_lines(data)]
    for a, b in zip(starts, starts[1:]):
        if b < a:
            sys.exit(f"Line timestamps go backwards: {a // 60}:{a % 60:02d} then {b // 60}:{b % 60:02d}")
    add_confidence(data, args.whisper)
    for talk in data["talks"]:
        talk["start"] = next(l["start"] for b in talk["blocks"] for l in b.get("lines", []) if l)

    template = args.template.read_text()
    if PLACEHOLDER not in template:
        sys.exit(f"{args.template} has no {PLACEHOLDER} placeholder")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(template.replace(PLACEHOLDER, payload))
    print(f"wrote {args.output}: {len(data['talks'])} talks, {len(starts)} lines")


if __name__ == "__main__":
    main()
