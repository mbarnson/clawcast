#!/usr/bin/env python3
"""
Generate TTS audio using OpenAI's gpt-4o-mini-tts model.

Usage:
    generate_tts_openai.py "Text to speak" --voice coral --output segment.mp3
    generate_tts_openai.py --voice shimmer --instructions "Enthusiastic tone" < script.txt

Environment:
    OPENAI_API_KEY or pass --api-key
"""

import argparse
import os
import sys
import json
import subprocess

# Voice presets for podcast roles
VOICE_PRESETS = {
    "shovel": {"voice": "coral", "instructions": "Warm morning host, welcoming but not over-the-top"},
    "nova": {"voice": "shimmer", "instructions": "Enthusiastic tech reporter, curious and engaged"},
    "jessica": {"voice": "sage", "instructions": "Calm, measured international correspondent"},
    "george": {"voice": "onyx", "instructions": "Deep, serious, no-nonsense reporter"},
    "fable": {"voice": "fable", "instructions": "British accent, dry wit, thoughtful"},
    "puck": {"voice": "nova", "instructions": "Light, playful, conversational"},
}

def generate_tts(text, voice, instructions, output_path, api_key):
    """Generate TTS audio using OpenAI API."""
    
    # Build JSON payload using jq for proper escaping
    payload = json.dumps({
        "model": "gpt-4o-mini-tts",
        "voice": voice,
        "input": text,
        "instructions": instructions
    })
    
    cmd = [
        "curl", "-s",
        "https://api.openai.com/v1/audio/speech",
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json",
        "-d", payload,
        "--output", output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return False
    
    # Check if output file exists and has content
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return True
    else:
        print(f"Error: Output file not created or empty", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate TTS using OpenAI")
    parser.add_argument("text", nargs="?", help="Text to convert (or use stdin)")
    parser.add_argument("--voice", "-v", default="coral", help="Voice name (coral, shimmer, sage, onyx, fable, nova, etc.)")
    parser.add_argument("--preset", "-p", choices=VOICE_PRESETS.keys(), help="Use preset for podcast role")
    parser.add_argument("--instructions", "-i", default="", help="Voice instructions/style")
    parser.add_argument("--output", "-o", required=True, help="Output file path")
    parser.add_argument("--api-key", help="OpenAI API key (or use OPENAI_API_KEY env)")
    parser.add_argument("--prep", action="store_true", help="Preprocess text for TTS (numbers, abbreviations)")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Try reading from secrets file
        secrets_path = os.path.expanduser("~/.secrets/OPENAI_API_KEY.txt")
        if os.path.exists(secrets_path):
            with open(secrets_path) as f:
                api_key = f.read().strip()
    
    if not api_key:
        print("Error: No API key. Set OPENAI_API_KEY or use --api-key", file=sys.stderr)
        sys.exit(1)
    
    # Get text
    if args.text:
        text = args.text
    else:
        text = sys.stdin.read()
    
    if not text.strip():
        print("Error: No text provided", file=sys.stderr)
        sys.exit(1)
    
    # Apply preset if specified
    if args.preset:
        preset = VOICE_PRESETS[args.preset]
        voice = preset["voice"]
        instructions = args.instructions or preset["instructions"]
    else:
        voice = args.voice
        instructions = args.instructions
    
    # Preprocess if requested
    if args.prep:
        from prep_for_tts import prep_for_tts
        text = prep_for_tts(text)
    
    # Generate
    success = generate_tts(text, voice, instructions, args.output, api_key)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
