#!/bin/bash
#
# prune_reported.sh - Remove old entries from news-reported.md
#
# Keeps only the last 7 days of entries to prevent the file from growing forever.
#
# Usage:
#   ./prune_reported.sh [days_to_keep]
#

DAYS_TO_KEEP=${1:-7}
REPORTED_FILE="${2:-$HOME/workspace/news-reported.md}"

if [ ! -f "$REPORTED_FILE" ]; then
    echo "Error: news-reported.md not found at $REPORTED_FILE"
    exit 1
fi

# Calculate cutoff date
CUTOFF=$(date -d "$DAYS_TO_KEEP days ago" +%Y-%m-%d 2>/dev/null || \
         date -v-${DAYS_TO_KEEP}d +%Y-%m-%d)

echo "Pruning entries older than $CUTOFF from $REPORTED_FILE"

# Create temp file
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

# Process the file
# Keep header (everything before first ## YYYY-MM-DD)
# Keep date sections where date >= cutoff
awk -v cutoff="$CUTOFF" '
BEGIN { in_header = 1; keep_section = 1 }

/^## [0-9]{4}-[0-9]{2}-[0-9]{2}/ {
    in_header = 0
    date = substr($2, 1, 10)  # Extract YYYY-MM-DD
    keep_section = (date >= cutoff)
}

in_header || keep_section { print }
' "$REPORTED_FILE" > "$TMPFILE"

# Count lines removed
BEFORE=$(wc -l < "$REPORTED_FILE")
AFTER=$(wc -l < "$TMPFILE")
REMOVED=$((BEFORE - AFTER))

# Replace original
mv "$TMPFILE" "$REPORTED_FILE"

echo "Removed $REMOVED lines (kept entries from $CUTOFF onwards)"
