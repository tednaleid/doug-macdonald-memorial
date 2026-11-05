#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.12"
# dependencies = ["deepfilternet==0.5.6", "torch==2.1.2", "torchaudio==2.1.2", "numpy<2", "soundfile"]
# ///
# ABOUTME: Removes background noise from speech with DeepFilterNet 3, running locally.
# ABOUTME: Usage: enhance-deepfilter.py INPUT.wav OUTPUT.wav (48 kHz is the model's native rate).

import sys

from df.enhance import enhance, init_df, load_audio, save_audio


def main() -> None:
    source, destination = sys.argv[1], sys.argv[2]
    model, df_state, _ = init_df()
    audio, _ = load_audio(source, sr=df_state.sr())
    enhanced = enhance(model, df_state, audio)
    save_audio(destination, enhanced, df_state.sr())


if __name__ == "__main__":
    main()
