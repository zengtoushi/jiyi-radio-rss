#!/usr/bin/env python3
"""Build a small, self-hosted RSS feed for the public Xiaoyuzhou podcast page.

Only public episode metadata is fetched. Audio remains hosted by Xiaoyuzhou.
"""
from __future__ import annotations

import email.utils
import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

PODCAST_ID = "64341d0ec21112da279464c6"
PODCAST_URL = f"https://www.xiaoyuzhoufm.com/podcast/{PODCAST_ID}"
EPISODE_URL = "https://www.xiaoyuzhoufm.com/episode/"
FEED_URL = os.environ.get(
    "FEED_URL",
    "https://zengtoushi.github.io/jiyi-radio-rss/feed.xml",
)
KEEP = 30
STATE_PATH = Path("state/episodes.json")
OUTPUT_PATH = Path("docs/feed.xml")
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def parse_date(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        # Xiaoyuzhou page data normally uses an ISO string, but tolerate epoch values.
        stamp = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(stamp, tz=timezone.utc)
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except ValueError:
        try:
            return email.utils.parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None


def fetch_source():
    response = requests.get(
        PODCAST_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        timeout=40,
    )
    response.raise_for_status()
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        response.text,
        flags=re.S,
    )
    if not match:
        raise RuntimeError("Could not find Xiaoyuzhou page data (__NEXT_DATA__).")
    data = json.loads(html.unescape(match.group(1)))
    page = data.get("props", {}).get("pageProps", {})
    podcast = page.get("podcast") or {}
    raw_episodes = podcast.get("episodes") or []
    if not raw_episodes:
        raise RuntimeError("Xiaoyuzhou returned no episodes; keeping the previous feed.")
    return podcast, raw_episodes


def normalize_episode(raw):
    eid = raw.get("eid") or raw.get("id")
    enclosure = raw.get("enclosure") or {}
    audio = enclosure.get("url") or raw.get("audioUrl")
    if not eid or not audio:
        return None
    parsed = urlparse(audio)
    if parsed.scheme not in ("http", "https"):
        return None
    pub = parse_date(raw.get("pubDate") or raw.get("pub_date"))
    return {
        "eid": str(eid),
        "title": str(raw.get("title") or "Untitled episode").strip(),
        "url": EPISODE_URL + str(eid),
        "audio": audio,
        "audio_type": enclosure.get("type") or "audio/mpeg",
        "audio_length": str(enclosure.get("length") or raw.get("size") or 0),
        "duration": int(raw.get("duration") or 0),
        "pub_date": pub.isoformat() if pub else None,
        "description": str(raw.get("shownotes") or raw.get("description") or ""),
        "image": (
            (raw.get("image") or {}).get("smallPicUrl")
            if isinstance(raw.get("image"), dict)
            else raw.get("image")
        ),
    }


def load_state():
    if not STATE_PATH.exists():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return {item["eid"]: item for item in data.get("episodes", [])}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def build_feed(podcast, episodes):
    channel = ET.Element("channel")
    ET.SubElement(channel, "title").text = podcast.get("title") or "记意电波"
    ET.SubElement(channel, "link").text = PODCAST_URL
    ET.SubElement(channel, "description").text = (
        podcast.get("description") or "一档意大利足球播客节目。"
    )
    ET.SubElement(channel, "language").text = "zh-CN"
    ET.SubElement(channel, "lastBuildDate").text = email.utils.format_datetime(
        datetime.now(timezone.utc)
    )
    atom = ET.SubElement(channel, f"{{{NS['atom']}}}link")
    atom.set("href", FEED_URL)
    atom.set("rel", "self")
    atom.set("type", "application/rss+xml")

    image_url = None
    image = podcast.get("image")
    if isinstance(image, dict):
        image_url = image.get("smallPicUrl") or image.get("picUrl")
    elif isinstance(image, str):
        image_url = image
    if image_url:
        image_node = ET.SubElement(channel, "image")
        ET.SubElement(image_node, "url").text = image_url
        ET.SubElement(image_node, "title").text = podcast.get("title") or "记意电波"
        ET.SubElement(image_node, "link").text = PODCAST_URL
        ET.SubElement(channel, f"{{{NS['itunes']}}}image", {"href": image_url})

    ET.SubElement(channel, f"{{{NS['itunes']}}}author").text = (
        podcast.get("author") or "记意电波"
    )
    ET.SubElement(channel, f"{{{NS['itunes']}}}summary").text = (
        podcast.get("description") or "一档意大利足球播客节目。"
    )
    ET.SubElement(channel, f"{{{NS['itunes']}}}explicit").text = "false"
    ET.SubElement(channel, f"{{{NS['itunes']}}}type").text = "episodic"

    for episode in episodes:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = episode["title"]
        ET.SubElement(item, "link").text = episode["url"]
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = episode["url"]
        ET.SubElement(item, "enclosure", {
            "url": episode["audio"],
            "length": str(episode.get("audio_length") or 0),
            "type": episode.get("audio_type") or "audio/mpeg",
        })
        pub = parse_date(episode.get("pub_date"))
        if pub:
            ET.SubElement(item, "pubDate").text = email.utils.format_datetime(pub)
        desc = episode.get("description") or ""
        ET.SubElement(item, "description").text = desc
        ET.SubElement(item, f"{{{NS['itunes']}}}summary").text = desc
        if episode.get("duration"):
            seconds = episode["duration"]
            hours, remainder = divmod(seconds, 3600)
            minutes, secs = divmod(remainder, 60)
            duration = f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"
            ET.SubElement(item, f"{{{NS['itunes']}}}duration").text = duration
        if episode.get("image"):
            ET.SubElement(item, f"{{{NS['itunes']}}}image", {"href": episode["image"]})

    root = ET.Element("rss", {"version": "2.0"})
    root.append(channel)
    return ET.ElementTree(root)


def main():
    podcast, raw_episodes = fetch_source()
    known = load_state()
    fresh = 0
    for raw in raw_episodes:
        item = normalize_episode(raw)
        if not item:
            continue
        old = known.get(item["eid"], {})
        # Preserve a previously captured audio URL if the page temporarily omits it.
        known[item["eid"]] = {**old, **{k: v for k, v in item.items() if v not in (None, "")}}
        if item["eid"] not in old:
            fresh += 1

    if not known:
        raise RuntimeError("No usable episodes found; refusing to publish an empty feed.")

    all_items = list(known.values())
    all_items.sort(
        key=lambda x: parse_date(x.get("pub_date")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    all_items = all_items[:KEEP]

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"podcast_id": PODCAST_ID, "episodes": all_items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tree = build_feed(podcast, all_items)
    tree.write(OUTPUT_PATH, encoding="utf-8", xml_declaration=True)
    print(f"Published {len(all_items)} episodes; discovered {fresh} new episode(s).")
    print(f"Newest: {all_items[0]['title']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
