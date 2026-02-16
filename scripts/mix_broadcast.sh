#!/bin/bash
#
# mix_broadcast.sh - Mix voice track with theme music (with loudness normalization)
#
# The signature "Shovel News" sound:
# - Theme plays at full volume for 3 seconds
# - Fades to 5% volume over 1 second
# - Stays at 5% under the voice
# - Fades to 0% during the signoff
#
# Audio processing:
# - Two-pass loudnorm: voice track normalized before mixing, final output normalized after
# - Target: -16 LUFS (podcast standard), -1.5 dBTP max
#
# Usage:
#   ./mix_broadcast.sh voice.mp3 theme.mp3 output.mp3
#   ./mix_broadcast.sh voice.mp3 theme.mp3 output.mp3 --voice-start 4 --normalize
#

set -e

# Defaults
VOICE_START=4        # Seconds before voice begins (after theme intro)
THEME_FADE_START=3   # When theme starts fading
THEME_FADE_DURATION=1  # How long the fade takes
THEME_VOLUME=0.05    # Volume under voice (5%)
SIGNOFF_DURATION=5   # How long before end to start final fade
NORMALIZE=true       # Apply loudness normalization
TARGET_LUFS=-16      # Target loudness
TARGET_TP=-1.5       # Target true peak
TARGET_LRA=11        # Target loudness range

usage() {
    echo "Usage: $0 <voice_track> <theme_music> <output_file> [options]"
    echo
    echo "Options:"
    echo "  --voice-start SECS    When voice begins (default: $VOICE_START)"
    echo "  --theme-volume VOL    Theme volume under voice, 0-1 (default: $THEME_VOLUME)"
    echo "  --signoff SECS        Fade-out duration at end (default: $SIGNOFF_DURATION)"
    echo "  --no-normalize        Skip loudness normalization"
    echo "  --target-lufs LUFS    Target loudness (default: $TARGET_LUFS)"
    echo
    echo "Example:"
    echo "  $0 voice.mp3 shovel-theme.mp3 broadcast.mp3"
    exit 1
}

# Parse arguments
if [ $# -lt 3 ]; then
    usage
fi

VOICE_TRACK="$1"
THEME_MUSIC="$2"
OUTPUT_FILE="$3"
shift 3

while [ $# -gt 0 ]; do
    case "$1" in
        --voice-start)
            VOICE_START="$2"
            shift 2
            ;;
        --theme-volume)
            THEME_VOLUME="$2"
            shift 2
            ;;
        --signoff)
            SIGNOFF_DURATION="$2"
            shift 2
            ;;
        --no-normalize)
            NORMALIZE=false
            shift
            ;;
        --target-lufs)
            TARGET_LUFS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate inputs
if [ ! -f "$VOICE_TRACK" ]; then
    echo "Error: Voice track not found: $VOICE_TRACK"
    exit 1
fi

if [ ! -f "$THEME_MUSIC" ]; then
    echo "Error: Theme music not found: $THEME_MUSIC"
    exit 1
fi

# Create a temporary directory
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Step 1: Normalize voice track (first loudnorm pass)
if [ "$NORMALIZE" = true ]; then
    echo "Normalizing voice track to ${TARGET_LUFS} LUFS..."
    ffmpeg -y -hide_banner -loglevel warning \
        -i "$VOICE_TRACK" \
        -af "loudnorm=I=${TARGET_LUFS}:TP=${TARGET_TP}:LRA=${TARGET_LRA}" \
        -ar 44100 -c:a libmp3lame -b:a 128k \
        "$TMPDIR/voice_normalized.mp3"
    VOICE_TRACK="$TMPDIR/voice_normalized.mp3"
fi

# Get voice track duration
VOICE_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VOICE_TRACK")

# Calculate total duration (voice start offset + voice duration + padding)
TOTAL_DURATION=$(echo "$VOICE_START + $VOICE_DURATION + 2" | bc)

# Calculate when to start the final fade-out
FADE_OUT_START=$(echo "$TOTAL_DURATION - $SIGNOFF_DURATION" | bc)

echo "Voice duration: ${VOICE_DURATION}s"
echo "Total duration: ${TOTAL_DURATION}s"
echo "Voice starts at: ${VOICE_START}s"
echo "Final fade starts at: ${FADE_OUT_START}s"

# Step 2: Create the theme music track with volume envelope
echo "Creating theme track with ducking envelope..."
ffmpeg -y -hide_banner -loglevel warning \
    -stream_loop -1 -i "$THEME_MUSIC" \
    -t "$TOTAL_DURATION" -ar 44100 \
    -af "volume='if(lt(t,$THEME_FADE_START),1,if(lt(t,$((THEME_FADE_START + THEME_FADE_DURATION))),1-((1-$THEME_VOLUME)*(t-$THEME_FADE_START)/$THEME_FADE_DURATION),if(lt(t,$FADE_OUT_START),$THEME_VOLUME,$THEME_VOLUME*(1-(t-$FADE_OUT_START)/$SIGNOFF_DURATION))))':eval=frame" \
    "$TMPDIR/theme_ducked.wav"

# Step 3: Mix voice (with delay) and theme
echo "Mixing voice and theme..."
DELAY_MS=$((VOICE_START * 1000))
ffmpeg -y -hide_banner -loglevel warning \
    -i "$TMPDIR/theme_ducked.wav" \
    -i "$VOICE_TRACK" \
    -filter_complex "[1:a]adelay=${DELAY_MS}|${DELAY_MS}[v];[0:a][v]amix=inputs=2:duration=longest" \
    -ar 44100 -c:a libmp3lame -b:a 128k \
    "$TMPDIR/mixed.mp3"

# Step 4: Final loudnorm pass
if [ "$NORMALIZE" = true ]; then
    echo "Applying final loudness normalization..."
    ffmpeg -y -hide_banner -loglevel warning \
        -i "$TMPDIR/mixed.mp3" \
        -af "loudnorm=I=${TARGET_LUFS}:TP=${TARGET_TP}:LRA=${TARGET_LRA}" \
        -ar 44100 -c:a libmp3lame -b:a 128k \
        "$OUTPUT_FILE"
else
    cp "$TMPDIR/mixed.mp3" "$OUTPUT_FILE"
fi

# Report results
OUTPUT_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
OUTPUT_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_FILE")
OUTPUT_LUFS=$(ffmpeg -i "$OUTPUT_FILE" -af "loudnorm=print_format=summary" -f null - 2>&1 | grep "Input Integrated" | awk '{print $3}')

echo
echo "Done!"
echo "  Output: $OUTPUT_FILE"
echo "  Size: $OUTPUT_SIZE"
echo "  Duration: ${OUTPUT_DURATION%.*}s"
echo "  Loudness: $OUTPUT_LUFS LUFS"
