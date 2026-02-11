#!/bin/bash
#
# mix_broadcast.sh - Mix voice track with theme music
#
# The signature "Shovel News" sound:
# - Theme plays at full volume for 3 seconds
# - Fades to 3% volume over 1 second
# - Stays at 3% under the voice
# - Fades to 0% during the signoff
#
# Usage:
#   ./mix_broadcast.sh voice.wav theme.mp3 output.mp3
#   ./mix_broadcast.sh voice.wav theme.mp3 output.mp3 --voice-start 4
#

set -e

# Defaults
VOICE_START=4        # Seconds before voice begins (after theme intro)
THEME_FADE_START=3   # When theme starts fading
THEME_FADE_DURATION=1  # How long the fade takes
THEME_VOLUME=0.03    # Volume under voice (3%)
SIGNOFF_DURATION=5   # How long before end to start final fade

usage() {
    echo "Usage: $0 <voice_track> <theme_music> <output_file> [options]"
    echo
    echo "Options:"
    echo "  --voice-start SECS    When voice begins (default: $VOICE_START)"
    echo "  --theme-volume VOL    Theme volume under voice, 0-1 (default: $THEME_VOLUME)"
    echo "  --signoff SECS        Fade-out duration at end (default: $SIGNOFF_DURATION)"
    echo
    echo "Example:"
    echo "  $0 voice.wav shovel-theme.mp3 broadcast.mp3"
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

# Get voice track duration
VOICE_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VOICE_TRACK")
VOICE_DURATION=${VOICE_DURATION%.*}  # Round to integer

# Calculate total duration (voice start offset + voice duration + a little padding)
TOTAL_DURATION=$((VOICE_START + VOICE_DURATION + 2))

# Calculate when to start the final fade-out
FADE_OUT_START=$((TOTAL_DURATION - SIGNOFF_DURATION))

echo "Voice duration: ${VOICE_DURATION}s"
echo "Total duration: ${TOTAL_DURATION}s"
echo "Voice starts at: ${VOICE_START}s"
echo "Final fade starts at: ${FADE_OUT_START}s"

# Create a temporary directory
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Step 1: Prepare voice track with leading silence
echo "Adding ${VOICE_START}s silence before voice..."
ffmpeg -y -hide_banner -loglevel warning \
    -f lavfi -i anullsrc=r=24000:cl=mono -t "$VOICE_START" \
    -i "$VOICE_TRACK" \
    -filter_complex "[0][1]concat=n=2:v=0:a=1" \
    "$TMPDIR/voice_padded.wav"

# Step 2: Create the theme music track with volume envelope
# The volume envelope:
# - 0 to THEME_FADE_START: full volume (1.0)
# - THEME_FADE_START to THEME_FADE_START+THEME_FADE_DURATION: fade to THEME_VOLUME
# - THEME_FADE_START+THEME_FADE_DURATION to FADE_OUT_START: stay at THEME_VOLUME
# - FADE_OUT_START to end: fade to 0

FADE_IN_END=$((THEME_FADE_START + THEME_FADE_DURATION))

echo "Creating theme track with volume envelope..."
ffmpeg -y -hide_banner -loglevel warning \
    -i "$THEME_MUSIC" \
    -t "$TOTAL_DURATION" \
    -af "volume=eval=frame:
         volume='if(lt(t,$THEME_FADE_START), 1,
                 if(lt(t,$FADE_IN_END), 1 - (1-$THEME_VOLUME)*(t-$THEME_FADE_START)/$THEME_FADE_DURATION,
                 if(lt(t,$FADE_OUT_START), $THEME_VOLUME,
                 $THEME_VOLUME * (1 - (t-$FADE_OUT_START)/$SIGNOFF_DURATION))))'" \
    "$TMPDIR/theme_ducked.wav"

# Step 3: Mix voice and theme
echo "Mixing voice and theme..."
ffmpeg -y -hide_banner -loglevel warning \
    -i "$TMPDIR/voice_padded.wav" \
    -i "$TMPDIR/theme_ducked.wav" \
    -filter_complex "[0][1]amix=inputs=2:duration=longest:normalize=0" \
    -ar 44100 \
    -b:a 192k \
    "$OUTPUT_FILE"

# Report results
OUTPUT_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
OUTPUT_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_FILE")

echo
echo "Done!"
echo "  Output: $OUTPUT_FILE"
echo "  Size: $OUTPUT_SIZE"
echo "  Duration: ${OUTPUT_DURATION%.*}s"
