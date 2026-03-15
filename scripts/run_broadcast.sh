#!/bin/bash
#
# run_broadcast.sh - End-to-end broadcast generation (fully local)
#
# Pipeline:
#   0. (Optional) Fetch news from RSS feeds
#   1. Generate script with local LLM (Qwen3.5-27B via vLLM)
#   2. Preprocess text for TTS
#   3. Generate TTS for each segment (Kokoro)
#   4. Speed up segments
#   5. Concatenate
#   6. Mix with theme music + loudness normalization
#   7. Generate HTML show notes
#
# No cloud APIs. Everything runs locally.
#
# Usage:
#   ./run_broadcast.sh --rss                     # Fetch real news + full pipeline
#   ./run_broadcast.sh --demo                    # Demo with sample topics
#   ./run_broadcast.sh --topics "AI news,space"  # Custom topics
#   ./run_broadcast.sh --topics-file topics.txt  # Topics from file
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RIG_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE_DIR="$HOME/workspace"
OUTPUT_DIR="$WORKSPACE_DIR/www/daily-news"
THEME_FILE="$RIG_DIR/assets/shovel-theme.mp3"
TODAY=$(date +%Y-%m-%d)
SPEED=1.25

# Ensure ffmpeg is in PATH
export PATH="$HOME/bin:$PATH"

usage() {
    echo "Usage: $0 [options]"
    echo
    echo "News source (pick one):"
    echo "  --rss                 Fetch real news from RSS feeds"
    echo "  --demo                Use sample topics"
    echo "  --topics TOPICS       Comma-separated news topics"
    echo "  --topics-file FILE    File with topics (text or JSON from fetch_news.py)"
    echo
    echo "Options:"
    echo "  --date DATE           Broadcast date (default: today)"
    echo "  --output FILE         Output file (default: $OUTPUT_DIR/<date>.mp3)"
    echo "  --no-music            Skip theme music mixing"
    echo "  --no-show-notes       Skip HTML show notes generation"
    echo "  --speed FACTOR        Playback speed (default: $SPEED)"
    echo "  --script-only         Generate script only, skip TTS"
    echo "  --feeds FILE          Custom feeds config JSON (with --rss)"
    echo "  --max-per-beat N      Max stories per beat (default: 3, with --rss)"
    echo "  --no-dedup            Skip dedup against reported stories"
    echo
    echo "Environment:"
    echo "  VLLM_API_BASE         vLLM endpoint (default: http://localhost:8000/v1)"
    echo "  VLLM_MODEL            Model name (default: Qwen/Qwen3.5-27B)"
    exit 1
}

# Parse arguments
SCRIPT_ARGS=""
NO_MUSIC=false
SCRIPT_ONLY=false
OUTPUT_FILE=""
USE_RSS=false
NO_SHOW_NOTES=false
FEEDS_FILE=""
MAX_PER_BEAT=3
NO_DEDUP=false

while [ $# -gt 0 ]; do
    case "$1" in
        --rss)
            USE_RSS=true
            shift
            ;;
        --demo)
            SCRIPT_ARGS="$SCRIPT_ARGS --demo"
            shift
            ;;
        --topics)
            SCRIPT_ARGS="$SCRIPT_ARGS --topics \"$2\""
            shift 2
            ;;
        --topics-file)
            SCRIPT_ARGS="$SCRIPT_ARGS --topics-file $2"
            shift 2
            ;;
        --date)
            TODAY="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --no-music)
            NO_MUSIC=true
            shift
            ;;
        --no-show-notes)
            NO_SHOW_NOTES=true
            shift
            ;;
        --speed)
            SPEED="$2"
            shift 2
            ;;
        --script-only)
            SCRIPT_ONLY=true
            shift
            ;;
        --feeds)
            FEEDS_FILE="$2"
            shift 2
            ;;
        --max-per-beat)
            MAX_PER_BEAT="$2"
            shift 2
            ;;
        --no-dedup)
            NO_DEDUP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

if [ -z "$SCRIPT_ARGS" ] && [ "$USE_RSS" = false ]; then
    usage
fi

# Set output file
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="$OUTPUT_DIR/${TODAY}.mp3"
fi

SCRIPT_OUTPUT_DIR="$WORKSPACE_DIR/scripts/$TODAY"
mkdir -p "$SCRIPT_OUTPUT_DIR" "$OUTPUT_DIR"

echo "=== Shovel News Broadcast Generator ==="
echo "Date: $TODAY"
echo "Output: $OUTPUT_FILE"
echo

# ── Step 0: Fetch News (if --rss) ────────────────────────────────────
if [ "$USE_RSS" = true ]; then
    echo "▸ Step 0: Fetching news from RSS feeds..."

    TOPICS_FILE="$SCRIPT_OUTPUT_DIR/topics.json"
    FETCH_ARGS="--max-per-beat $MAX_PER_BEAT --date $TODAY -o $TOPICS_FILE --save-reported"

    if [ -n "$FEEDS_FILE" ]; then
        FETCH_ARGS="$FETCH_ARGS --feeds $FEEDS_FILE"
    fi
    if [ "$NO_DEDUP" = true ]; then
        FETCH_ARGS="$FETCH_ARGS --no-dedup"
    fi

    python3 "$SCRIPT_DIR/fetch_news.py" $FETCH_ARGS

    if [ ! -f "$TOPICS_FILE" ]; then
        echo "Error: Failed to fetch news"
        exit 1
    fi

    TOPIC_COUNT=$(python3 -c "import json; print(len(json.load(open('$TOPICS_FILE'))))")
    echo "  Fetched $TOPIC_COUNT topics"
    echo

    # Set script args to use the topics file
    SCRIPT_ARGS="--topics-file $TOPICS_FILE"
fi

# ── Step 1: Generate Script ──────────────────────────────────────────
echo "▸ Step 1: Generating script with local LLM..."

eval python3 "$SCRIPT_DIR/generate_script.py" \
    $SCRIPT_ARGS \
    --date "$TODAY" \
    --output-dir "$SCRIPT_OUTPUT_DIR" \
    > /dev/null

MANIFEST="$SCRIPT_OUTPUT_DIR/manifest.json"

if [ ! -f "$MANIFEST" ]; then
    echo "Error: manifest.json not created"
    exit 1
fi

echo "  Script generated: $SCRIPT_OUTPUT_DIR/"

if [ "$SCRIPT_ONLY" = true ]; then
    echo
    echo "Script-only mode. Output: $SCRIPT_OUTPUT_DIR/"
    cat "$MANIFEST"
    exit 0
fi

# ── Step 2: Generate TTS ─────────────────────────────────────────────
echo
echo "▸ Step 2: Generating TTS with Kokoro..."

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Read manifest and generate TTS for each segment
SEGMENT_COUNT=$(python3 -c "import json; m=json.load(open('$MANIFEST')); print(len(m))")

for i in $(seq 0 $((SEGMENT_COUNT - 1))); do
    SEG_INFO=$(python3 -c "
import json
m = json.load(open('$MANIFEST'))
s = m[$i]
print(s['file'])
print(s['voice'])
print(s['character'])
")
    FILE=$(echo "$SEG_INFO" | sed -n 1p)
    VOICE=$(echo "$SEG_INFO" | sed -n 2p)
    CHARACTER=$(echo "$SEG_INFO" | sed -n 3p)

    SEGMENT_NUM=$(printf "%02d" $((i + 1)))
    INPUT_FILE="$SCRIPT_OUTPUT_DIR/$FILE"
    OUTPUT_WAV="$TMPDIR/${SEGMENT_NUM}_${CHARACTER}.wav"

    if [ ! -f "$INPUT_FILE" ]; then
        echo "  Warning: Missing segment file: $INPUT_FILE"
        continue
    fi

    # Preprocess text for TTS
    PREPPED=$(python3 "$SCRIPT_DIR/prep_for_tts.py" < "$INPUT_FILE")

    echo "  [$SEGMENT_NUM] $CHARACTER ($VOICE)..."
    echo "$PREPPED" | python3 "$SCRIPT_DIR/generate_tts.py" \
        -v "$VOICE" \
        -o "$OUTPUT_WAV"

    if [ ! -f "$OUTPUT_WAV" ]; then
        echo "  Error: TTS failed for segment $SEGMENT_NUM"
        exit 1
    fi
done

# ── Step 3: Speed Up ─────────────────────────────────────────────────
echo
echo "▸ Step 3: Adjusting playback speed (${SPEED}x)..."

for f in "$TMPDIR"/*.wav; do
    BASENAME=$(basename "$f" .wav)
    ffmpeg -y -hide_banner -loglevel warning \
        -i "$f" \
        -filter:a "atempo=$SPEED" \
        "$TMPDIR/${BASENAME}_fast.wav"
done

# ── Step 4: Concatenate ──────────────────────────────────────────────
echo
echo "▸ Step 4: Concatenating segments..."

# Build segments list in order
SEGMENTS_FILE="$TMPDIR/segments.txt"
for f in $(ls "$TMPDIR"/*_fast.wav 2>/dev/null | sort); do
    echo "file '$f'" >> "$SEGMENTS_FILE"
done

if [ ! -f "$SEGMENTS_FILE" ]; then
    echo "Error: No segments to concatenate"
    exit 1
fi

VOICE_TRACK="$TMPDIR/voice_track.wav"
ffmpeg -y -hide_banner -loglevel warning \
    -f concat -safe 0 -i "$SEGMENTS_FILE" \
    -c copy \
    "$VOICE_TRACK"

VOICE_DURATION=$(ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$VOICE_TRACK")
echo "  Voice track: ${VOICE_DURATION%.*}s"

# ── Step 5: Mix with Theme ───────────────────────────────────────────
mkdir -p "$(dirname "$OUTPUT_FILE")"

if [ "$NO_MUSIC" = true ] || [ ! -f "$THEME_FILE" ]; then
    echo
    if [ ! -f "$THEME_FILE" ]; then
        echo "▸ Step 5: No theme music found, outputting voice-only..."
    else
        echo "▸ Step 5: Skipping music (--no-music)..."
    fi

    # Just convert to MP3
    ffmpeg -y -hide_banner -loglevel warning \
        -i "$VOICE_TRACK" \
        -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
        -ar 44100 -c:a libmp3lame -b:a 256k \
        "$OUTPUT_FILE"
else
    echo
    echo "▸ Step 5: Mixing with theme music..."
    "$SCRIPT_DIR/mix_broadcast.sh" \
        "$VOICE_TRACK" \
        "$THEME_FILE" \
        "$OUTPUT_FILE"
fi

# ── Step 6: Generate Show Notes ──────────────────────────────────────
HTML_FILE="${OUTPUT_FILE%.mp3}.html"

if [ "$NO_SHOW_NOTES" = false ]; then
    echo
    echo "▸ Step 6: Generating show notes..."

    AUDIO_BASENAME=$(basename "$OUTPUT_FILE")
    python3 "$SCRIPT_DIR/generate_show_notes.py" \
        --manifest "$MANIFEST" \
        --audio "$AUDIO_BASENAME" \
        --date "$TODAY" \
        -o "$HTML_FILE"

    echo "  Show notes: $HTML_FILE"
fi

# ── Report ────────────────────────────────────────────────────────────
echo
echo "=== Broadcast Complete ==="
OUTPUT_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
OUTPUT_DURATION=$(ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_FILE")
echo "  Audio: $OUTPUT_FILE ($OUTPUT_SIZE, ${OUTPUT_DURATION%.*}s)"
if [ "$NO_SHOW_NOTES" = false ] && [ -f "$HTML_FILE" ]; then
    echo "  Notes: $HTML_FILE"
fi
echo "  Script: $SCRIPT_OUTPUT_DIR/"
echo
echo "Play with: mpv $OUTPUT_FILE"
