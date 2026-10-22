"""Base de datos compartida. Local: SQLite. En la nube: Postgres (Supabase) vía DATABASE_URL."""
import datetime as dt

import pandas as pd
from sqlalchemy import (Column, Integer, MetaData, String, Table, Text, and_,
                        create_engine, delete, insert, select, update)

from config import get_secret

_url = get_secret("DATABASE_URL") or "sqlite:///xb_content.db"
_url = str(_url).strip()
# Use the psycopg (v3) driver explicitly — works on every Python version Streamlit Cloud uses.
for prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
    if _url.startswith(prefix):
        _url = "postgresql+psycopg://" + _url[len(prefix):]
        break

_connect_args = {"connect_timeout": 10} if _url.startswith("postgresql") else {}
engine = create_engine(_url, pool_pre_ping=True, pool_recycle=300, connect_args=_connect_args)
md = MetaData()

posts = Table(
    "posts", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("publish_date", String(10)),   # YYYY-MM-DD
    Column("publish_time", String(5)),    # HH:MM
    Column("account", String(30)),
    Column("format", String(40)),
    Column("pillar", String(80)),
    Column("title", String(250)),
    Column("body", Text),                 # copy
    Column("media_url", Text),            # link a Drive/Dropbox con el material
    Column("permalink", Text),            # link al post publicado (para cruzar métricas)
    Column("status", String(30)),
    Column("owner", String(60)),
    Column("notes", Text),
    Column("created_by", String(60)),
    Column("updated_at", String(30)),
)

ideas = Table(
    "ideas", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", String(250)),
    Column("description", Text),
    Column("pillar", String(80)),
    Column("format", String(40)),
    Column("account", String(30)),
    Column("inspo", String(250)),
    Column("source", String(20)),         # Equipo / IA
    Column("votes", Integer, default=0),
    Column("voters", Text, default=""),
    Column("status", String(20)),         # Nueva / Usada / Archivada
    Column("created_by", String(60)),
    Column("created_at", String(30)),
)

metrics = Table(
    "metrics", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account", String(30)),
    Column("external_id", String(200)),
    Column("permalink", Text),
    Column("caption", Text),
    Column("published_at", String(30)),
    Column("media_type", String(40)),
    Column("likes", Integer),
    Column("comments", Integer),
    Column("views", Integer),
    Column("reach", Integer),
    Column("shares", Integer),
    Column("saves", Integer),
    Column("source", String(20)),         # api / manual / csv
    Column("fetched_at", String(30)),
)

meta = Table("meta", md, Column("key", String(80), primary_key=True), Column("value", Text))

try:
    md.create_all(engine)
    DB_ERROR = ""
except Exception as _e:  # noqa: BLE001 — shown nicely by app.py instead of an endless spinner
    DB_ERROR = str(_e)[:300]


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def df(table):
    with engine.connect() as c:
        return pd.read_sql(select(table), c)


def insert_row(table, data):
    with engine.begin() as c:
        r = c.execute(insert(table).values(**data))
        return r.inserted_primary_key[0]


def update_row(table, row_id, data):
    with engine.begin() as c:
        c.execute(update(table).where(table.c.id == int(row_id)).values(**data))


def delete_row(table, row_id):
    with engine.begin() as c:
        c.execute(delete(table).where(table.c.id == int(row_id)))


def get_meta(key, default=None):
    with engine.connect() as c:
        r = c.execute(select(meta.c.value).where(meta.c.key == key)).fetchone()
        return r[0] if r else default


def set_meta(key, value):
    with engine.begin() as c:
        c.execute(delete(meta).where(meta.c.key == key))
        c.execute(insert(meta).values(key=key, value=str(value)))


def upsert_metric(row):
    row = {**row, "fetched_at": now()}
    with engine.begin() as c:
        c.execute(delete(metrics).where(and_(metrics.c.account == row["account"],
                                             metrics.c.external_id == row["external_id"])))
        c.execute(insert(metrics).values(**row))
