#!/bin/bash
#
# setup.sh - Set up the AI podcast environment
#
# This script:
# 1. Creates necessary directories
# 2. Sets up Python virtual environment
# 3. Installs dependencies
# 4. Downloads Kokoro TTS models
#

set -e

echo "=== AI Podcast Setup ==="
echo

# Directories
VENV_DIR="$HOME/kokoro-venv"
MODEL_DIR="$HOME/kokoro-models"
WORKSPACE_DIR="$HOME/workspace"
WWW_DIR="$WORKSPACE_DIR/www/daily-news"

# Create directories
echo "Creating directories..."
mkdir -p "$MODEL_DIR"
mkdir -p "$WWW_DIR"
mkdir -p "$WORKSPACE_DIR"

# Check for system dependencies
echo "Checking system dependencies..."
for cmd in python3 ffmpeg ffprobe; do
    if ! command -v $cmd &> /dev/null; then
        echo "Error: $cmd is not installed."
        echo "Install with: sudo apt install python3 ffmpeg"
        exit 1
    fi
done

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install packages
echo "Installing Python packages..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install kokoro-onnx onnxruntime soundfile numpy

# Download models if not present
MODEL_FILE="$MODEL_DIR/kokoro-v1.0.fp16.onnx"
VOICES_FILE="$MODEL_DIR/voices-v1.0.bin"

if [ ! -f "$MODEL_FILE" ]; then
    echo "Downloading Kokoro model (fp16)..."
    echo "This may take a few minutes..."
    
    # Download from HuggingFace
    pip install huggingface_hub
    python3 -c "
from huggingface_hub import hf_hub_download
import shutil

# Download model
model_path = hf_hub_download(
    repo_id='hexgrad/Kokoro-82M-v1.0-ONNX',
    filename='fp16/kokoro-v1.0.fp16.onnx'
)
shutil.copy(model_path, '$MODEL_FILE')
print(f'Model saved to: $MODEL_FILE')
"
fi

if [ ! -f "$VOICES_FILE" ]; then
    echo "Downloading voices file..."
    python3 -c "
from huggingface_hub import hf_hub_download
import shutil

voices_path = hf_hub_download(
    repo_id='hexgrad/Kokoro-82M-v1.0-ONNX',
    filename='voices-v1.0.bin'
)
shutil.copy(voices_path, '$VOICES_FILE')
print(f'Voices saved to: $VOICES_FILE')
"
fi

# Create news-reported.md if not present
REPORTED_FILE="$WORKSPACE_DIR/news-reported.md"
if [ ! -f "$REPORTED_FILE" ]; then
    echo "Creating news-reported.md..."
    cat > "$REPORTED_FILE" << 'EOF'
# Recently Reported Topics (7-day window)

This file tracks news stories we've already covered to avoid repetition.
Check this before writing new scripts. Don't repeat these topics unless there's a major update.

---

EOF
fi

# Make scripts executable
chmod +x "$(dirname "$0")"/*.sh
chmod +x "$(dirname "$0")"/*.py 2>/dev/null || true

echo
echo "=== Setup Complete ==="
echo
echo "Directories:"
echo "  Virtual env: $VENV_DIR"
echo "  Models: $MODEL_DIR"
echo "  Output: $WWW_DIR"
echo
echo "To activate the environment:"
echo "  source $VENV_DIR/bin/activate"
echo
echo "To generate speech:"
echo "  ./scripts/generate_tts.py 'Hello world' -v am_michael -o test.wav"
echo
echo "Next: Create a theme song and place it at:"
echo "  $WORKSPACE_DIR/shovel-theme.mp3"
