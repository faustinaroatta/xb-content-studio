"""Live Instagram feed of OTHER accounts (studios / competitors) — official Business Discovery API.

Shows their real latest posts: photo/video, full caption, likes, comments, date, link.
Requirements (one time, in Meta): an app with Facebook Login, @xb.architecture linked to a Facebook Page,
and a token with instagram_basic + pages_show_list + pages_read_engagement + business_management.
Secrets: FB_ACCESS_TOKEN and FB_IG_USER_ID (XB's Instagram business account id).
Only public Business/Creator accounts can be read; handles that don't resolve are skipped silently.
"""
import requests

from config import get_secret

GRAPH = (get_secret("FB_GRAPH_HOST") or "https://graph.facebook.com/v23.0").rstrip("/")

# Accounts to watch. First handle that resolves wins (exact handles could not all be verified).
WATCH = [
    {"name": "BIG – Bjarke Ingels Group", "where": "🌍", "handles": ["big_builds"]},
    {"name": "Zaha Hadid Architects", "where": "🌍", "handles": ["zahahadidarchitects"]},
    {"name": "SOM", "where": "🇺🇸", "handles": ["skidmoreowingsmerrill"]},
    {"name": "Gensler", "where": "🇺🇸", "handles": ["gensler_design", "gensler"]},
    {"name": "Rojkind Arquitectos", "where": "🇲🇽", "handles": ["rojkindarquitectos"]},
    {"name": "Legorreta", "where": "🇲🇽", "handles": ["legorreta_arqs"]},
    {"name": "Luciano Kruk", "where": "🇦🇷", "handles": ["lucianokruk", "krukarquitectos", "lucianokrukarquitectos"]},
    {"name": "Andrés Remy Arquitectos", "where": "🇦🇷", "handles": ["andresremyarquitectos", "andresremy"]},
    {"name": "BMA Bodas Miani Anger", "where": "🇦🇷", "handles": ["bmaarquitectos", "bodasmiananger"]},
    {"name": "Besonías Almeida", "where": "🇦🇷", "handles": ["besoniasalmeida", "besoniasalmeidaarquitectos"]},
    {"name": "MAPA", "where": "🇺🇾", "handles": ["mapa.arq", "mapaarchitects", "mapa_arq"]},
    {"name": "Martín Gómez Arquitectos", "where": "🇺🇾", "handles": ["martingomezarquitectos", "estudiomartingomez"]},
    {"name": "Arquitectonica", "where": "🇺🇸 Miami", "handles": ["arquitectonica", "arquitectonicaintl"]},
    {"name": "Oppenheim Architecture", "where": "🇺🇸 Miami", "handles": ["oppenheimarchitecture", "oppenheim_architecture"]},
    {"name": "Choeff Levy Fischman", "where": "🇺🇸 Miami", "handles": ["choefflevyfischman", "clfarchitects"]},
    {"name": "Kobi Karp", "where": "🇺🇸 Miami", "handles": ["kobikarp", "kobikarparchitecture"]},
    {"name": "Touzet Studio", "where": "🇺🇸 Miami", "handles": ["touzetstudio"]},
]

FIELDS = ("business_discovery.username({u}){{username,name,profile_picture_url,followers_count,"
          "media.limit({n}){{id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,"
          "like_count,comments_count}}}}")


def ready():
    return bool(get_secret("FB_ACCESS_TOKEN")) and bool(get_secret("FB_IG_USER_ID"))


def _one(handle, n):
    r = requests.get(f"{GRAPH}/{str(get_secret('FB_IG_USER_ID')).strip()}",
                     params={"fields": FIELDS.format(u=handle, n=n),
                             "access_token": str(get_secret("FB_ACCESS_TOKEN")).strip()}, timeout=25)
    if not r.ok:
        return None, r.text[:160]
    return r.json().get("business_discovery"), ""


def fetch_all(extra_handles=(), per_account=6):
    """Returns (posts, accounts_found, errors). Never raises."""
    posts, found, errors = [], [], []
    watch = list(WATCH) + [{"name": h, "where": "", "handles": [h]} for h in extra_handles if h]
    for acc in watch:
        bd, err = None, ""
        for h in acc["handles"]:
            try:
                bd, err = _one(h.strip().lstrip("@"), per_account)
            except Exception as e:  # noqa: BLE001
                bd, err = None, str(e)[:160]
            if bd:
                break
        if not bd:
            errors.append(f"{acc['name']}: {err or 'not found'}")
            continue
        if any(f["username"] == bd.get("username") for f in found):
            continue
        found.append({"name": acc["name"], "where": acc["where"], "username": bd.get("username"),
                      "followers": bd.get("followers_count"), "pic": bd.get("profile_picture_url")})
        for m in (bd.get("media") or {}).get("data", []):
            image = m.get("thumbnail_url") if m.get("media_type") == "VIDEO" else m.get("media_url")
            posts.append({
                "account": bd.get("name") or acc["name"], "username": bd.get("username"),
                "where": acc["where"], "pic": bd.get("profile_picture_url"),
                "followers": bd.get("followers_count") or 0, "image": image or "",
                "type": m.get("media_type"), "caption": m.get("caption") or "",
                "likes": m.get("like_count"), "comments": m.get("comments_count"),
                "timestamp": m.get("timestamp") or "", "link": m.get("permalink"),
            })
    seen, unique = set(), []
    for p in sorted(posts, key=lambda p: p["timestamp"], reverse=True):
        if p["link"] not in seen:
            seen.add(p["link"])
            unique.append(p)
    posts = unique
    return posts, found, errors
