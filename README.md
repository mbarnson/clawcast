# ClawCast - AI Morning Broadcast

A system for generating daily news podcasts using cloud TTS (OpenAI) or local TTS (Kokoro) with ffmpeg audio processing. This repo documents the process used by "Shovel News" - an AI-generated morning broadcast.

## Overview

The broadcast is a ~5-7 minute audio file featuring:
- A host (Shovel) introducing the day's news
- Multiple correspondents covering different beats (tech, international, politics, law/business, quirky stories)
- Background music (theme song ducks under voice)
- Professional loudness normalization (-16 LUFS)

## TTS Options

### OpenAI (Primary - Recommended)
- Model: `gpt-4o-mini-tts`
- Cost: ~$0.015/1K characters (~$2-3/month for daily broadcasts)
- Quality: Excellent, with promptable voice instructions
- Voices: coral, shimmer, sage, onyx, fable, nova, and more

### Kokoro (Fallback - Local)
- Runs entirely on Raspberry Pi 5
- No API costs
- Slower generation, slightly lower quality
- Voices: am_michael, af_nova, af_jessica, bm_george, bm_fable, am_puck

### ElevenLabs (Premium - Optional)
- Highest quality voices
- Higher cost (~$99/month for daily use)
- See commented examples in scripts

## Hardware Requirements

For OpenAI TTS:
- Any machine with internet access
- Raspberry Pi 4/5 works fine

For local Kokoro TTS:
- Raspberry Pi 5 (8GB recommended, 4GB minimum)
- microSD card (32GB+) or NVMe storage

## Software Dependencies

```bash
# System packages
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg jq bc curl

# For Kokoro fallback (optional)
python3 -m venv ~/kokoro-venv
source ~/kokoro-venv/bin/activate
pip install kokoro-onnx soundfile
```

## Voice Mapping

| Character | Role | OpenAI Voice | Instructions |
|-----------|------|--------------|--------------|
| **Shovel** | Host | `coral` | Warm morning host, welcoming but not over-the-top |
| **Nova** | Tech | `shimmer` | Enthusiastic tech reporter, curious and engaged |
| **Jessica** | International | `sage` | Calm, measured international correspondent |
| **George** | Politics/War | `onyx` | Deep, serious, no-nonsense reporter |
| **Fable** | Law/Business | `fable` | British accent, dry wit, thoughtful |
| **Puck** | Quirky | `nova` | Light, playful, conversational |

## Audio Processing

### Two-Pass Loudness Normalization

The broadcast uses EBU R128 loudness normalization for consistent levels:

1. **First pass**: Normalize voice track to -16 LUFS before mixing
2. **Mix**: Combine with theme music (ducked to 5% under voice)
3. **Second pass**: Final loudnorm on complete mix

This ensures:
- Consistent loudness across all correspondent voices
- No jarring volume changes between segments
- Podcast-standard -16 LUFS output

### Theme Music Ducking

```
|--3s full--|--1s fade--|--voice @ 5% music--|--fade out during signoff--|
            ^theme ducks                      ^theme fades to 0
```

## Quick Start

### 1. Set up API key

```bash
# Create secrets directory
mkdir -p ~/.secrets
echo "sk-your-openai-key-here" > ~/.secrets/OPENAI_API_KEY.txt
chmod 600 ~/.secrets/OPENAI_API_KEY.txt
```

### 2. Generate a segment

```bash
export OPENAI_API_KEY=$(cat ~/.secrets/OPENAI_API_KEY.txt)

# Using the script
./scripts/generate_tts_openai.py "Hello, welcome to Shovel News!" \
  --voice coral \
  --instructions "Warm morning host" \
  --output segment.mp3

# Or with a preset
./scripts/generate_tts_openai.py "Tech news is exciting today!" \
  --preset nova \
  --output tech.mp3
```

### 3. Mix with music

```bash
./scripts/mix_broadcast.sh voice.mp3 theme.mp3 output.mp3
```

## Scripts

| Script | Description |
|--------|-------------|
| `generate_tts_openai.py` | Generate TTS with OpenAI (primary) |
| `generate_tts.py` | Generate TTS with Kokoro (fallback) |
| `prep_for_tts.py` | Preprocess text (numbers, abbreviations) |
| `concat_segments.sh` | Concatenate multiple segments |
| `mix_broadcast.sh` | Mix voice with theme, apply loudnorm |
| `demo_broadcast.sh` | Full demo generation |

## Text Preprocessing

Numbers and abbreviations should be spelled out for better TTS:

```bash
echo "The project cost \$11,000" | ./scripts/prep_for_tts.py
# Output: The project cost eleven thousand dollars

echo "AI grew 3.5% in Q4" | ./scripts/prep_for_tts.py
# Output: A.I. grew three point five percent in Q4
```

## Writing Style (Hemingway Rules)

For best results, write scripts following these guidelines:
- Short sentences. Strong verbs. Active voice.
- NO adverbs ("ran quickly" → "sprinted")
- NO hedging ("perhaps", "sort of", "I think")
- NO AI-isms ("quietly reshaping", "it's not X, it's Y")
- Simple words ("use" not "utilize")

## Example Output

See `examples/output/` for sample broadcasts.

## License

MIT License - see LICENSE file.
