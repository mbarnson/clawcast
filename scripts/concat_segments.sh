#!/bin/bash
#
# concat_segments.sh - Concatenate audio segments into a single track
#
# Usage:
#   ./concat_segments.sh output.wav segment1.wav segment2.wav segment3.wav
#   ./concat_segments.sh output.wav -f segments.txt
#
# segments.txt format:
#   file 'path/to/segment1.wav'
#   file 'path/to/segment2.wav'
#

set -e

usage() {
    echo "Usage: $0 <output.wav> <segment1.wav> [segment2.wav ...]"
    echo "       $0 <output.wav> -f <segments_list.txt>"
    echo
    echo "Concatenates multiple audio segments into a single file."
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

OUTPUT="$1"
shift

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Build the segments file
SEGMENTS_FILE="$TMPDIR/segments.txt"

if [ "$1" = "-f" ]; then
    # Use provided segments file
    if [ ! -f "$2" ]; then
        echo "Error: Segments file not found: $2"
        exit 1
    fi
    cp "$2" "$SEGMENTS_FILE"
else
    # Build segments file from arguments
    for segment in "$@"; do
        if [ ! -f "$segment" ]; then
            echo "Error: Segment not found: $segment"
            exit 1
        fi
        # Use absolute path
        echo "file '$(realpath "$segment")'" >> "$SEGMENTS_FILE"
    done
fi

# Count segments
NUM_SEGMENTS=$(wc -l < "$SEGMENTS_FILE")
echo "Concatenating $NUM_SEGMENTS segments..."

# Concatenate
ffmpeg -y -hide_banner -loglevel warning \
    -f concat -safe 0 -i "$SEGMENTS_FILE" \
    -c copy \
    "$OUTPUT"

# Report
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT")
echo "Created: $OUTPUT (${DURATION%.*}s)"
