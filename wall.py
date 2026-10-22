"""Wall of REAL Instagram / LinkedIn posts (official embeds) + list of accounts to follow."""
import json
import re
from urllib.parse import quote_plus

from sqlalchemy import Column, Integer, String, Table, Text

import db

wall = Table(
    "wall", db.md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("url", Text),
    Column("platform", String(20)),
    Column("embed", Text),
    Column("author", String(120)),
    Column("note", Text),
    Column("votes", Integer, default=0),
    Column("voters", Text, default=""),
    Column("added_by", String(60)),
    Column("added_at", String(30)),
)
db.md.create_all(db.engine)

# Seed list of accounts to watch. "ig" / "li" are filled only where the handle was verified;
# the rest have a 🔎 button so the team confirms the exact account once.
SEED_ACCOUNTS = [
    # Argentina
    {"name": "Luciano Kruk (Kruk Arquitectos)", "country": "🇦🇷 Argentina", "why": "Concrete houses on the Atlantic coast; hugely shared online."},
    {"name": "Andrés Remy Arquitectos", "country": "🇦🇷 Argentina", "why": "Luxury residential, from Patagonia to Abu Dhabi."},
    {"name": "BMA Bodas Miani Anger", "country": "🇦🇷 Argentina", "why": "Large corporate and mixed-use projects in Buenos Aires."},
    {"name": "Besonías Almeida Arquitectos", "country": "🇦🇷 Argentina", "why": "Award-winning brick and concrete houses."},
    # Uruguay
    {"name": "MAPA Architects", "country": "🇺🇾 Uruguay", "why": "Innovative prefabricated cabins and modular homes."},
    {"name": "Martín Gómez Arquitectos", "country": "🇺🇾 Uruguay", "why": "Punta del Este luxury beach houses."},
    {"name": "Carlos Ott", "country": "🇺🇾 Uruguay", "why": "Towers and landmark buildings (Punta del Este, Dubai)."},
    # Miami / Florida
    {"name": "Arquitectonica", "country": "🇺🇸 Miami", "why": "Shaped Miami's skyline; residential towers."},
    {"name": "Oppenheim Architecture", "country": "🇺🇸 Miami", "why": "Minimal luxury villas and hotels."},
    {"name": "Choeff Levy Fischman", "country": "🇺🇸 Miami", "why": "Tropical-modern waterfront homes — direct competitor."},
    {"name": "Kobi Karp Architecture", "country": "🇺🇸 Miami", "why": "Coastal towers, hotels and resorts."},
    {"name": "Touzet Studio", "country": "🇺🇸 Miami", "why": "Luxury residential and hospitality, modernist."},
    # USA / global, massive
    {"name": "BIG – Bjarke Ingels Group", "country": "🌍 Global", "why": "Most followed studio; explains ideas with diagrams and humor.",
     "ig": "big_builds"},
    {"name": "Skidmore, Owings & Merrill (SOM)", "country": "🇺🇸 USA", "why": "Iconic towers; strong storytelling on LinkedIn.",
     "ig": "skidmoreowingsmerrill"},
    {"name": "Zaha Hadid Architects", "country": "🌍 Global", "why": "Iconic forms; render vs. reality posts."},
    {"name": "Gensler", "country": "🇺🇸 USA", "why": "Largest firm in the US; very active on LinkedIn."},
    {"name": "Rojkind Arquitectos", "country": "🇲🇽 Mexico", "why": "Bold Latin American studio with a big following.",
     "ig": "rojkindarquitectos"},
    {"name": "Legorreta", "country": "🇲🇽 Mexico", "why": "Color, light and craft; huge Latin American audience.",
     "ig": "legorreta_arqs"},
]


def accounts():
    raw = db.get_meta("wall_accounts")
    if raw:
        try:
            return json.loads(raw)
        except ValueError:
            pass
    return [dict(a) for a in SEED_ACCOUNTS]


def save_accounts(items):
    db.set_meta("wall_accounts", json.dumps(items, ensure_ascii=False))


def clean_handle(h):
    h = (h or "").strip()
    m = re.search(r"instagram\.com/([\w.]+)", h)
    if m:
        h = m.group(1)
    return h.lstrip("@").strip("/").lower()


def ig_profile_embed(handle):
    return f"https://www.instagram.com/{clean_handle(handle)}/embed/"


def li_posts_url(value):
    url = li_url(value).rstrip("/")
    return url if url.endswith("/posts") else url + "/posts/"


def search_url(name, platform):
    site = "instagram.com" if platform == "ig" else "linkedin.com/company"
    return "https://www.google.com/search?q=" + quote_plus(f"site:{site} {name}")


def ig_url(handle):
    return f"https://www.instagram.com/{handle.strip().lstrip('@').strip('/')}/"


def li_url(value):
    v = value.strip()
    return v if v.startswith("http") else f"https://www.linkedin.com/company/{v.strip('/')}/"


# ---------------- Post links → official embeds ----------------
IG_RE = re.compile(r"instagram\.com/(?:[\w.]+/)?(p|reel|reels|tv)/([\w-]+)", re.I)
LI_URN_RE = re.compile(r"urn:li:(activity|share|ugcPost):(\d+)", re.I)
LI_ACT_RE = re.compile(r"activity[-:](\d{15,25})", re.I)
LI_SLUG_RE = re.compile(r"linkedin\.com/posts/([\w%-]+?)_", re.I)
SRC_RE = re.compile(r"src=[\"']([^\"']+)[\"']", re.I)


def parse_link(text):
    """Accepts a post URL or an embed code. Returns dict(platform, embed, url, author) or None."""
    text = (text or "").strip()
    m = SRC_RE.search(text)
    if m and "linkedin.com/embed" in m.group(1):
        text = m.group(1)
    m = IG_RE.search(text)
    if m:
        kind = "reel" if m.group(1).lower().startswith("reel") else "p"
        code = m.group(2)
        return {"platform": "instagram", "url": f"https://www.instagram.com/{kind}/{code}/",
                "embed": f"https://www.instagram.com/{kind}/{code}/embed/captioned/", "author": ""}
    if "linkedin.com" in text:
        urn = None
        m = LI_URN_RE.search(text)
        if m:
            urn = f"urn:li:{m.group(1)}:{m.group(2)}"
        else:
            m = LI_ACT_RE.search(text)
            if m:
                urn = f"urn:li:activity:{m.group(1)}"
        if not urn:
            return None
        author = ""
        m = LI_SLUG_RE.search(text)
        if m:
            author = m.group(1).replace("-", " ").title()
        url = text if text.startswith("http") and "/embed/" not in text else f"https://www.linkedin.com/feed/update/{urn}/"
        return {"platform": "linkedin", "url": url,
                "embed": f"https://www.linkedin.com/embed/feed/update/{urn}", "author": author}
    return None
