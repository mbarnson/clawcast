#!/usr/bin/env python3
"""
Generate TTS audio using Piper (local, no cloud APIs).

Drop-in replacement for generate_tts.py / generate_tts_openai.py using Piper TTS.

Usage:
    ./generate_tts_piper.py "Text to speak" -v en_US-lessac-medium -o output.wav
    ./generate_tts_piper.py -f script.txt -v en_US-joe-medium -o output.wav
    echo "Hello" | ./generate_tts_piper.py -o output.wav
"""

import argparse
import os
import subprocess
import sys

DEFAULT_MODEL_DIR = os.path.expanduser("~/piper-models")

# Voice mapping for ClawCast characters
VOICE_PRESETS = {
    "shovel":  {"voice": "en_US-lessac-medium", "desc": "Warm morning host"},
    "nova":    {"voice": "en_US-amy-medium",    "desc": "Enthusiastic tech reporter"},
    "jessica": {"voice": "en_US-amy-medium",    "desc": "Calm international correspondent"},
    "george":  {"voice": "en_US-joe-medium",    "desc": "Serious politics reporter"},
    "fable":   {"voice": "en_GB-alan-medium",   "desc": "British law/business reporter"},
    "puck":    {"voice": "en_US-ryan-medium",   "desc": "Playful quirky reporter"},
}


def generate_tts(text, voice, output_path, model_dir=DEFAULT_MODEL_DIR):
    """Generate TTS audio using Piper."""
    model_path = os.path.join(model_dir, f"{voice}.onnx")
    if not os.path.exists(model_path):
        print(f"Error: Voice model not found: {model_path}", file=sys.stderr)
        print(f"Available models in {model_dir}:", file=sys.stderr)
        for f in sorted(os.listdir(model_dir)):
            if f.endswith(".onnx") and not f.endswith(".onnx.json"):
                print(f"  {f.replace('.onnx', '')}", file=sys.stderr)
        return False

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    cmd = [
        "piper",
        "--model", model_path,
        "--output_file", output_path,
    ]

    result = subprocess.run(
        cmd,
        input=text,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Piper error: {result.stderr}", file=sys.stderr)
        return False

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        size_kb = os.path.getsize(output_path) / 1024
        print(f"Generated: {output_path} ({size_kb:.0f} KB)", file=sys.stderr)
        return True

    print("Error: Output file not created or empty", file=sys.stderr)
    return False


def main():
    parser = argparse.ArgumentParser(description="Generate TTS using Piper (local)")
    parser.add_argument("text", nargs="?", help="Text to speak (or use -f/stdin)")
    parser.add_argument("-f", "--file", help="Read text from file")
    parser.add_argument("-v", "--voice", default="en_US-lessac-medium",
                        help="Piper voice name (default: en_US-lessac-medium)")
    parser.add_argument("-p", "--preset", choices=VOICE_PRESETS.keys(),
                        help="Use character preset")
    parser.add_argument("-o", "--output", default="output.wav",
                        help="Output WAV file (default: output.wav)")
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR,
                        help=f"Model directory (default: {DEFAULT_MODEL_DIR})")
    parser.add_argument("--prep", action="store_true",
                        help="Preprocess text for TTS")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available voices")

    args = parser.parse_args()

    if args.list_voices:
        print("Character presets:")
        for name, info in VOICE_PRESETS.items():
            print(f"  {name:10} -> {info['voice']:25} ({info['desc']})")
        print(f"\nAvailable models in {args.model_dir}:")
        if os.path.isdir(args.model_dir):
            for f in sorted(os.listdir(args.model_dir)):
                if f.endswith(".onnx") and not f.endswith(".onnx.json"):
                    print(f"  {f.replace('.onnx', '')}")
        return 0

    # Apply preset
    if args.preset:
        args.voice = VOICE_PRESETS[args.preset]["voice"]

    # Get text
    if args.text:
        text = args.text
    elif args.file:
        with open(args.file) as f:
            text = f.read()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.print_help()
        print("\nError: No text provided", file=sys.stderr)
        return 1

    if not text.strip():
        print("Error: Empty text", file=sys.stderr)
        return 1

    # Preprocess
    if args.prep:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from prep_for_tts import prep_for_tts
        text = prep_for_tts(text)

    success = generate_tts(text.strip(), args.voice, args.output, args.model_dir)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
