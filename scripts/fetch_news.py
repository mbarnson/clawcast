#!/usr/bin/env python3
"""
Fetch news from RSS/Atom feeds for broadcast script generation.

Pulls articles from configured feeds, categorizes by correspondent beat,
deduplicates against previously reported stories, and outputs structured
topics with source URLs for generate_script.py.

Usage:
    ./fetch_news.py                          # Use default feeds
    ./fetch_news.py --feeds feeds.json       # Custom feed config
    ./fetch_news.py --max-per-beat 3         # Limit stories per beat
    ./fetch_news.py --no-dedup               # Skip dedup check

Output: JSON array of topics with source URLs, suitable for piping to
generate_script.py via --topics-file.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, date
from html import unescape

WORKSPACE_DIR = os.path.expanduser("~/workspace")
REPORTED_FILE = os.path.join(WORKSPACE_DIR, "news-reported.md")

# Default RSS feeds organized by beat
DEFAULT_FEEDS = {
    "tech": [
        {"url": "https://hnrss.org/newest?points=100&count=10", "name": "Hacker News (100+)"},
        {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge"},
        {"url": "https://feeds.arstechnica.com/arstechnica/index", "name": "Ars Technica"},
    ],
    "international": [
        {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "name": "BBC World"},
        {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "name": "NYT World"},
    ],
    "politics": [
        {"url": "https://feeds.bbci.co.uk/news/politics/rss.xml", "name": "BBC Politics"},
        {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml", "name": "NYT Politics"},
    ],
    "business": [
        {"url": "https://feeds.bbci.co.uk/news/business/rss.xml", "name": "BBC Business"},
        {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "name": "NYT Business"},
    ],
    "quirky": [
        {"url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "name": "BBC Science"},
        {"url": "https://www.reddit.com/r/UpliftingNews/.rss?limit=10", "name": "r/UpliftingNews"},
    ],
}

# Map beats to ClawCast correspondents
BEAT_TO_CORRESPONDENT = {
    "tech": "nova",
    "international": "jessica",
    "politics": "george",
    "business": "fable",
    "quirky": "puck",
}


def fetch_feed(url, timeout=15):
    """Fetch and parse an RSS/Atom feed. Returns list of articles."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "ClawCast/1.0 (news podcast generator)",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  Warning: Failed to fetch {url}: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        print(f"  Warning: Failed to parse {url}: {e}", file=sys.stderr)
        return []

    articles = []

    # RSS 2.0
    for item in root.findall(".//item"):
        article = _parse_rss_item(item)
        if article:
            articles.append(article)

    # Atom
    if not articles:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//atom:entry", ns):
            article = _parse_atom_entry(entry, ns)
            if article:
                articles.append(article)
        # Try without namespace (some feeds don't use it)
        if not articles:
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                article = _parse_atom_entry_no_ns(entry)
                if article:
                    articles.append(article)

    return articles


def _parse_rss_item(item):
    """Parse an RSS 2.0 <item>."""
    title = _text(item, "title")
    link = _text(item, "link")
    desc = _text(item, "description")
    pub_date = _text(item, "pubDate")

    if not title:
        return None

    # Clean HTML from description
    if desc:
        desc = _strip_html(desc)
        desc = desc[:500]  # Truncate long descriptions

    return {
        "title": unescape(title),
        "url": link or "",
        "summary": unescape(desc) if desc else "",
        "published": pub_date or "",
    }


def _parse_atom_entry(entry, ns):
    """Parse an Atom <entry> with namespace."""
    title_el = entry.find("atom:title", ns)
    link_el = entry.find("atom:link", ns)
    summary_el = entry.find("atom:summary", ns) or entry.find("atom:content", ns)

    title = title_el.text if title_el is not None and title_el.text else None
    if not title:
        return None

    link = link_el.get("href", "") if link_el is not None else ""
    summary = summary_el.text if summary_el is not None and summary_el.text else ""

    if summary:
        summary = _strip_html(summary)[:500]

    return {
        "title": unescape(title),
        "url": link,
        "summary": unescape(summary),
        "published": "",
    }


def _parse_atom_entry_no_ns(entry):
    """Parse Atom entry with inline namespace."""
    ns = "http://www.w3.org/2005/Atom"
    title_el = entry.find(f"{{{ns}}}title")
    link_el = entry.find(f"{{{ns}}}link")
    summary_el = entry.find(f"{{{ns}}}summary") or entry.find(f"{{{ns}}}content")

    title = title_el.text if title_el is not None and title_el.text else None
    if not title:
        return None

    link = link_el.get("href", "") if link_el is not None else ""
    summary = summary_el.text if summary_el is not None and summary_el.text else ""

    if summary:
        summary = _strip_html(summary)[:500]

    return {
        "title": unescape(title),
        "url": link,
        "summary": unescape(summary),
        "published": "",
    }


def _text(element, tag):
    """Get text content of a child element."""
    child = element.find(tag)
    return child.text if child is not None and child.text else None


def _strip_html(text):
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def load_reported(reported_file=REPORTED_FILE):
    """Load previously reported story URLs/titles from news-reported.md."""
    reported = set()
    if not os.path.exists(reported_file):
        return reported

    with open(reported_file) as f:
        for line in f:
            line = line.strip()
            # Extract URLs from markdown links [title](url)
            urls = re.findall(r'\((https?://[^)]+)\)', line)
            for url in urls:
                reported.add(url)
            # Also match bare titles after "- " bullets
            if line.startswith("- ") and not urls:
                title = line[2:].strip()
                if title:
                    reported.add(title.lower())
    return reported


def save_reported(articles, broadcast_date, reported_file=REPORTED_FILE):
    """Append covered stories to news-reported.md."""
    os.makedirs(os.path.dirname(reported_file), exist_ok=True)

    with open(reported_file, "a") as f:
        f.write(f"\n## {broadcast_date}\n\n")
        for article in articles:
            if article.get("url"):
                f.write(f"- [{article['title']}]({article['url']})\n")
            else:
                f.write(f"- {article['title']}\n")


def is_duplicate(article, reported):
    """Check if an article has been previously reported."""
    if article.get("url") and article["url"] in reported:
        return True
    if article.get("title") and article["title"].lower() in reported:
        return True
    return False


def fetch_all_feeds(feeds_config, max_per_beat=5, skip_dedup=False,
                    reported_file=REPORTED_FILE):
    """Fetch from all configured feeds, deduplicate, and organize by beat."""
    reported = set() if skip_dedup else load_reported(reported_file)

    results = {}
    all_used_articles = []

    for beat, feeds in feeds_config.items():
        beat_articles = []
        for feed_info in feeds:
            url = feed_info["url"]
            name = feed_info.get("name", url)
            print(f"  Fetching {name}...", file=sys.stderr)

            articles = fetch_feed(url)
            for article in articles:
                article["source"] = name
                article["beat"] = beat

            beat_articles.extend(articles)

        # Deduplicate
        unique = []
        seen_titles = set()
        for article in beat_articles:
            if is_duplicate(article, reported):
                continue
            # Also deduplicate within this fetch
            title_key = article["title"].lower()[:60]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            unique.append(article)

        # Take top N
        selected = unique[:max_per_beat]
        if selected:
            correspondent = BEAT_TO_CORRESPONDENT.get(beat, beat)
            results[beat] = {
                "correspondent": correspondent,
                "articles": selected,
            }
            all_used_articles.extend(selected)

        print(f"  {beat}: {len(articles)} fetched, {len(unique)} unique, "
              f"{len(selected)} selected", file=sys.stderr)

    return results, all_used_articles


def format_topics_for_script(results):
    """Format fetched news into topics structure for generate_script.py."""
    topics = []
    for beat, data in results.items():
        for article in data["articles"]:
            topic = {
                "beat": beat,
                "correspondent": data["correspondent"],
                "title": article["title"],
                "summary": article.get("summary", ""),
                "url": article.get("url", ""),
                "source": article.get("source", ""),
            }
            topics.append(topic)
    return topics


def write_topics_file(topics, output_path):
    """Write topics to a file for generate_script.py --topics-file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(topics, f, indent=2)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Fetch news from RSS/Atom feeds")
    parser.add_argument("--feeds", help="JSON file with feed configuration")
    parser.add_argument("--max-per-beat", type=int, default=3,
                        help="Max stories per beat (default: 3)")
    parser.add_argument("--no-dedup", action="store_true",
                        help="Skip deduplication against reported stories")
    parser.add_argument("--output", "-o", help="Output topics file (default: stdout)")
    parser.add_argument("--save-reported", action="store_true",
                        help="Append used stories to news-reported.md after output")
    parser.add_argument("--date", default=str(date.today()),
                        help="Broadcast date (default: today)")
    parser.add_argument("--reported-file", default=REPORTED_FILE,
                        help=f"Path to news-reported.md (default: {REPORTED_FILE})")
    parser.add_argument("--list-feeds", action="store_true",
                        help="List configured feeds and exit")

    args = parser.parse_args()

    # Load feed config
    if args.feeds:
        with open(args.feeds) as f:
            feeds_config = json.load(f)
    else:
        feeds_config = DEFAULT_FEEDS

    if args.list_feeds:
        for beat, feeds in feeds_config.items():
            print(f"\n{beat} ({BEAT_TO_CORRESPONDENT.get(beat, '?')}):")
            for feed in feeds:
                print(f"  - {feed.get('name', feed['url'])}: {feed['url']}")
        return

    print(f"Fetching news for {args.date}...", file=sys.stderr)

    results, used_articles = fetch_all_feeds(
        feeds_config,
        max_per_beat=args.max_per_beat,
        skip_dedup=args.no_dedup,
        reported_file=args.reported_file,
    )

    if not results:
        print("Error: No news articles found from any feed", file=sys.stderr)
        sys.exit(1)

    topics = format_topics_for_script(results)
    print(f"\nTotal topics: {len(topics)}", file=sys.stderr)

    # Output
    output = json.dumps(topics, indent=2)
    if args.output:
        write_topics_file(topics, args.output)
        print(f"Written to: {args.output}", file=sys.stderr)
    else:
        print(output)

    # Save reported
    if args.save_reported and used_articles:
        save_reported(used_articles, args.date, args.reported_file)
        print(f"Appended {len(used_articles)} stories to {args.reported_file}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
