"""Photographer photos, organized by project.

Files live in Supabase Storage (private bucket "photos") when SUPABASE_URL + SUPABASE_SERVICE_KEY are set;
otherwise in a local folder (testing only). Every upload is optimized: a 2048 px web version (ideal for
Instagram/LinkedIn) + a light thumbnail, so ~1,500 photos fit in Supabase's free 1 GB.
"""
import io
import re
import uuid
from pathlib import Path

import requests
from PIL import Image, ImageOps
from sqlalchemy import Boolean, Column, Integer, String, Table, Text, delete, insert, select, update

import db
from config import get_secret

photos = Table(
    "photos", db.md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_key", String(120)),     # stable key: Monograph job number (e.g. "2417") or project name
    Column("project_name", String(200)),
    Column("path_web", Text),
    Column("path_thumb", Text),
    Column("filename", String(250)),
    Column("width", Integer),
    Column("height", Integer),
    Column("tags", Text, default=""),
    Column("photographer", String(120)),
    Column("shot_date", String(10)),
    Column("favorite", Boolean, default=False),
    Column("used", Boolean, default=False),
    Column("uploaded_by", String(60)),
    Column("uploaded_at", String(30)),
)
db.md.create_all(db.engine)

TAGS = ["Exterior", "Interior", "Pool", "Drone", "Detail", "Twilight", "Kitchen", "Bath", "Living",
        "Facade", "Landscape", "Under construction", "Before", "After", "Team"]
TAGS_ES = {"Exterior": "Exterior", "Interior": "Interior", "Pool": "Piscina", "Drone": "Drone", "Detail": "Detalle",
           "Twilight": "Atardecer", "Kitchen": "Cocina", "Bath": "Baño", "Living": "Living", "Facade": "Fachada",
           "Landscape": "Paisajismo", "Under construction": "En obra", "Before": "Antes", "After": "Después",
           "Team": "Equipo"}
NO_PROJECT = "__none__"
BUCKET = "photos"
WEB_SIZE, THUMB_SIZE = 2048, 520
LOCAL_DIR = Path(__file__).with_name("photo_store")


def project_key(name):
    """Monograph names start with the job number ('2417 · NE 26th Ter') → '2417'. Stable week to week."""
    name = str(name or "").strip()
    m = re.match(r"^(\d{3,6})\b", name)
    return m.group(1) if m else name.lower()


# ---------------- storage backend ----------------
def _sb():
    url, key = get_secret("SUPABASE_URL"), get_secret("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    key = str(key).strip()
    headers = {"apikey": key}
    if not key.startswith("sb_"):          # legacy service_role JWT also goes in Authorization
        headers["Authorization"] = f"Bearer {key}"
    return str(url).strip().rstrip("/") + "/storage/v1", headers


def backend():
    return "supabase" if _sb() else "local"


def ensure_bucket():
    sb = _sb()
    if not sb or db.get_meta("photos_bucket_ok") == "1":
        return
    base, h = sb
    r = requests.post(f"{base}/bucket", headers=h, json={"id": BUCKET, "name": BUCKET, "public": False}, timeout=30)
    if r.ok or "already exists" in r.text.lower() or r.status_code == 409:
        db.set_meta("photos_bucket_ok", "1")
    else:
        raise RuntimeError(f"Supabase Storage: {r.status_code} {r.text[:200]}")


def _put(path, data):
    sb = _sb()
    if not sb:
        f = LOCAL_DIR / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        return
    base, h = sb
    r = requests.post(f"{base}/object/{BUCKET}/{path}", headers={**h, "Content-Type": "image/jpeg", "x-upsert": "true"},
                      data=data, timeout=120)
    if not r.ok:
        raise RuntimeError(f"Upload failed: {r.status_code} {r.text[:200]}")


def _remove(paths):
    paths = [p for p in paths if p]
    if not paths:
        return
    sb = _sb()
    if not sb:
        for p in paths:
            (LOCAL_DIR / p).unlink(missing_ok=True)
        return
    base, h = sb
    requests.delete(f"{base}/object/{BUCKET}", headers=h, json={"prefixes": paths}, timeout=60)


def urls(paths, expires=3600):
    """path → viewable URL (signed for Supabase, data URI for local testing)."""
    paths = [p for p in paths if p]
    if not paths:
        return {}
    sb = _sb()
    if not sb:
        import base64
        out = {}
        for p in paths:
            f = LOCAL_DIR / p
            if f.exists():
                out[p] = "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()
        return out
    base, h = sb
    out = {}
    for i in range(0, len(paths), 100):
        r = requests.post(f"{base}/object/sign/{BUCKET}", headers=h,
                          json={"expiresIn": expires, "paths": paths[i:i + 100]}, timeout=30)
        if r.ok:
            for item in r.json():
                if item.get("signedURL"):
                    out[item["path"]] = base + item["signedURL"]
    return out


def read_bytes(path):
    sb = _sb()
    if not sb:
        return (LOCAL_DIR / path).read_bytes()
    url = urls([path]).get(path)
    return requests.get(url, timeout=60).content if url else b""


# ---------------- processing ----------------
def _jpeg(img, size, quality):
    im = img.copy()
    im.thumbnail((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue(), im.size


def add_photo(file_bytes, filename, project_name, tags, photographer, shot_date, user):
    ensure_bucket()
    img = Image.open(io.BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    web, (w, h) = _jpeg(img, WEB_SIZE, 85)
    thumb, _ = _jpeg(img, THUMB_SIZE, 72)
    key = project_key(project_name) if project_name else NO_PROJECT
    folder = re.sub(r"[^a-z0-9_-]+", "-", key.lower()).strip("-") or "none"
    uid = uuid.uuid4().hex[:12]
    p_web, p_thumb = f"{folder}/{uid}.jpg", f"{folder}/{uid}_t.jpg"
    _put(p_web, web)
    _put(p_thumb, thumb)
    with db.engine.begin() as c:
        c.execute(insert(photos).values(
            project_key=key, project_name=project_name or "", path_web=p_web, path_thumb=p_thumb,
            filename=filename[:250], width=w, height=h, tags=",".join(tags or []), photographer=photographer or "",
            shot_date=shot_date or "", favorite=False, used=False, uploaded_by=user, uploaded_at=db.now()))
    return len(web) + len(thumb)


def all_photos():
    return db.df(photos)


def set_fields(ids, **values):
    with db.engine.begin() as c:
        c.execute(update(photos).where(photos.c.id.in_([int(i) for i in ids])).values(**values))


def move_to_project(ids, project_name):
    key = project_key(project_name) if project_name else NO_PROJECT
    set_fields(ids, project_key=key, project_name=project_name or "")


def delete_photos(ids):
    with db.engine.connect() as c:
        rows = c.execute(select(photos.c.path_web, photos.c.path_thumb).where(photos.c.id.in_([int(i) for i in ids]))).fetchall()
    _remove([p for r in rows for p in r])
    with db.engine.begin() as c:
        c.execute(delete(photos).where(photos.c.id.in_([int(i) for i in ids])))


def counts_by_project():
    df = all_photos()
    return df.groupby("project_key").size().to_dict() if not df.empty else {}
