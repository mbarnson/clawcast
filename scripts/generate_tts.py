#!/usr/bin/env python3
"""
Generate TTS audio using Kokoro.

Usage:
    ./generate_tts.py "Text to speak" -v am_michael -o output.wav
    ./generate_tts.py -f script.txt -v af_nova -o output.wav
    echo "Hello world" | ./generate_tts.py -v am_puck -o output.wav
"""

import argparse
import sys
import os
from pathlib import Path

# Default paths - adjust for your setup
DEFAULT_MODEL = os.path.expanduser("~/kokoro-models/kokoro-v1.0.fp16.onnx")
DEFAULT_VOICES = os.path.expanduser("~/kokoro-models/voices-v1.0.bin")

# Available voices
VOICES = {
    # American English
    "am_michael": "Male, warm and friendly (default host voice)",
    "am_puck": "Male, clear and engaging",
    "af_nova": "Female, enthusiastic",
    "af_jessica": "Female, mature and reassuring",
    "af_bella": "Female, warm",
    "af_heart": "Female, expressive",
    # British English
    "bm_george": "Male, deep and authoritative",
    "bm_fable": "Male, husky with dry wit",
    "bf_emma": "Female, British",
}


def list_voices():
    """Print available voices."""
    print("Available voices:")
    print("-" * 50)
    for code, desc in VOICES.items():
        print(f"  {code:12} - {desc}")
    print()


def generate_speech(text: str, voice: str, output_path: str, 
                    model_path: str = DEFAULT_MODEL,
                    voices_path: str = DEFAULT_VOICES,
                    speed: float = 1.0) -> bool:
    """
    Generate speech from text using Kokoro TTS.
    
    Args:
        text: Text to convert to speech
        voice: Voice code (e.g., 'am_michael')
        output_path: Path for output WAV file
        model_path: Path to Kokoro ONNX model
        voices_path: Path to voices.bin file
        speed: Speech speed multiplier (1.0 = normal)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf
    except ImportError:
        print("Error: kokoro-onnx not installed. Run: pip install kokoro-onnx", file=sys.stderr)
        return False
    
    # Validate paths
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}", file=sys.stderr)
        return False
    if not os.path.exists(voices_path):
        print(f"Error: Voices file not found at {voices_path}", file=sys.stderr)
        return False
    
    # Initialize Kokoro
    print(f"Loading model...", file=sys.stderr)
    kokoro = Kokoro(model_path, voices_path)
    
    # Generate audio
    print(f"Generating speech ({len(text)} chars, voice={voice})...", file=sys.stderr)
    samples, sample_rate = kokoro.create(text, voice=voice, speed=speed)
    
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save to file
    sf.write(output_path, samples, sample_rate)
    print(f"Saved: {output_path} ({len(samples)/sample_rate:.1f}s)", file=sys.stderr)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate TTS audio using Kokoro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Hello, world!" -v am_michael -o hello.wav
  %(prog)s -f script.txt -v af_nova -o segment.wav
  %(prog)s --list-voices
  echo "News update" | %(prog)s -v bm_george -o news.wav
        """
    )
    
    parser.add_argument("text", nargs="?", help="Text to speak (or use -f for file)")
    parser.add_argument("-f", "--file", help="Read text from file")
    parser.add_argument("-v", "--voice", default="am_michael", 
                        help="Voice code (default: am_michael)")
    parser.add_argument("-o", "--output", default="output.wav",
                        help="Output WAV file (default: output.wav)")
    parser.add_argument("-s", "--speed", type=float, default=1.0,
                        help="Speech speed multiplier (default: 1.0)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Path to Kokoro model (default: {DEFAULT_MODEL})")
    parser.add_argument("--voices", default=DEFAULT_VOICES,
                        help=f"Path to voices file (default: {DEFAULT_VOICES})")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available voices and exit")
    
    args = parser.parse_args()
    
    if args.list_voices:
        list_voices()
        return 0
    
    # Get text from argument, file, or stdin
    text = None
    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, 'r') as f:
            text = f.read()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    
    if not text or not text.strip():
        parser.print_help()
        print("\nError: No text provided", file=sys.stderr)
        return 1
    
    # Validate voice
    if args.voice not in VOICES:
        print(f"Error: Unknown voice '{args.voice}'", file=sys.stderr)
        list_voices()
        return 1
    
    # Generate speech
    success = generate_speech(
        text=text.strip(),
        voice=args.voice,
        output_path=args.output,
        model_path=args.model,
        voices_path=args.voices,
        speed=args.speed
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
