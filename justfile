# ABOUTME: Task runner for the Doug MacDonald memorial transcript and audio.
# ABOUTME: Run `just` to list recipes. Intermediate files go in work/ (gitignored); the page is built into site/.

recording := "audio/recording.m4a"
speech_wav := "work/speech-16k.wav"
source_wav := "work/source-48k.wav"
diarization_prototype := env("DIARIZATION_PROTOTYPE", "../../misc/diarization-prototype")
whisper := "data/whisper.json data/whisper-closing.json"

# Volume leveling applied after any noise reduction, so speakers at different distances sound alike
leveling := "highpass=f=80,dynaudnorm=f=200:g=11:p=0.9:m=15,loudnorm=I=-18:TP=-1.5:LRA=7"

# The Piping, in seconds; the Cleaned audio leaves it untouched apart from leveling
piping := "2497-2622"

# List available recipes
default:
    @just --list

# Build the page from transcript.md into site/index.html
build:
    ./scripts/build.py transcript.md page/template.html site/index.html {{whisper}}

# Build and open the page in the browser (add review=1 to see guesses and unsure Lines)
open review="": build
    open "site/index.html{{ if review != "" { "?review" } else { "" } }}"

# Make the 16 kHz mono, loudness-normalized WAV used for transcription and diarization
prepare:
    mkdir -p work
    ffmpeg -hide_banner -loglevel error -y -i {{recording}} -ac 1 -ar 16000 -af "highpass=f=80,loudnorm=I=-20:TP=-2:LRA=11" {{speech_wav}}

# Transcribe with Whisper large-v3, plus a separate pass over Sharon's closing remarks after the Piping
transcribe: prepare
    ./scripts/transcribe.py {{speech_wav}} data/whisper.json
    ./scripts/transcribe.py {{speech_wav}} data/whisper-closing.json --clip 2620,2682

# Find speaker turns with the pyannote diarization prototype (writes data/diarization.json)
diarize: prepare
    cd {{diarization_prototype}} && just diarize-unlocked dougmemorial --min-speakers 4 --max-speakers 8 --wav {{justfile_directory()}}/{{speech_wav}}
    mv {{diarization_prototype}}/out/dougmemorial.diarization.json data/diarization.json

# Write a first-draft transcript from Whisper and diarization (work/draft.md), for comparison with transcript.md
draft:
    ./scripts/draft.py data/diarization.json work/draft.md {{whisper}}

# Make the Cleaned audio with ClearerVoice, keep the Piping untouched, level it, and encode site/audio.m4a
clean-audio:
    mkdir -p work site
    ffmpeg -hide_banner -loglevel error -y -i {{recording}} -ac 1 -ar 48000 {{source_wav}}
    ./scripts/enhance-clearvoice.py {{source_wav}} work/clearvoice-48k.wav
    just compose-audio

# Combine the enhanced speech with the untouched Piping, then level and encode site/audio.m4a
compose-audio:
    ./scripts/compose-cleaned.py work/clearvoice-48k.wav {{source_wav}} work/cleaned-48k.wav --keep {{piping}}
    ffmpeg -hide_banner -loglevel error -y -i work/cleaned-48k.wav -af "{{leveling}}" -ac 1 -ar 48000 -c:a aac -b:a 80k -movflags +faststart site/audio.m4a

# Render one clip through every cleaning method for listening (start in seconds)
sample name start duration="60":
    #!/usr/bin/env bash
    set -euo pipefail
    dir=work/samples/{{name}}
    mkdir -p "$dir"
    ffmpeg -hide_banner -loglevel error -y -ss {{start}} -t {{duration}} -i {{recording}} -ac 1 -ar 48000 "$dir/source.wav"
    ./scripts/enhance-deepfilter.py "$dir/source.wav" "$dir/deepfilter.wav"
    ./scripts/enhance-demucs.py "$dir/source.wav" "$dir/demucs.wav"
    ./scripts/enhance-clearvoice.py "$dir/source.wav" "$dir/clearvoice.wav"
    ffmpeg -hide_banner -loglevel error -y -i "$dir/source.wav" -af "afftdn=nr=15:nf=-40:tn=1" "$dir/ffmpeg.wav"
    encode() { ffmpeg -hide_banner -loglevel error -y -i "$1" -af "$2" -ac 1 -ar 48000 -c:a aac -b:a 128k "$3"; }
    encode "$dir/source.wav" anull "$dir/1-original.m4a"
    encode "$dir/source.wav" "{{leveling}}" "$dir/2-leveled-only.m4a"
    encode "$dir/ffmpeg.wav" "{{leveling}}" "$dir/3-ffmpeg-denoise.m4a"
    encode "$dir/deepfilter.wav" "{{leveling}}" "$dir/4-deepfilternet.m4a"
    encode "$dir/demucs.wav" "{{leveling}}" "$dir/5-demucs.m4a"
    encode "$dir/clearvoice.wav" "{{leveling}}" "$dir/6-clearvoice.m4a"

# Build and serve the page locally with seekable audio (Ctrl-C to stop)
serve port="8765": build
    python3 scripts/serve.py {{port}} site
