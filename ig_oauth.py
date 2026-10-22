"""'Connect Instagram' button: Instagram API with Instagram Login (OAuth).

One-time setup (in Meta): create the app, add @xb.architecture, set the redirect URI and
copy the Instagram App ID / App Secret into Streamlit secrets as IG_APP_ID / IG_APP_SECRET.
After that anyone on the team clicks "Connect Instagram" in the app, logs in with
@xb.architecture and the long-lived token is stored in the database and renewed automatically.
"""
import datetime as dt
import secrets as pysecrets
from urllib.parse import urlencode

import requests

import db
from config import get_secret

SCOPES = "instagram_business_basic,instagram_business_manage_insights"
GRAPH = "https://graph.instagram.com"


def app_url():
    url = (get_secret("APP_URL") or "https://xb-content-studio.streamlit.app").strip()
    return url if url.endswith("/") else url + "/"


def oauth_ready():
    return bool(get_secret("IG_APP_ID")) and bool(get_secret("IG_APP_SECRET"))


def auth_link():
    state = pysecrets.token_urlsafe(16)
    db.set_meta("ig_oauth_state", f"{state}|{db.now()}")
    params = {
        "client_id": str(get_secret("IG_APP_ID")).strip(),
        "redirect_uri": app_url(),
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "enable_fb_login": "false",
        "force_reauth": "true",
    }
    return "https://www.instagram.com/oauth/authorize?" + urlencode(params)


def _valid_state(state):
    saved = db.get_meta("ig_oauth_state") or ""
    if "|" not in saved or not state:
        return False
    value, created = saved.split("|", 1)
    try:
        fresh = dt.datetime.now() - dt.datetime.fromisoformat(created) < dt.timedelta(hours=1)
    except ValueError:
        fresh = False
    return fresh and pysecrets.compare_digest(value, state)


def _save_token(token, expires_in):
    db.set_meta("ig_token", token)
    db.set_meta("ig_token_issued", db.now())
    expires = dt.datetime.now() + dt.timedelta(seconds=int(expires_in or 5183944))
    db.set_meta("ig_token_expires", expires.isoformat(timespec="seconds"))


def handle_callback(code, state):
    """Exchanges the code for a long-lived token. Returns (ok, message)."""
    if not _valid_state(state):
        return False, "Link expired or invalid, please try again. / El link venció, probá de nuevo."
    code = code.split("#")[0].strip()
    r = requests.post("https://api.instagram.com/oauth/access_token", data={
        "client_id": str(get_secret("IG_APP_ID")).strip(),
        "client_secret": str(get_secret("IG_APP_SECRET")).strip(),
        "grant_type": "authorization_code",
        "redirect_uri": app_url(),
        "code": code,
    }, timeout=30)
    if not r.ok:
        return False, f"Instagram: {r.text[:200]}"
    j = r.json()
    data = (j.get("data") or [j])[0]
    short = data.get("access_token")
    r2 = requests.get(f"{GRAPH}/access_token", params={
        "grant_type": "ig_exchange_token",
        "client_secret": str(get_secret("IG_APP_SECRET")).strip(),
        "access_token": short,
    }, timeout=30)
    if not r2.ok:
        return False, f"Instagram: {r2.text[:200]}"
    j2 = r2.json()
    _save_token(j2["access_token"], j2.get("expires_in"))
    me = requests.get(f"{GRAPH}/me", params={"fields": "user_id,username",
                                            "access_token": j2["access_token"]}, timeout=30)
    if me.ok:
        db.set_meta("ig_user_id", str(me.json().get("user_id") or me.json().get("id") or ""))
        db.set_meta("ig_username", me.json().get("username", ""))
    db.set_meta("ig_oauth_state", "")
    return True, f"@{db.get_meta('ig_username') or 'instagram'}"


def stored_token():
    return db.get_meta("ig_token") or ""


def disconnect():
    for k in ["ig_token", "ig_token_issued", "ig_token_expires", "ig_user_id", "ig_username"]:
        db.set_meta(k, "")


def maybe_refresh():
    """Renews the long-lived token when it's older than 1 day and expires in < 30 days."""
    tok = stored_token()
    if not tok:
        return
    try:
        issued = dt.datetime.fromisoformat(db.get_meta("ig_token_issued"))
        expires = dt.datetime.fromisoformat(db.get_meta("ig_token_expires"))
    except (TypeError, ValueError):
        return
    now = dt.datetime.now()
    if now - issued < dt.timedelta(days=1) or expires - now > dt.timedelta(days=30) or expires < now:
        return
    r = requests.get(f"{GRAPH}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": tok}, timeout=30)
    if r.ok:
        _save_token(r.json()["access_token"], r.json().get("expires_in"))
