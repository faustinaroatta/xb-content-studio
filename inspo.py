"""Live 'What's new in architecture' feed.

Reads the public RSS feeds of leading architecture publications (they publish what studios
around the world are doing, several times a day) and returns text-first cards, newest first.
Cached for a few hours so the wall refreshes on its own.
"""
import datetime as dt
import html
import re
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import requests

FEEDS = [
    {"name": "ArchDaily", "url": "https://feeds.feedburner.com/Archdaily"},
    {"name": "Dezeen", "url": "https://www.dezeen.com/architecture/feed/"},
    {"name": "Dezeen · Interiors", "url": "https://www.dezeen.com/interiors/feed/"},
]

UA = {"User-Agent": "Mozilla/5.0 (XB Content Studio; +https://xb-content-studio.streamlit.app/?privacy)"}
NS_CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"


def _clean(text, limit=380):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    text = re.sub(r"The post .* appeared first on .*$", "", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def _date(value):
    try:
        d = parsedate_to_datetime(value)
        return d.replace(tzinfo=None) if d.tzinfo is None else d.astimezone(dt.timezone.utc).replace(tzinfo=None)
    except Exception:  # noqa: BLE001
        return None


def _studio(title, source):
    # ArchDaily titles are "Project / Studio"
    if source.startswith("ArchDaily") and " / " in title:
        return title.split(" / ", 1)[1].strip()
    # Dezeen titles often start with the studio: "Takero Shimazaki upgrades …"
    m = re.match(r"^([A-Z][\w&'.\-]*(?:\s+(?:[A-Z][\w&'.\-]*|and|de|da|&))*)\s+(?:creates|designs|builds|"
                 r"completes|unveils|upgrades|transforms|converts|adds|uses|wraps|reveals|turns|tops|"
                 r"renovates|extends|places|overhauls|stacks|nestles|clads|restores|revamps)\b", title)
    return m.group(1) if m else ""


def parse(xml_bytes, source):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):
        title = _clean(it.findtext("title"), 200)
        link = (it.findtext("link") or "").strip()
        desc = it.findtext("description") or ""
        body = it.findtext(NS_CONTENT) or ""
        summary = _clean(desc) or _clean(body)
        if not title or not link:
            continue
        items.append({
            "source": source, "title": title, "link": link, "summary": summary,
            "studio": _studio(title, source), "published": _date(it.findtext("pubDate")),
        })
    return items


def fetch_all(feeds=None):
    """Returns (items, errors). Never raises."""
    items, errors = [], []
    for f in feeds or FEEDS:
        try:
            r = requests.get(f["url"], headers=UA, timeout=20)
            r.raise_for_status()
            items.extend(parse(r.content, f["name"]))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{f['name']}: {str(e)[:120]}")
    seen, unique = set(), []
    for i in sorted(items, key=lambda x: x["published"] or dt.datetime.min, reverse=True):
        if i["link"] not in seen:
            seen.add(i["link"])
            unique.append(i)
    return unique, errors
