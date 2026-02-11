#!/bin/bash
#
# simple_broadcast.sh - Minimal example of generating a two-segment broadcast
#
# This is a stripped-down example showing the core workflow:
# 1. Generate TTS for each segment
# 2. Speed up the audio
# 3. Concatenate segments
# 4. Mix with music
#

set -e

SCRIPT_DIR="$(dirname "$0")/../scripts"
source "$HOME/kokoro-venv/bin/activate"

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

echo "=== Simple Broadcast Example ==="

# Step 1: Generate TTS segments
echo "Generating intro..."
"$SCRIPT_DIR/generate_tts.py" \
    "Hello! This is a simple example of the AI podcast system. Let me tell you about it." \
    -v am_michael -o "$TMPDIR/intro.wav"

echo "Generating main content..."
"$SCRIPT_DIR/generate_tts.py" \
    "The system uses Kokoro for text-to-speech, running entirely on a Raspberry Pi. No internet required for generation -- just local neural network inference. Pretty neat, right?" \
    -v af_nova -o "$TMPDIR/content.wav"

echo "Generating outro..."
"$SCRIPT_DIR/generate_tts.py" \
    "Thanks for listening to this demo. Have a great day!" \
    -v am_michael -o "$TMPDIR/outro.wav"

# Step 2: Speed up to 1.25x
echo "Adjusting speed..."
for f in "$TMPDIR"/*.wav; do
    ffmpeg -y -hide_banner -loglevel warning \
        -i "$f" -filter:a "atempo=1.25" "${f%.wav}_fast.wav"
done

# Step 3: Concatenate
echo "Concatenating..."
"$SCRIPT_DIR/concat_segments.sh" "$TMPDIR/voice.wav" \
    "$TMPDIR/intro_fast.wav" \
    "$TMPDIR/content_fast.wav" \
    "$TMPDIR/outro_fast.wav"

# Step 4: If you have a theme song, mix it
# "$SCRIPT_DIR/mix_broadcast.sh" "$TMPDIR/voice.wav" ~/workspace/theme.mp3 output.mp3

# For now, just output the voice track
cp "$TMPDIR/voice.wav" ./simple_output.wav

echo
echo "Done! Output: simple_output.wav"
echo "Play with: mpv simple_output.wav"
