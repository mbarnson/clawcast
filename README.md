# AI Morning Broadcast

A Raspberry Pi-based system for generating daily news podcasts using local TTS (Kokoro) and ffmpeg. This repo documents the process used by "Shovel News" - an AI-generated morning broadcast.

## Overview

The broadcast is a ~5-7 minute audio file featuring:
- A host (Shovel) introducing the day's news
- Multiple correspondents covering different beats (tech, international, sports, law/business, quirky stories)
- Background music (theme song fades under voice)
- Professional-sounding transitions

All TTS runs locally on a Raspberry Pi 5 (8GB) using Kokoro - no cloud APIs required.

## Hardware Requirements

- Raspberry Pi 5 (8GB recommended, 4GB minimum)
- microSD card (32GB+) or NVMe storage
- Internet connection (for fetching news)

## Software Dependencies

```bash
# System packages
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg git

# Create virtual environment
python3 -m venv ~/kokoro-venv
source ~/kokoro-venv/bin/activate

# Install Kokoro TTS
pip install kokoro-onnx onnxruntime soundfile numpy
```

## Directory Structure

```
~/
├── kokoro-venv/              # Python virtual environment
├── kokoro-models/            # TTS model files
│   ├── kokoro-v1.0.fp16.onnx
│   └── voices-v1.0.bin
├── workspace/
│   ├── shovel-theme.mp3      # Theme song (you provide)
│   ├── news-reported.md      # Topic dedup tracking
│   └── www/
│       └── daily-news/
│           └── latest.mp3    # Output broadcast
└── src/
    └── ai_podcast/           # This repo
        ├── scripts/
        ├── examples/
        └── templates/
```

## Voice Cast

| Voice Code | Character | Role |
|------------|-----------|------|
| am_michael | Shovel | Host (warm, friendly) |
| af_nova | Nova | Tech correspondent |
| af_jessica | Jessica | International news |
| bm_george | George | War/Sports |
| bm_fable | Fable | Law/Business |
| am_puck | Puck | Quirky closer |

## The Production Pipeline

### 1. Research & Topic Selection

Check `news-reported.md` for recently covered topics (7-day dedup window), then gather news from sources:
- Hacker News (tech)
- NPR (general, international)
- Slashdot (tech, law)
- Local news sources
- Ars Technica (tech deep dives)

### 2. Script Writing

Each segment follows this structure:
- **Intro** (Shovel): ~50-75 words welcoming listeners
- **Segments** (Correspondents): ~250-350 words each
- **Handoffs**: Brief transitions between speakers
- **Outro** (Shovel): ~50 words closing

See `templates/script_template.md` for the full format.

### 3. TTS Generation

Generate audio for each segment using Kokoro:

```bash
./scripts/generate_tts.py "Hello, this is Shovel!" -v am_michael -o shovel_intro.wav
```

Kokoro runs at roughly 1.2x realtime on Pi 5 (a 30-second clip takes ~25 seconds to generate).

### 4. Speed Adjustment

The raw TTS output is clear but slightly slow. Speed up to 1.25x for a natural pace:

```bash
ffmpeg -i segment.wav -filter:a "atempo=1.25" -y segment_fast.wav
```

### 5. Concatenate Voice Segments

Join all voice segments in order:

```bash
ffmpeg -f concat -safe 0 -i segments.txt -c copy voice_track.wav
```

Where `segments.txt` contains:
```
file 'shovel_intro.wav'
file 'nova_tech.wav'
file 'jessica_intl.wav'
...
```

### 6. Mix with Theme Music

The signature sound: theme plays full for 3 seconds, fades to 3% volume under the voice, then fades out during the signoff.

```bash
./scripts/mix_broadcast.sh voice_track.wav theme.mp3 output.mp3
```

See `scripts/mix_broadcast.sh` for the full ffmpeg filter chain.

### 7. Publish

Copy the final file to your web server directory:

```bash
cp output.mp3 ~/workspace/www/daily-news/latest.mp3
```

## Quick Start

```bash
# Clone this repo
git clone https://github.com/youruser/ai_podcast.git
cd ai_podcast

# Set up environment
./scripts/setup.sh

# Generate a test broadcast
./scripts/demo_broadcast.sh

# Listen to the result
mpv ~/workspace/www/daily-news/latest.mp3
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/setup.sh` | Install dependencies, download models |
| `scripts/generate_tts.py` | Generate TTS audio from text |
| `scripts/mix_broadcast.sh` | Mix voice + theme music |
| `scripts/demo_broadcast.sh` | Generate a sample broadcast |
| `scripts/prune_reported.sh` | Clean old entries from news-reported.md |

## Tips & Tricks

### Voice Quality
- Kokoro's `fp16` model sounds better than `int8` on ARM (Pi's NEON makes fp16 fast)
- Add brief pauses with `...` or `--` in your scripts
- Avoid ALL CAPS (sounds shouty)

### Audio Mixing
- Voice should start at 4 seconds (after theme establishes)
- Theme at 3% volume is audible but not distracting
- Fade theme to 0 during signoff for clean ending

### Performance
- Expect ~5 minutes of generation time for a 6-minute broadcast
- Run overnight via cron for morning delivery
- fp16 model: ~1.2x realtime on Pi 5

### Topic Deduplication
Keep `news-reported.md` updated to avoid repeating stories. Format:
```markdown
## 2026-02-10
- Story one (category)
- Story two (category)
```
Prune entries older than 7 days with `scripts/prune_reported.sh`.

## Example Cron Setup

```bash
# Generate broadcast at 6:00 AM daily
0 6 * * * cd ~/src/ai_podcast && ./scripts/generate_broadcast.sh >> ~/logs/broadcast.log 2>&1
```

## Sample Output

Listen to an actual broadcast generated with this system:

**[examples/output/sample_broadcast.mp3](examples/output/sample_broadcast.mp3)** (~6 min, 6.3MB)

This was generated entirely on a Raspberry Pi 5 using Kokoro TTS -- no cloud APIs.

## License

MIT - Do whatever you want with this.

## Acknowledgments

- [Kokoro TTS](https://github.com/thewh1teagle/kokoro-onnx) - Local neural TTS
- [ffmpeg](https://ffmpeg.org/) - Audio processing swiss army knife
- The fine folks who make Raspberry Pi actually usable for ML inference
