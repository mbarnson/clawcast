#!/bin/bash
#
# demo_broadcast.sh - Generate a sample broadcast to test the setup
#
# Creates a short demo broadcast with all voice actors
#

set -e

SCRIPT_DIR="$(dirname "$0")"
VENV_DIR="$HOME/kokoro-venv"
WORKSPACE_DIR="$HOME/workspace"
OUTPUT_DIR="$WORKSPACE_DIR/www/daily-news"
THEME_FILE="$WORKSPACE_DIR/shovel-theme.mp3"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Create temp directory
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

echo "=== Generating Demo Broadcast ==="
echo

# Check for theme music
if [ ! -f "$THEME_FILE" ]; then
    echo "Warning: Theme music not found at $THEME_FILE"
    echo "Creating silent placeholder..."
    ffmpeg -y -hide_banner -loglevel warning \
        -f lavfi -i anullsrc=r=24000:cl=mono -t 30 \
        "$TMPDIR/theme.mp3"
    THEME_FILE="$TMPDIR/theme.mp3"
fi

# Demo script segments
echo "Generating voice segments..."

# Shovel (Host) - Intro
"$SCRIPT_DIR/generate_tts.py" \
    "Good morning! I'm Shovel, and welcome to your AI-generated daily briefing. Today we're demonstrating our multi-voice broadcast system. Let's check in with our correspondents." \
    -v am_michael -o "$TMPDIR/01_shovel_intro.wav"

# Nova (Tech)
"$SCRIPT_DIR/generate_tts.py" \
    "Thanks, Shovel! I'm Nova, covering tech news. This is a demonstration of the Kokoro text-to-speech system running entirely on a Raspberry Pi. No cloud APIs needed -- just local neural network inference. Pretty cool, right?" \
    -v af_nova -o "$TMPDIR/02_nova_tech.wav"

# Jessica (International)
"$SCRIPT_DIR/generate_tts.py" \
    "This is Jessica with international news. The beauty of this system is that it can run 24/7 on low-power hardware. A Raspberry Pi 5 uses about five watts -- less than a light bulb -- while generating human-quality speech." \
    -v af_jessica -o "$TMPDIR/03_jessica_intl.wav"

# George (Sports)
"$SCRIPT_DIR/generate_tts.py" \
    "George here. The generation speed is roughly one-point-two times real time on the Pi 5. That means a six-minute broadcast takes about five minutes to generate. Not instant, but perfectly practical for scheduled daily shows." \
    -v bm_george -o "$TMPDIR/04_george_sports.wav"

# Fable (Law/Business)
"$SCRIPT_DIR/generate_tts.py" \
    "Fable reporting. Each voice has distinct characteristics -- pitch, tone, pacing. The Kokoro model supports multiple voices from a single 82-megabyte model file. Quite efficient." \
    -v bm_fable -o "$TMPDIR/05_fable_law.wav"

# Puck (Quirky)
"$SCRIPT_DIR/generate_tts.py" \
    "And I'm Puck with something fun! Did you know this entire broadcast pipeline -- from text to mixed audio -- runs with just Python and ffmpeg? Open source tools doing professional work. Love to see it!" \
    -v am_puck -o "$TMPDIR/06_puck_quirky.wav"

# Shovel (Host) - Outro
"$SCRIPT_DIR/generate_tts.py" \
    "That's our demo broadcast. Thanks for listening, and have a great day! This has been Shovel News." \
    -v am_michael -o "$TMPDIR/07_shovel_outro.wav"

# Speed up all segments to 1.25x
echo "Adjusting playback speed..."
for f in "$TMPDIR"/*.wav; do
    ffmpeg -y -hide_banner -loglevel warning \
        -i "$f" \
        -filter:a "atempo=1.25" \
        "${f%.wav}_fast.wav"
done

# Create segments list
echo "Concatenating segments..."
cat > "$TMPDIR/segments.txt" << EOF
file '${TMPDIR}/01_shovel_intro_fast.wav'
file '${TMPDIR}/02_nova_tech_fast.wav'
file '${TMPDIR}/03_jessica_intl_fast.wav'
file '${TMPDIR}/04_george_sports_fast.wav'
file '${TMPDIR}/05_fable_law_fast.wav'
file '${TMPDIR}/06_puck_quirky_fast.wav'
file '${TMPDIR}/07_shovel_outro_fast.wav'
EOF

# Concatenate
ffmpeg -y -hide_banner -loglevel warning \
    -f concat -safe 0 -i "$TMPDIR/segments.txt" \
    -c copy \
    "$TMPDIR/voice_track.wav"

# Mix with theme
echo "Mixing with theme music..."
"$SCRIPT_DIR/mix_broadcast.sh" \
    "$TMPDIR/voice_track.wav" \
    "$THEME_FILE" \
    "$TMPDIR/broadcast.mp3"

# Copy to output
mkdir -p "$OUTPUT_DIR"
cp "$TMPDIR/broadcast.mp3" "$OUTPUT_DIR/demo.mp3"

echo
echo "=== Demo Complete ==="
echo "Output: $OUTPUT_DIR/demo.mp3"
echo
echo "Play with: mpv $OUTPUT_DIR/demo.mp3"
