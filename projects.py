"""XB projects (imported weekly from Monograph) — used by the AI to suggest content per project phase."""
import io
import json

import pandas as pd
from sqlalchemy import Column, Integer, String, Table, Text, delete, insert

import db

projects = Table(
    "projects", db.md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(200)),
    Column("location", String(200)),
    Column("phase", String(40)),
    Column("type", String(120)),
    Column("notes", Text),
    Column("updated_at", String(30)),
)
try:
    db.md.create_all(db.engine)
except Exception:  # noqa: BLE001
    pass

PHASES = ["Design", "Permits", "Under construction", "Finished", "On hold", "Other"]
PHASES_ES = {"Design": "Diseño", "Permits": "Permisos", "Under construction": "En obra",
             "Finished": "Terminado", "On hold": "En pausa", "Other": "Otro"}
PHASE_ICON = {"Design": "✏️", "Permits": "📄", "Under construction": "🏗️", "Finished": "✅", "On hold": "⏸️", "Other": "•"}

_KEYWORDS = [
    ("Finished", ["complete", "completed", "finished", "closed", "close out", "closeout", "done", "terminad", "finaliz", "entregad"]),
    ("Under construction", ["construction", "ca ", "contract admin", "build", "obra", "construcc"]),
    ("Permits", ["permit", "permiso", "bid", "licit", "approval", "aprobaci"]),
    ("Design", ["design", "schematic", "sd", "dd", "cd", "concept", "diseñ", "anteproyecto", "proyecto ejecutivo", "drawings"]),
    ("On hold", ["hold", "paused", "pausa", "suspend"]),
]


def normalize_phase(value):
    v = f" {str(value or '').strip().lower()} "
    for phase in PHASES:
        if v.strip() == phase.lower():
            return phase
    for phase, words in _KEYWORDS:
        if any(w in v for w in words):
            return phase
    return "Other"


def current():
    return db.df(projects)


def last_update():
    return db.get_meta("projects_updated")


def read_table(file_bytes, filename):
    """CSV / Excel → plain text table for the AI to interpret (columns vary by export)."""
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        raw = file_bytes.decode("utf-8", errors="ignore")
        try:
            df = pd.read_csv(io.StringIO(raw), sep=None, engine="python")
        except Exception:  # noqa: BLE001
            return raw[:30000]
    return df.head(300).to_csv(index=False)[:30000]


def diff(new_rows):
    """Compares with what's stored. Returns (added, changed, removed) lists of names/(name, old, new)."""
    old = current()
    old_map = {str(r["name"]).strip().lower(): r for _, r in old.iterrows()} if not old.empty else {}
    new_map = {str(r["name"]).strip().lower(): r for r in new_rows if str(r.get("name") or "").strip()}
    added = [new_map[k]["name"] for k in new_map if k not in old_map]
    removed = [old_map[k]["name"] for k in old_map if k not in new_map]
    changed = [(new_map[k]["name"], old_map[k]["phase"], new_map[k]["phase"])
               for k in new_map if k in old_map and old_map[k]["phase"] != new_map[k]["phase"]]
    return added, changed, removed


def replace_all(rows, user):
    with db.engine.begin() as c:
        c.execute(delete(projects))
        for r in rows:
            if not str(r.get("name") or "").strip():
                continue
            c.execute(insert(projects).values(
                name=str(r.get("name"))[:200], location=str(r.get("location") or "")[:200],
                phase=normalize_phase(r.get("phase")), type=str(r.get("type") or "")[:120],
                notes=str(r.get("notes") or "")[:1000], updated_at=db.now()))
    db.set_meta("projects_updated", db.now())
    db.set_meta("projects_updated_by", user)


def context_for_ai(limit=40):
    """Short text block describing XB's real projects, for every AI prompt."""
    df = current()
    if df.empty:
        return ""
    lines = [f"- {r['name']} ({r['location'] or 'South Florida'}) — phase: {r['phase']}"
             + (f", {r['type']}" if r["type"] else "") + (f". {r['notes'][:140]}" if r["notes"] else "")
             for _, r in df.head(limit).iterrows()]
    return "XB's current real projects (use them; match the content to each phase):\n" + "\n".join(lines)


def to_json(rows):
    return json.dumps(rows, ensure_ascii=False)
