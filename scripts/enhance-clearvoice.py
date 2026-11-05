#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["clearvoice"]
# ///
# ABOUTME: Enhances speech with ClearerVoice-Studio's MossFormer2 48 kHz model, running locally.
# ABOUTME: Usage: enhance-clearvoice.py INPUT.wav OUTPUT.wav

import sys

from clearvoice import ClearVoice


def main() -> None:
    source, destination = sys.argv[1], sys.argv[2]
    model = ClearVoice(task="speech_enhancement", model_names=["MossFormer2_SE_48K"])
    enhanced = model(input_path=source, online_write=False)
    model.write(enhanced, output_path=destination)


if __name__ == "__main__":
    main()
