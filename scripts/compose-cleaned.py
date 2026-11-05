#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "soundfile"]
# ///
# ABOUTME: Builds the Cleaned audio by taking the enhanced speech everywhere except the kept ranges, which use the source.
# ABOUTME: Crossfades at each boundary so the switch is not audible; the output keeps the source's length and timeline.

import argparse

import numpy as np
import soundfile as sf

CROSSFADE_SECONDS = 0.5


def parse_range(text: str) -> tuple[float, float]:
    start, end = text.split("-")
    return float(start), float(end)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("enhanced")
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--keep", type=parse_range, action="append", default=[],
                        help="START-END seconds to take from the source, e.g. 2497-2622")
    args = parser.parse_args()

    source, rate = sf.read(args.source, dtype="float32")
    enhanced, enhanced_rate = sf.read(args.enhanced, dtype="float32")
    if enhanced_rate != rate:
        raise SystemExit(f"sample rates differ: {enhanced_rate} vs {rate}")
    enhanced = np.pad(enhanced, (0, max(0, len(source) - len(enhanced))))[: len(source)]

    # Weight of the source at each sample: 0 means enhanced speech, 1 means the untouched source.
    t = np.arange(len(source)) / rate
    source_weight = np.zeros(len(source), dtype=np.float32)
    for start, end in args.keep:
        ramp_in = np.clip((t - start) / CROSSFADE_SECONDS + 0.5, 0, 1)
        ramp_out = np.clip((end - t) / CROSSFADE_SECONDS + 0.5, 0, 1)
        source_weight = np.maximum(source_weight, np.minimum(ramp_in, ramp_out))

    mixed = enhanced * (1 - source_weight) + source * source_weight
    sf.write(args.output, mixed, rate)
    print(f"wrote {args.output} ({len(mixed) / rate:.1f}s)")


if __name__ == "__main__":
    main()
