#!/usr/bin/env python3
"""
Generate broadcast scripts using a local LLM (Qwen3.5-27B via vLLM).

Uses the OpenAI-compatible API at localhost:8000/v1. No cloud APIs needed.

Usage:
    ./generate_script.py --topics "AI regulation,space launch" --date 2026-03-14
    ./generate_script.py --topics-file topics.txt --output-dir scripts/2026-03-14/
    ./generate_script.py --demo  # Generate a demo script with sample topics
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date


# Default vLLM endpoint
DEFAULT_API_BASE = "http://localhost:8000/v1"
DEFAULT_MODEL = "Qwen/Qwen3.5-27B"

# Map beats to correspondents (used with structured topics from fetch_news.py)
BEAT_TO_CORRESPONDENT = {
    "tech": "Nova",
    "international": "Jessica",
    "politics": "George",
    "business": "Fable",
    "quirky": "Puck",
}

# Voice assignments matching ClawCast character roster (Kokoro voice codes)
CHARACTERS = {
    "shovel": {"role": "Host", "voice": "am_michael", "style": "Warm morning host, welcoming but not over-the-top"},
    "nova": {"role": "Tech reporter", "voice": "af_nova", "style": "Enthusiastic tech reporter, curious and engaged"},
    "jessica": {"role": "International correspondent", "voice": "af_jessica", "style": "Calm, measured international correspondent"},
    "george": {"role": "Politics/War correspondent", "voice": "bm_george", "style": "Deep, serious, no-nonsense reporter"},
    "fable": {"role": "Law/Business reporter", "voice": "bm_fable", "style": "British accent, dry wit, thoughtful"},
    "puck": {"role": "Quirky/fun reporter", "voice": "am_puck", "style": "Light, playful, conversational"},
}

SYSTEM_PROMPT = """You are a broadcast script writer for "Shovel News", an AI-generated daily news podcast.

Write a complete broadcast script with the following structure:
1. Host Intro (Shovel, 50-75 words) - greet listeners, preview topics
2. Segment 1 - Tech news (Nova, 250-350 words)
3. Segment 2 - International news (Jessica, 250-350 words)
4. Segment 3 - Politics/conflict (George, 250-350 words)
5. Segment 4 - Law/Business (Fable, 250-350 words)
6. Segment 5 - Quirky/fun closer (Puck, 200-300 words)
7. Host Outro (Shovel, 50 words)

Between each segment, include a brief host handoff (Shovel, 15-25 words).

WRITING RULES:
- Short sentences. Strong verbs. Active voice.
- NO adverbs ("ran quickly" -> "sprinted")
- NO hedging ("perhaps", "sort of", "I think")
- NO AI-isms ("quietly reshaping", "it's not X, it's Y", "let that sink in")
- Simple words ("use" not "utilize")
- Use ... for brief pauses, -- for mid-sentence breaks
- Spell out acronyms on first use
- Each correspondent has a personality - let it show
- Transitions between segments should be natural

OUTPUT FORMAT:
Return a JSON array where each element has:
- "segment": segment number (1-11)
- "character": character name (shovel, nova, jessica, george, fable, puck)
- "text": the spoken text for this segment
- "type": "intro", "content", "handoff", or "outro"

Each content segment should include a "sources" array with objects containing "title" and "url" for the news stories referenced in that segment. Handoff, intro, and outro segments should have an empty "sources" array.

Return ONLY the JSON array, no other text."""


def call_llm(prompt, api_base=DEFAULT_API_BASE, model=DEFAULT_MODEL):
    """Call the local LLM via OpenAI-compatible API."""
    url = f"{api_base}/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "presence_penalty": 0.0,
        "max_tokens": 4096,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except urllib.error.URLError as e:
        print(f"Error connecting to LLM at {api_base}: {e}", file=sys.stderr)
        print("Is vLLM running? Check: curl http://localhost:8000/v1/models", file=sys.stderr)
        sys.exit(1)


def parse_script(raw_text):
    """Parse the LLM output into script segments."""
    # Try to extract JSON from the response
    text = raw_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # Find JSON array
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        print("Error: Could not find JSON array in LLM output", file=sys.stderr)
        print("Raw output:", file=sys.stderr)
        print(text[:500], file=sys.stderr)
        sys.exit(1)

    try:
        segments = json.loads(text[start:end])
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        print("Raw JSON:", file=sys.stderr)
        print(text[start:end][:500], file=sys.stderr)
        sys.exit(1)

    return segments


def write_segments(segments, output_dir):
    """Write each segment to a numbered text file."""
    os.makedirs(output_dir, exist_ok=True)

    manifest = []
    for seg in segments:
        num = seg["segment"]
        character = seg["character"]
        text = seg["text"]
        seg_type = seg.get("type", "content")

        filename = f"{num:02d}_{character}_{seg_type}.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w") as f:
            f.write(text)

        voice = CHARACTERS.get(character, {}).get("voice", "am_michael")
        entry = {
            "segment": num,
            "character": character,
            "type": seg_type,
            "file": filename,
            "voice": voice,
            "text_length": len(text),
        }
        # Include sources from LLM output if present
        if "sources" in seg and seg["sources"]:
            entry["sources"] = seg["sources"]
        manifest.append(entry)
        print(f"  {filename} ({len(text)} chars)", file=sys.stderr)

    # Write manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  manifest.json", file=sys.stderr)

    return manifest


DEMO_TOPICS = [
    "A new open-source AI model beats proprietary models on coding benchmarks",
    "International climate summit reaches surprise agreement on carbon pricing",
    "Congressional hearing on tech regulation draws sharp exchanges",
    "Major tech company announces record quarterly earnings amid antitrust scrutiny",
    "Scientists discover high-speed internet can be transmitted through potatoes",
]


def main():
    parser = argparse.ArgumentParser(description="Generate broadcast scripts using local LLM")
    parser.add_argument("--topics", help="Comma-separated news topics")
    parser.add_argument("--topics-file", help="File with one topic per line")
    parser.add_argument("--date", default=str(date.today()), help="Broadcast date (default: today)")
    parser.add_argument("--output-dir", help="Output directory (default: scripts/<date>/)")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help=f"LLM API base URL (default: {DEFAULT_API_BASE})")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--demo", action="store_true", help="Use demo topics")
    parser.add_argument("--raw", action="store_true", help="Print raw LLM output without parsing")

    args = parser.parse_args()

    # Get topics
    structured_topics = None  # JSON topics from fetch_news.py
    if args.demo:
        topics = DEMO_TOPICS
    elif args.topics:
        topics = [t.strip() for t in args.topics.split(",")]
    elif args.topics_file:
        with open(args.topics_file) as f:
            content = f.read().strip()
            # Try JSON first (from fetch_news.py)
            if content.startswith("["):
                try:
                    structured_topics = json.loads(content)
                    topics = [t["title"] for t in structured_topics]
                except (json.JSONDecodeError, KeyError):
                    topics = [line.strip() for line in content.split("\n") if line.strip()]
            else:
                topics = [line.strip() for line in content.split("\n") if line.strip()]
    else:
        print("Error: Provide --topics, --topics-file, or --demo", file=sys.stderr)
        sys.exit(1)

    # Build prompt
    if structured_topics:
        # Rich prompt with source material and citations
        topic_blocks = []
        for t in structured_topics:
            block = f"- **{t['title']}**"
            if t.get("summary"):
                block += f"\n  Context: {t['summary']}"
            if t.get("url"):
                block += f"\n  Source: {t['url']} ({t.get('source', 'unknown')})"
            if t.get("beat"):
                block += f"\n  Beat: {t['beat']} (assign to {BEAT_TO_CORRESPONDENT.get(t['beat'], t['beat'])})"
            topic_blocks.append(block)
        topic_list = "\n".join(topic_blocks)

        prompt = f"""Write a Shovel News broadcast script for {args.date}.

Today's news stories (with source material — use these facts, do NOT invent details):
{topic_list}

Correspondent assignments:
- Nova: tech/science stories
- Jessica: international stories
- George: politics/conflict stories
- Fable: law/business stories
- Puck: quirky/fun stories

IMPORTANT: Each content segment MUST include a "sources" array referencing the stories used.
Use the provided facts and context. Do NOT fabricate statistics or quotes.
Combine related stories within a beat if needed. Every beat should have at least one story."""
    else:
        topic_list = "\n".join(f"- {t}" for t in topics)
        prompt = f"""Write a Shovel News broadcast script for {args.date}.

Today's news topics:
{topic_list}

Assign topics to correspondents based on their beats:
- Nova: tech/science topics
- Jessica: international topics
- George: politics/conflict topics
- Fable: law/business topics
- Puck: quirky/fun topics

If a topic doesn't fit a beat perfectly, assign it to the closest match. You may combine or expand on topics as needed to fill each correspondent's segment."""

    # Also pass structured topics for source tracking in manifest
    source_lookup = {}
    if structured_topics:
        for t in structured_topics:
            source_lookup[t["title"].lower()[:60]] = {
                "title": t["title"],
                "url": t.get("url", ""),
                "source": t.get("source", ""),
            }

    # Generate
    print(f"Generating script for {args.date}...", file=sys.stderr)
    print(f"  Model: {args.model}", file=sys.stderr)
    print(f"  Topics: {len(topics)}", file=sys.stderr)

    raw = call_llm(prompt, api_base=args.api_base, model=args.model)

    if args.raw:
        print(raw)
        return

    # Parse
    print("Parsing script...", file=sys.stderr)
    segments = parse_script(raw)

    # Write
    output_dir = args.output_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts", args.date
    )
    print(f"Writing {len(segments)} segments to {output_dir}/", file=sys.stderr)
    manifest = write_segments(segments, output_dir)

    # Summary
    total_chars = sum(s["text_length"] for s in manifest)
    print(f"\nScript generated: {len(segments)} segments, {total_chars} characters total", file=sys.stderr)
    print(f"Output: {output_dir}/", file=sys.stderr)

    # Print manifest to stdout for piping
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
