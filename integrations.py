"""Automatic metrics sync from linked accounts (Instagram Graph API and LinkedIn API).

Each account activates itself once its credentials are in secrets. If an API fails or lacks
permissions, it is logged and everything else keeps working.
"""
import datetime as dt
from urllib.parse import quote

import requests

import db
from config import SYNC_EVERY_HOURS, get_secret

IG_HOST = (get_secret("IG_GRAPH_HOST") or "https://graph.facebook.com/v23.0").rstrip("/")
LI_VERSION = get_secret("LINKEDIN_VERSION") or "202509"

CREDS = {
    "ig_xb": ("IG_USER_ID", "IG_ACCESS_TOKEN"),
    "li_xb": ("LI_ORG_ID", "LI_ORG_TOKEN"),
    "li_john": ("LI_JOHN_PERSON_ID", "LI_JOHN_TOKEN"),
    "li_ximena": ("LI_XIMENA_PERSON_ID", "LI_XIMENA_TOKEN"),
}


def _ig_stored():
    import ig_oauth
    return ig_oauth.stored_token()


def is_configured(account):
    if account == "ig_xb" and _ig_stored():
        return True
    a, b = CREDS[account]
    return bool(get_secret(a)) and bool(get_secret(b))


# ---------------- Instagram ----------------
def _ig_insights(media_id, token, host=IG_HOST):
    for metrics in ("views,reach,saved,shares", "reach,saved,shares", "reach"):
        r = requests.get(f"{host}/{media_id}/insights",
                         params={"metric": metrics, "access_token": token}, timeout=30)
        if r.ok:
            out = {}
            for item in r.json().get("data", []):
                if item.get("values"):
                    val = item["values"][0].get("value")
                else:
                    val = (item.get("total_value") or {}).get("value")
                out[item["name"]] = val or 0
            return out
    return {}


def sync_instagram():
    stored = _ig_stored()
    if stored:   # connected with the "Connect Instagram" button
        import ig_oauth
        ig_oauth.maybe_refresh()
        uid, tok, host = "me", ig_oauth.stored_token(), "https://graph.instagram.com/v23.0"
    else:        # token pasted manually in secrets
        uid, tok, host = get_secret("IG_USER_ID"), get_secret("IG_ACCESS_TOKEN"), IG_HOST
    r = requests.get(f"{host}/{uid}/media", params={
        "fields": "id,caption,media_type,permalink,timestamp,like_count,comments_count",
        "limit": 50, "access_token": tok}, timeout=30)
    r.raise_for_status()
    n = 0
    for m in r.json().get("data", []):
        ins = _ig_insights(m["id"], tok, host)
        db.upsert_metric({
            "account": "ig_xb", "external_id": m["id"], "permalink": m.get("permalink"),
            "caption": (m.get("caption") or "")[:2000], "published_at": (m.get("timestamp") or "")[:19],
            "media_type": m.get("media_type"), "likes": m.get("like_count") or 0,
            "comments": m.get("comments_count") or 0, "views": ins.get("views", 0) or 0,
            "reach": ins.get("reach", 0) or 0, "shares": ins.get("shares", 0) or 0,
            "saves": ins.get("saved", 0) or 0, "source": "api",
        })
        n += 1
    return n


# ---------------- LinkedIn ----------------
def _li_headers(tok):
    return {"Authorization": f"Bearer {tok}", "LinkedIn-Version": LI_VERSION,
            "X-Restli-Protocol-Version": "2.0.0"}


def _li_social(urn, tok):
    r = requests.get(f"https://api.linkedin.com/rest/socialMetadata/{quote(urn, safe='')}",
                     headers=_li_headers(tok), timeout=30)
    if r.ok:
        j = r.json()
        likes = sum((v or {}).get("count", 0) for v in (j.get("reactionSummaries") or {}).values())
        comments = (j.get("commentSummary") or {}).get("count", 0)
        return likes, comments
    r = requests.get(f"https://api.linkedin.com/v2/socialActions/{quote(urn, safe='')}",
                     headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    if r.ok:
        j = r.json()
        return ((j.get("likesSummary") or {}).get("totalLikes", 0),
                (j.get("commentsSummary") or {}).get("aggregatedTotalComments", 0))
    return 0, 0


def _li_org_stats(org_urn, urn, tok):
    """Impressions for a company page post."""
    kind = "ugcPosts" if ":ugcPost:" in urn else "shares"
    url = (f"https://api.linkedin.com/rest/organizationalEntityShareStatistics?q=organizationalEntity"
           f"&organizationalEntity={quote(org_urn, safe='')}&{kind}=List({quote(urn, safe='')})")
    r = requests.get(url, headers=_li_headers(tok), timeout=30)
    if not r.ok:
        return {}
    els = r.json().get("elements") or []
    return (els[0].get("totalShareStatistics") or {}) if els else {}


def sync_linkedin(account):
    id_key, tok_key = CREDS[account]
    raw_id, tok = str(get_secret(id_key)), get_secret(tok_key)
    is_org = account == "li_xb"
    author = raw_id if raw_id.startswith("urn:") else (
        f"urn:li:organization:{raw_id}" if is_org else f"urn:li:person:{raw_id}")
    r = requests.get("https://api.linkedin.com/rest/posts",
                     params={"author": author, "q": "author", "count": 50, "sortBy": "LAST_MODIFIED"},
                     headers=_li_headers(tok), timeout=30)
    r.raise_for_status()
    n = 0
    for p in r.json().get("elements", []):
        urn = p["id"]
        likes, comments = _li_social(urn, tok)
        stats = _li_org_stats(author, urn, tok) if is_org else {}
        ts = p.get("publishedAt") or p.get("createdAt")
        pub = dt.datetime.fromtimestamp(ts / 1000).isoformat(timespec="seconds") if ts else ""
        db.upsert_metric({
            "account": account, "external_id": urn,
            "permalink": f"https://www.linkedin.com/feed/update/{urn}/",
            "caption": (p.get("commentary") or "")[:2000], "published_at": pub,
            "media_type": "LinkedIn post", "likes": stats.get("likeCount", likes) or likes,
            "comments": stats.get("commentCount", comments) or comments,
            "views": stats.get("impressionCount", 0) or 0,
            "reach": stats.get("uniqueImpressionsCount", 0) or 0,
            "shares": stats.get("shareCount", 0) or 0, "saves": 0, "source": "api",
        })
        n += 1
    return n


# ---------------- Orquestación ----------------
def sync_all():
    log = []
    for acc in CREDS:
        if not is_configured(acc):
            log.append((acc, "not linked", 0))
            continue
        try:
            n = sync_instagram() if acc == "ig_xb" else sync_linkedin(acc)
            log.append((acc, "ok", n))
            db.set_meta(f"sync_{acc}", f"ok · {n} posts · {db.now()}")
        except Exception as e:  # noqa: BLE001
            msg = str(e)[:300]
            log.append((acc, f"error: {msg}", 0))
            db.set_meta(f"sync_{acc}", f"error · {db.now()} · {msg}")
    db.set_meta("last_sync", db.now())
    return log


def maybe_auto_sync():
    """Syncs automatically if more than SYNC_EVERY_HOURS have passed since the last sync."""
    if not any(is_configured(a) for a in CREDS):
        return None
    last = db.get_meta("last_sync")
    if last:
        try:
            if dt.datetime.now() - dt.datetime.fromisoformat(last) < dt.timedelta(hours=SYNC_EVERY_HOURS):
                return None
        except ValueError:
            pass
    return sync_all()
