"""XB Architecture · Content Studio
Shared content calendar + idea bank + AI copywriting + automatic reports.
English by default, Spanish available with the 🌐 switch (remembered per user).
Run with:  streamlit run app.py
"""
import datetime as dt
import hmac
import io

import altair as alt
import pandas as pd
import streamlit as st

import ai
import db
import ig_oauth
import integrations
from config import (ACCOUNTS, BRAND, DEFAULT_VOICES, FORMATS, IDEA_STATUSES, INSPO,
                    LANGUAGES, LOGO_SVG, PILLARS, STATUSES, get_secret)
from i18n import LANG_OPTIONS, date_fmt, days, is_es, opt, short_date, t

st.set_page_config(page_title="XB · Content Studio", page_icon="◼", layout="wide")

ACC_KEYS = list(ACCOUNTS)
SANS = "'Jost', 'Helvetica Neue', Arial, sans-serif"


# ======================================================================
# Style / branding
# ======================================================================
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500&family=Inter:wght@300;400;500;600&display=swap');
    html, body, [class*="css"], .stMarkdown, p, label, input, textarea {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: {BRAND['bg']}; }}
    h1, h2, h3, h4 {{ font-family: {SANS} !important; font-weight: 400 !important;
                      letter-spacing: .04em; color: {BRAND['black']}; }}
    section[data-testid="stSidebar"] {{ background: {BRAND['black']}; }}
    section[data-testid="stSidebar"] * {{ color: #EDEDED !important; }}
    section[data-testid="stSidebar"] .stRadio[aria-label] label p, section[data-testid="stSidebar"] .stRadio label p {{ font-family: {SANS}; letter-spacing: .12em;
                      text-transform: uppercase; font-size: .82rem; }}
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
        border-radius: 0; border: 1px solid {BRAND['black']}; background: {BRAND['white']};
        color: {BRAND['black']}; font-family: {SANS}; letter-spacing: .08em; }}
    .stButton > button:hover {{ background: {BRAND['black']}; color: #fff; border-color: {BRAND['black']}; }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {{
        background: {BRAND['black']}; color: #fff; }}
    section[data-testid="stSidebar"] .stButton > button {{ background: transparent; border-color: #555; }}
    section[data-testid="stSidebar"] .stButton > button:hover {{ background: #fff; color: #111 !important; }}
    div[data-testid="stMetric"] {{ background: #fff; border: 1px solid {BRAND['line']}; padding: 14px 18px; }}
    div[data-testid="stMetricLabel"] p {{ text-transform: uppercase; letter-spacing: .12em; font-size: .72rem;
                      color: {BRAND['grey']}; }}
    .xb-eyebrow {{ font-family: {SANS}; letter-spacing: .3em; text-transform: uppercase; font-size: .72rem;
                   color: {BRAND['grey']}; margin-bottom: -6px; }}
    .xb-title {{ font-family: {SANS}; font-weight: 300; font-size: 2.2rem; letter-spacing: .06em;
                 margin: 0 0 4px 0; color: {BRAND['black']}; }}
    .xb-rule {{ height: 1px; background: {BRAND['black']}; width: 56px; margin: 6px 0 22px 0; }}
    .xb-day {{ font-family: {SANS}; letter-spacing: .14em; text-transform: uppercase; font-size: .75rem;
               color: {BRAND['grey']}; border-bottom: 1px solid {BRAND['line']}; padding-bottom: 4px;
               margin-bottom: 6px; }}
    .xb-day b {{ color: {BRAND['black']}; font-size: 1.15rem; font-weight: 400; letter-spacing: .02em; }}
    .xb-today {{ border-bottom: 2px solid {BRAND['black']}; }}
    .xb-card {{ background: #fff; border: 1px solid {BRAND['line']}; border-left: 4px solid var(--c);
                padding: 7px 9px; margin: 4px 0 2px 0; font-size: .78rem; line-height: 1.3; }}
    .xb-card .t {{ font-weight: 600; color: {BRAND['black']}; }}
    .xb-card .m {{ color: {BRAND['grey']}; font-size: .7rem; letter-spacing: .04em; }}
    .xb-chip {{ display: inline-block; border: 1px solid {BRAND['line']}; padding: 0 6px; font-size: .64rem;
                letter-spacing: .08em; text-transform: uppercase; margin-top: 3px; background: {BRAND['light']}; }}
    .xb-legend span {{ display: inline-block; margin-right: 16px; font-size: .78rem; }}
    .xb-legend i {{ display: inline-block; width: 10px; height: 10px; margin-right: 6px; }}
    .xb-idea {{ background: #fff; border: 1px solid {BRAND['line']}; padding: 14px 16px; margin-bottom: 4px; }}
    .xb-idea h4 {{ margin: 0 0 4px 0; font-size: 1.02rem; }}
    .xb-muted {{ color: {BRAND['grey']}; font-size: .8rem; }}
    </style>""", unsafe_allow_html=True)


def header(eyebrow, title, sub=None):
    st.markdown(f"<div class='xb-eyebrow'>{eyebrow}</div><div class='xb-title'>{title}</div>"
                f"<div class='xb-rule'></div>", unsafe_allow_html=True)
    if sub:
        st.caption(sub)


def acc_label(k):
    return ACCOUNTS.get(k, {}).get("label", k)


def legend():
    st.markdown("<div class='xb-legend'>" + "".join(
        f"<span><i style='background:{a['color']}'></i>{a['label']}</span>" for a in ACCOUNTS.values()
    ) + "</div>", unsafe_allow_html=True)


def sel(label, options, value=None, key=None, **kw):
    """Selectbox over stored (English) values with translated labels."""
    idx = options.index(value) if value in options else 0
    return st.selectbox(label, options, index=idx, format_func=opt, key=key, **kw)


# ======================================================================
# Language switch (remembered per user)
# ======================================================================
def _on_lang_change(widget_key):
    code = st.session_state[widget_key]
    st.session_state["lang"] = code
    if st.session_state.get("user"):
        db.set_meta(f"lang_{st.session_state['user']}", code)


def language_switch():
    current = st.session_state.get("lang", "en")
    wkey = f"_lang_widget_{current}"   # keyed by language so the switch always mirrors the active language
    st.radio("🌐 Language / Idioma", list(LANG_OPTIONS), format_func=LANG_OPTIONS.get, horizontal=True,
             index=list(LANG_OPTIONS).index(current), key=wkey, on_change=_on_lang_change, args=(wkey,))


def _start_session(user):
    st.session_state["user"] = user
    saved = db.get_meta(f"lang_{user}")
    if saved:
        st.session_state["lang"] = saved
    else:
        db.set_meta(f"lang_{user}", st.session_state.get("lang", "en"))


# ======================================================================
# Login (users defined in secrets)
# ======================================================================
def login():
    if st.session_state.get("user"):
        return st.session_state["user"]
    users = {}
    try:
        users = {str(k).strip().lower(): v for k, v in dict(st.secrets.get("users", {})).items()}
    except Exception:
        pass
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.markdown(f"<div style='text-align:center;margin-top:7vh'>{LOGO_SVG.format(w=170)}</div>",
                    unsafe_allow_html=True)
        st.markdown("<div class='xb-eyebrow' style='text-align:center;margin-top:18px'>Content Studio</div>",
                    unsafe_allow_html=True)
        language_switch()
        with st.form("login"):
            if users:
                u = st.text_input(t("Username", "Usuario"))
                p = st.text_input(t("Password", "Contraseña"), type="password")
            else:
                st.info(t("Test mode: no users in secrets. Type a name to sign in.",
                          "Modo prueba: no hay usuarios en secrets. Escribí un nombre para entrar."))
                u = st.text_input(t("Your name", "Tu nombre"), value="Faustina")
                p = ""
            if st.form_submit_button(t("Sign in", "Entrar"), width="stretch", type="primary"):
                if not users and u.strip():
                    _start_session(u.strip())
                    st.rerun()
                elif u.strip().lower() in users and hmac.compare_digest(str(users[u.strip().lower()]), p.strip()):
                    _start_session(u.strip().lower().capitalize())
                    st.rerun()
                else:
                    st.error(t("Wrong username or password.", "Usuario o contraseña incorrectos."))
    st.stop()


# ======================================================================
# Data helpers
# ======================================================================
def monday(d):
    return d - dt.timedelta(days=d.weekday())


def load_posts():
    p = db.df(db.posts)
    if not p.empty:
        p["publish_date"] = pd.to_datetime(p["publish_date"], errors="coerce").dt.date
    return p


def load_metrics():
    m = db.df(db.metrics)
    if not m.empty:
        m["published_at"] = pd.to_datetime(m["published_at"], errors="coerce")
        for c in ["likes", "comments", "views", "reach", "shares", "saves"]:
            m[c] = pd.to_numeric(m[c], errors="coerce").fillna(0).astype(int)
        m["interactions"] = m["likes"] + m["comments"] + m["shares"] + m["saves"]
        m["engagement_%"] = (m["interactions"] / m["views"].where(m["views"] > 0) * 100).round(2)
        m["account_name"] = m["account"].map(acc_label)
    return m


def clear_keys(prefix):
    for k in [k for k in st.session_state if str(k).startswith(prefix)]:
        del st.session_state[k]


# ======================================================================
# Dialogs
# ======================================================================
def _ai_fill(key, account, title, fmt, pillar, lang, extra):
    try:
        st.session_state[key] = ai.generate_copy(account, title, fmt, pillar, lang, extra=extra)
        st.session_state.pop("ai_err", None)
    except Exception as e:  # noqa: BLE001
        st.session_state["ai_err"] = str(e)


@st.dialog("Post", width="large")
def post_dialog(post=None, default_date=None):
    user = st.session_state["user"]
    pid = int(post["id"]) if post is not None else "new"
    pre = f"pd_{pid}_"
    src = post if post is not None else {}

    def g(field, default=""):
        v = src.get(field, default) if isinstance(src, dict) else src[field]
        return default if v is None or (isinstance(v, float) and pd.isna(v)) else v

    c1, c2, c3 = st.columns(3)
    d0 = g("publish_date", default_date or dt.date.today())
    if isinstance(d0, str):
        d0 = dt.date.fromisoformat(d0)
    date = c1.date_input(t("Date", "Fecha"), value=d0, key=pre + "date", format=date_fmt())
    try:
        hh, mm = str(g("publish_time", "11:00") or "11:00").split(":")[:2]
        t0 = dt.time(int(hh), int(mm[:2]))
    except Exception:
        t0 = dt.time(11, 0)
    time = c2.time_input(t("Time (ET)", "Hora (ET)"), value=t0, key=pre + "time")
    acc0 = g("account", ACC_KEYS[0])
    acc = c3.selectbox(t("Account", "Cuenta"), ACC_KEYS, index=ACC_KEYS.index(acc0) if acc0 in ACC_KEYS else 0,
                       format_func=acc_label, key=pre + "acc")
    c4, c5, c6 = st.columns(3)
    with c4:
        fmt = sel(t("Format", "Formato"), FORMATS, g("format"), key=pre + "fmt")
    with c5:
        pil = sel(t("Pillar", "Pilar"), PILLARS, g("pillar"), key=pre + "pil")
    with c6:
        stt = sel(t("Status", "Estado"), STATUSES, g("status", "Draft"), key=pre + "st")
    title = st.text_input(t("Title / topic", "Título / tema"), value=g("title"), key=pre + "title")

    body_key = pre + "body"
    if body_key not in st.session_state:
        st.session_state[body_key] = g("body")
    ca, cb = st.columns([3, 1])
    with cb:
        lang = sel(t("Caption language", "Idioma del copy"), LANGUAGES, key=pre + "lang")
    extra = ca.text_input(t("Notes for the AI (optional)", "Indicaciones para la IA (opcional)"), key=pre + "extra",
                          placeholder=t("e.g. focus on the infinity pool and the canal view",
                                        "ej.: enfocá en la piscina infinity y la vista al canal"))
    st.button(t("✨ Write caption with AI", "✨ Escribir copy con IA"), key=pre + "ai", on_click=_ai_fill,
              args=(body_key, acc, title, fmt, pil, lang, extra), disabled=not title)
    if st.session_state.get("ai_err"):
        st.error(st.session_state["ai_err"])
    st.text_area(t("Caption", "Copy"), key=body_key, height=220)

    c7, c8 = st.columns(2)
    media = c7.text_input(t("Link to assets (Drive / Dropbox)", "Link al material (Drive / Dropbox)"),
                          value=g("media_url"), key=pre + "media")
    owner = c8.text_input(t("Owner", "Responsable"), value=g("owner", user), key=pre + "owner")
    perma = st.text_input(t("Link to the published post (to match with reports)",
                            "Link del post publicado (para cruzar con reportes)"), value=g("permalink"), key=pre + "perma")
    notes = st.text_area(t("Internal notes", "Notas internas"), value=g("notes"), key=pre + "notes", height=70)

    data = dict(publish_date=date.isoformat(), publish_time=time.strftime("%H:%M"), account=acc, format=fmt,
                pillar=pil, status=stt, title=title, body=st.session_state[body_key], media_url=media,
                owner=owner, permalink=perma, notes=notes, updated_at=db.now())
    b1, b2, b3 = st.columns([1, 1, 2])
    if b1.button(t("Save", "Guardar"), type="primary", key=pre + "save", width="stretch"):
        if post is None:
            db.insert_row(db.posts, {**data, "created_by": user})
        else:
            db.update_row(db.posts, pid, data)
        clear_keys(pre)
        st.rerun()
    if post is not None and b2.button(t("Delete", "Eliminar"), key=pre + "del", width="stretch"):
        db.delete_row(db.posts, pid)
        clear_keys(pre)
        st.rerun()
    if post is not None and b3.button(t("Duplicate for another account", "Duplicar para otra cuenta"),
                                      key=pre + "dup", width="stretch"):
        db.insert_row(db.posts, {**data, "status": "Draft", "created_by": user, "permalink": ""})
        clear_keys(pre)
        st.rerun()
    if post is not None:
        st.caption(t(f"Created by {g('created_by')} · last edited {g('updated_at')}",
                     f"Creado por {g('created_by')} · última edición {g('updated_at')}"))


@st.dialog("✨ AI planner", width="large")
def plan_dialog(start):
    st.caption(t("The AI drafts a plan for the accounts you choose. Review it, edit it and add it as Drafts.",
                 "La IA arma una propuesta para las cuentas que elijas. La revisás, editás y la sumás como Borrador."))
    c1, c2, c3 = st.columns(3)
    s = c1.date_input(t("From", "Desde"), value=start, key="pl_start", format=date_fmt())
    weeks = c2.radio(t("Length", "Duración"), [1, 2],
                     format_func=lambda w: t(f"{w} week" + ("s" if w > 1 else ""), f"{w} semana" + ("s" if w > 1 else "")),
                     horizontal=True, key="pl_weeks")
    with c3:
        lang = sel(t("Caption language", "Idioma del copy"), LANGUAGES, key="pl_lang")
    st.markdown(t("**Posts per week**", "**Posts por semana**"))
    cols = st.columns(4)
    defaults = {"ig_xb": 3, "li_xb": 2, "li_john": 1, "li_ximena": 1}
    per = {k: cols[i].number_input(ACCOUNTS[k]["short"], 0, 7, defaults[k], key=f"pl_n_{k}")
           for i, k in enumerate(ACC_KEYS)}
    notes = st.text_area(t("Context for these weeks", "Contexto de estas semanas"), key="pl_notes",
                         placeholder=t("e.g. final photos of Sea Island are in, Surfside is at structure stage, "
                                       "we want to reach developers…",
                                       "ej.: terminamos fotos de Sea Island, obra de Surfside en etapa de estructura, "
                                       "queremos captar desarrolladores…"))
    if st.button(t("✨ Generate plan", "✨ Generar propuesta"), type="primary"):
        with st.spinner(t("Building the calendar…", "Armando el calendario…")):
            try:
                taken = load_posts()
                titles = taken["title"].dropna().tolist() if not taken.empty else []
                plan = ai.plan_weeks(s.isoformat(), 7 * weeks, per, lang, notes, titles)
                st.session_state["plan"] = pd.DataFrame(plan)
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
    if "plan" in st.session_state:
        edited = st.data_editor(
            st.session_state["plan"], width="stretch", num_rows="dynamic", key="pl_editor",
            column_config={"account": st.column_config.SelectboxColumn(t("account", "cuenta"), options=ACC_KEYS),
                           "format": st.column_config.SelectboxColumn(t("format", "formato"), options=FORMATS),
                           "pillar": st.column_config.SelectboxColumn(t("pillar", "pilar"), options=PILLARS),
                           "date": t("date", "fecha"), "time": t("time", "hora"), "title": t("title", "título"),
                           "copy": st.column_config.TextColumn(t("caption", "copy"), width="large")})
        if st.button(t(f"Add {len(edited)} posts to the calendar", f"Agregar {len(edited)} posts al calendario"),
                     type="primary"):
            for _, r in edited.iterrows():
                db.insert_row(db.posts, dict(
                    publish_date=str(r.get("date")), publish_time=str(r.get("time") or "11:00")[:5],
                    account=r.get("account"), format=r.get("format"), pillar=r.get("pillar"),
                    title=r.get("title"), body=r.get("copy"), status="Draft", owner="",
                    created_by=f"AI · {st.session_state['user']}", updated_at=db.now()))
            del st.session_state["plan"]
            st.rerun()


@st.dialog("→ Calendar")
def idea_to_post_dialog(idea):
    d = st.date_input(t("Date", "Fecha"), value=dt.date.today() + dt.timedelta(days=1), format=date_fmt())
    tm = st.time_input(t("Time (ET)", "Hora (ET)"), value=dt.time(11, 0))
    acc0 = idea["account"] if idea["account"] in ACC_KEYS else ACC_KEYS[0]
    acc = st.selectbox(t("Account", "Cuenta"), ACC_KEYS, index=ACC_KEYS.index(acc0), format_func=acc_label)
    if st.button(t("Create draft", "Crear borrador"), type="primary"):
        db.insert_row(db.posts, dict(
            publish_date=d.isoformat(), publish_time=tm.strftime("%H:%M"), account=acc,
            format=idea["format"] if idea["format"] in FORMATS else FORMATS[0],
            pillar=idea["pillar"] if idea["pillar"] in PILLARS else PILLARS[0], title=idea["title"],
            body="", notes=f"{idea['description']}\n\nInspo: {idea['inspo'] or '—'}", status="Draft",
            owner=st.session_state["user"], created_by=st.session_state["user"], updated_at=db.now()))
        db.update_row(db.ideas, idea["id"], {"status": "Used"})
        st.rerun()


# ======================================================================
# Pages
# ======================================================================
def page_home():
    user = st.session_state["user"]
    header("Content Studio", t(f"Hi, {user}", f"Hola, {user}"),
           t("XB Architecture content at a glance", "Resumen del contenido de XB Architecture"))
    posts, m, ideas = load_posts(), load_metrics(), db.df(db.ideas)
    today = dt.date.today()
    wk = monday(today)
    week = posts[(posts["publish_date"] >= wk) & (posts["publish_date"] < wk + dt.timedelta(days=7))] if not posts.empty else posts
    pend = posts[posts["status"].isin(["Draft", "In review"])] if not posts.empty else posts
    last30 = m[m["published_at"] >= pd.Timestamp(today - dt.timedelta(days=30))] if not m.empty else m

    c = st.columns(4)
    c[0].metric(t("Posts this week", "Posts esta semana"), len(week))
    c[1].metric(t("Pending review", "Pendientes de revisión"), len(pend))
    c[2].metric(t("Ideas in the bank", "Ideas en el banco"), int((ideas["status"] == "New").sum()) if not ideas.empty else 0)
    c[3].metric(t("Views · 30 days", "Visualizaciones · 30 días"), f"{int(last30['views'].sum()):,}" if not last30.empty else "—")

    left, right = st.columns([1.6, 1])
    with left:
        st.subheader(t("Next 7 days", "Próximos 7 días"))
        nxt = posts[(posts["publish_date"] >= today) & (posts["publish_date"] <= today + dt.timedelta(days=7))] \
            if not posts.empty else posts
        if nxt.empty:
            st.caption(t("Nothing scheduled. Go to Calendar or ask the AI to plan the week.",
                         "No hay nada programado. Andá a Calendario o pedile a la IA que planifique la semana."))
        for _, p in nxt.sort_values(["publish_date", "publish_time"]).iterrows():
            a = ACCOUNTS.get(p["account"], {})
            st.markdown(f"<div class='xb-card' style='--c:{a.get('color', '#111')}'>"
                        f"<span class='m'>{days()[p['publish_date'].weekday()]} {short_date(p['publish_date'])} · "
                        f"{p['publish_time']} · {a.get('short', '')}</span><br><span class='t'>{p['title']}</span>"
                        f"<br><span class='xb-chip'>{opt(p['status'])}</span> <span class='xb-chip'>{opt(p['format'])}</span>"
                        f"</div>", unsafe_allow_html=True)
    with right:
        st.subheader("Pipeline")
        counts = posts["status"].value_counts().reindex(STATUSES, fill_value=0) if not posts.empty \
            else pd.Series(0, index=STATUSES)
        for s_, n in counts.items():
            st.markdown(f"<div style='display:flex;justify-content:space-between;border-bottom:1px solid "
                        f"{BRAND['line']};padding:6px 0'><span>{opt(s_)}</span><b>{n}</b></div>", unsafe_allow_html=True)
        st.subheader(t("Top post · 30 days", "Mejor post · 30 días"))
        if last30.empty:
            st.caption(t("No metrics yet. Link the accounts in Accounts.",
                         "Todavía no hay métricas. Vinculá las cuentas en Cuentas."))
        else:
            top = last30.sort_values("interactions", ascending=False).iloc[0]
            st.markdown(f"**{top['account_name']}** · {short_date(top['published_at'])}")
            st.caption((top["caption"] or "")[:180])
            st.markdown(f"❤ {top['likes']} · 💬 {top['comments']} · 👁 {top['views']}  ·  "
                        f"[{t('view post', 'ver post')}]({top['permalink']})")


def page_calendar():
    header(t("Planning", "Planificación"), t("Calendar", "Calendario"),
           t("Everyone can create, edit and move posts. Changes show up instantly for the whole team.",
             "Todos pueden crear, editar y mover posts. Los cambios se ven al instante para el equipo."))
    c1, c2, c3, c4, c5 = st.columns([1.1, 1, 2.4, 1, 1.2])
    start = monday(c1.date_input(t("Week of", "Semana del"), value=dt.date.today(), format=date_fmt()))
    weeks = c2.radio(t("View", "Vista"), [1, 2], format_func=lambda w: t(f"{w} wk", f"{w} sem."), horizontal=True)
    accs = c3.multiselect(t("Accounts", "Cuentas"), ACC_KEYS, default=ACC_KEYS, format_func=lambda k: ACCOUNTS[k]["short"])
    with c4:
        st.write("")
        if st.button(t("＋ New", "＋ Nuevo"), width="stretch"):
            post_dialog(None, default_date=start)
    with c5:
        st.write("")
        if st.button(t("✨ Plan with AI", "✨ Planificar con IA"), type="primary", width="stretch"):
            plan_dialog(start)
    legend()

    posts = load_posts()
    end = start + dt.timedelta(days=7 * weeks)
    if not posts.empty:
        posts = posts[(posts["publish_date"] >= start) & (posts["publish_date"] < end) & posts["account"].isin(accs)]

    for w in range(weeks):
        cols = st.columns(7, gap="small")
        for i in range(7):
            d = start + dt.timedelta(days=7 * w + i)
            with cols[i]:
                cls = "xb-day xb-today" if d == dt.date.today() else "xb-day"
                st.markdown(f"<div class='{cls}'>{days()[i]} <b>{d:%d}</b></div>", unsafe_allow_html=True)
                day = posts[posts["publish_date"] == d].sort_values("publish_time") if not posts.empty else posts
                for _, p in day.iterrows():
                    a = ACCOUNTS.get(p["account"], {})
                    st.markdown(f"<div class='xb-card' style='--c:{a.get('color', '#111')}'>"
                                f"<span class='m'>{p['publish_time']} · {a.get('short', '')}</span><br>"
                                f"<span class='t'>{(p['title'] or '')[:60]}</span><br>"
                                f"<span class='xb-chip'>{opt(p['status'])}</span></div>", unsafe_allow_html=True)
                    if st.button(t("Open", "Abrir"), key=f"open_{p['id']}", width="stretch"):
                        post_dialog(p)
                if st.button("＋", key=f"add_{d}", width="stretch", help=t("Add a post on this day", "Agregar post este día")):
                    post_dialog(None, default_date=d)
        st.write("")

    with st.expander(t("List view / export", "Vista lista / exportar")):
        if posts.empty:
            st.caption(t("No posts in this period.", "Sin posts en este período."))
        else:
            tb = posts.sort_values(["publish_date", "publish_time"])[
                ["publish_date", "publish_time", "account", "format", "pillar", "status", "title", "body", "owner"]].copy()
            tb["account"] = tb["account"].map(acc_label)
            for col in ["format", "pillar", "status"]:
                tb[col] = tb[col].map(opt)
            tb.columns = [t("date", "fecha"), t("time", "hora"), t("account", "cuenta"), t("format", "formato"),
                          t("pillar", "pilar"), t("status", "estado"), t("title", "título"), t("caption", "copy"),
                          t("owner", "responsable")]
            st.dataframe(tb, width="stretch", hide_index=True)
            st.download_button(t("Download CSV", "Descargar CSV"), tb.to_csv(index=False).encode(),
                               f"calendar_{start}.csv")


def page_ideas():
    user = st.session_state["user"]
    header(t("Creative", "Creatividad"), t("Ideas", "Ideas"),
           t("Shared team idea bank + AI generator inspired by reference studios.",
             "Banco compartido del equipo + generador con IA inspirado en estudios de referencia."))
    t1, t2, t3 = st.tabs([t("Team bank", "Banco del equipo"), t("✨ Generate with AI", "✨ Generar con IA"),
                          t("Inspo · reference accounts", "Inspo · cuentas de referencia")])

    with t1:
        with st.expander(t("＋ Add an idea", "＋ Sumar una idea"), expanded=False):
            with st.form("new_idea", clear_on_submit=True):
                title = st.text_input(t("Idea", "Idea"))
                desc = st.text_area(t("How we'd do it", "Cómo la haríamos"), height=80)
                c1, c2, c3 = st.columns(3)
                with c1:
                    pil = sel(t("Pillar", "Pilar"), PILLARS, key="ni_pil")
                with c2:
                    fmt = sel(t("Format", "Formato"), FORMATS, key="ni_fmt")
                acc = c3.selectbox(t("Suggested account", "Cuenta sugerida"), ACC_KEYS, format_func=acc_label)
                insp = st.text_input(t("Inspo (link or account)", "Inspo (link o cuenta)"))
                if st.form_submit_button(t("Save idea", "Guardar idea"), type="primary") and title:
                    db.insert_row(db.ideas, dict(title=title, description=desc, pillar=pil, format=fmt, account=acc,
                                                 inspo=insp, source="Team", votes=0, voters="", status="New",
                                                 created_by=user, created_at=db.now()))
                    st.rerun()
        ideas = db.df(db.ideas)
        c1, c2, c3 = st.columns(3)
        fstatus = c1.selectbox(t("Status", "Estado"), IDEA_STATUSES + ["All"],
                               format_func=lambda v: t("All", "Todas") if v == "All" else opt(v))
        fpil = c2.multiselect(t("Pillar", "Pilar"), PILLARS, format_func=opt)
        order = c3.selectbox(t("Sort by", "Ordenar por"), ["votes", "recent"],
                             format_func=lambda v: t("Most voted", "Más votadas") if v == "votes" else t("Most recent", "Más recientes"))
        if ideas.empty:
            st.caption(t("No ideas yet. Add the first one or generate some with AI.",
                         "Todavía no hay ideas. Sumá la primera o generá algunas con IA."))
        else:
            if fstatus != "All":
                ideas = ideas[ideas["status"] == fstatus]
            if fpil:
                ideas = ideas[ideas["pillar"].isin(fpil)]
            ideas = ideas.sort_values("votes" if order == "votes" else "created_at", ascending=False)
            for _, i in ideas.iterrows():
                voters = [v for v in (i["voters"] or "").split(",") if v]
                st.markdown(f"<div class='xb-idea'><h4>{i['title']}</h4>"
                            f"<div class='xb-muted'>{opt(i['pillar'])} · {opt(i['format'])} · {acc_label(i['account'])} · "
                            f"{t('by', 'por')} {i['created_by']} ({opt(i['source'])})</div>"
                            f"<p style='margin:8px 0 4px 0'>{i['description'] or ''}</p>"
                            f"<div class='xb-muted'>Inspo: {i['inspo'] or '—'}</div></div>", unsafe_allow_html=True)
                b1, b2, b3, _ = st.columns([1, 1.4, 1, 3])
                voted = user in voters
                if b1.button(f"{'★' if voted else '☆'} {int(i['votes'] or 0)}", key=f"v_{i['id']}"):
                    voters = [v for v in voters if v != user] if voted else voters + [user]
                    db.update_row(db.ideas, i["id"], {"voters": ",".join(voters), "votes": len(voters)})
                    st.rerun()
                if b2.button(t("→ Calendar", "→ Calendario"), key=f"c_{i['id']}"):
                    idea_to_post_dialog(i)
                if b3.button(t("Archive", "Archivar"), key=f"a_{i['id']}"):
                    db.update_row(db.ideas, i["id"], {"status": "Archived"})
                    st.rerun()

    with t2:
        c1, c2 = st.columns(2)
        insp = c1.multiselect(t("Get inspired by", "Inspirarse en"), [i["name"] for i in INSPO],
                              default=["ArchDaily", "Architectural Digest", "STRANG (Miami)"])
        pils = c2.multiselect(t("Pillars", "Pilares"), PILLARS, format_func=opt,
                              default=["Under construction", "Before & After", "Design process"])
        c3, c4, c5 = st.columns([2, 1, 1])
        accs = c3.multiselect(t("For which accounts", "Para qué cuentas"), ACC_KEYS, default=ACC_KEYS,
                              format_func=lambda k: ACCOUNTS[k]["short"])
        n = c4.slider(t("How many", "Cantidad"), 3, 15, 8)
        with c5:
            lang = sel(t("Language", "Idioma"), LANGUAGES, "Spanish" if is_es() else "English", key="id_lang")
        extra = st.text_input(t("Extra context", "Contexto extra"),
                              placeholder=t("e.g. high season is coming, show finished Coral Ridge",
                                            "ej.: se viene la temporada alta, mostrar Coral Ridge terminado"))
        if st.button(t("✨ Generate ideas", "✨ Generar ideas"), type="primary", disabled=not accs):
            with st.spinner(t("Thinking up ideas…", "Pensando ideas…")):
                try:
                    st.session_state["gen_ideas"] = ai.generate_ideas(n, pils, insp, accs, lang, extra)
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))
        gen = st.session_state.get("gen_ideas", [])
        if gen:
            if st.button(t(f"Save all {len(gen)} to the bank", f"Guardar las {len(gen)} en el banco"), key="save_all"):
                for g in gen:
                    _save_ai_idea(g, user)
                st.session_state["gen_ideas"] = []
                st.rerun()
            for k, g in enumerate(gen):
                st.markdown(f"<div class='xb-idea'><h4>{g.get('title')}</h4><div class='xb-muted'>{opt(g.get('pillar'))} · "
                            f"{opt(g.get('format'))} · {acc_label(g.get('account'))}</div><p style='margin:8px 0 4px 0'>"
                            f"{g.get('description')}</p><div class='xb-muted'>Inspo: {g.get('inspo')}</div></div>",
                            unsafe_allow_html=True)
                if st.button(t("Save", "Guardar"), key=f"sg_{k}"):
                    _save_ai_idea(g, user)
                    gen.pop(k)
                    st.rerun()

    with t3:
        st.caption(t("Style references. The AI borrows each one's approach, never their content.",
                     "Referencias de estilo. La IA toma el enfoque de cada una, nunca copia su contenido."))
        cols = st.columns(3)
        for k, i in enumerate(INSPO):
            with cols[k % 3]:
                st.markdown(f"<div class='xb-idea'><h4>{i['name']}</h4><div class='xb-muted'>{t(i['en'], i['es'])}</div></div>",
                            unsafe_allow_html=True)


def _save_ai_idea(g, user):
    db.insert_row(db.ideas, dict(title=g.get("title"), description=g.get("description"), pillar=g.get("pillar"),
                                 format=g.get("format"), account=g.get("account"), inspo=g.get("inspo"),
                                 source="AI", votes=0, voters="", status="New", created_by=user,
                                 created_at=db.now()))


REWRITE_OPTIONS = [
    ("Shorter and more direct", "Más corto y directo"),
    ("More premium / luxury", "Más premium / lujo"),
    ("Add a clear CTA", "Agregar un CTA claro"),
    ("Stronger hook in the first line", "Mejor gancho en la primera línea"),
    ("More storytelling", "Más storytelling"),
    ("Translate keeping the voice", "Traducir manteniendo la voz"),
    ("Improve hashtags", "Mejorar hashtags"),
]


def page_copy():
    user = st.session_state["user"]
    header("AI", t("Caption studio", "Estudio de copys"),
           t("Write, adapt to all 4 accounts, or rewrite captions in each account's voice.",
             "Escribí, adaptá a las 4 cuentas o reescribí copys con la voz de cada cuenta."))
    mode = st.radio(t("Mode", "Modo"), ["one", "all", "rewrite"], horizontal=True, key="cp_mode",
                    format_func=lambda v: {"one": t("One account", "Una cuenta"),
                                           "all": t("Adapt to all 4 accounts", "Adaptar a las 4 cuentas"),
                                           "rewrite": t("Rewrite a caption", "Reescribir un copy")}[v])
    lang = sel(t("Caption language", "Idioma del copy"), LANGUAGES, key="cp_lang")

    if mode == "one":
        c1, c2, c3 = st.columns(3)
        acc = c1.selectbox(t("Account", "Cuenta"), ACC_KEYS, format_func=acc_label, key="cp_acc")
        with c2:
            fmt = sel(t("Format", "Formato"), FORMATS, key="cp_fmt")
        with c3:
            pil = sel(t("Pillar", "Pilar"), PILLARS, key="cp_pil")
        topic = st.text_area("Brief", key="cp_brief",
                             placeholder=t("e.g. Reel walking through the finished Sea Island house: entry, double height, "
                                           "pool facing the canal at sunset",
                                           "ej.: Reel del recorrido final de la casa en Sea Island: entrada, "
                                           "doble altura, piscina hacia el canal al atardecer"))
        tone = st.text_input(t("Tone", "Tono"), placeholder=t("e.g. more emotional / more technical / for developers",
                                                              "ej.: más emocional / más técnico / para desarrolladores"))
        if st.button(t("✨ Write", "✨ Escribir"), type="primary", disabled=not topic):
            with st.spinner(t("Writing…", "Escribiendo…")):
                try:
                    st.session_state["cp_out"] = ai.generate_copy(acc, topic, fmt, pil, lang, tone)
                    st.session_state["cp_meta"] = dict(account=acc, format=fmt, pillar=pil, title=topic[:80])
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))
        if st.session_state.get("cp_out"):
            out = st.text_area(t("Result (editable)", "Resultado (editable)"), value=st.session_state["cp_out"], height=320)
            _save_to_calendar([dict(st.session_state["cp_meta"], body=out)], user, "cp1")

    elif mode == "all":
        topic = st.text_area(t("Shared topic", "Tema común"), key="ad_topic",
                             placeholder=t("e.g. Coral Ridge is finished: 3 levels on the water…",
                                           "ej.: Terminamos Coral Ridge: 3 niveles frente al agua…"))
        pil = sel(t("Pillar", "Pilar"), PILLARS, key="ad_pil")
        extra = st.text_input("Extra", key="ad_extra")
        if st.button(t("✨ Adapt", "✨ Adaptar"), type="primary", disabled=not topic):
            with st.spinner(t("Adapting to each voice…", "Adaptando a cada voz…")):
                try:
                    st.session_state["ad_out"] = ai.adapt_all(topic, pil, lang, extra)
                    st.session_state["ad_meta"] = dict(pillar=pil, title=topic[:80])
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))
        res = st.session_state.get("ad_out")
        if res:
            items = []
            cols = st.columns(2)
            for k, acc in enumerate(ACC_KEYS):
                v = res.get(acc) or {}
                fmt = v.get("format") if v.get("format") in FORMATS else FORMATS[0]
                with cols[k % 2]:
                    st.markdown(f"**{acc_label(acc)}** · {opt(fmt)}")
                    txt = st.text_area(acc_label(acc), value=v.get("copy", ""), height=260, key=f"ad_{acc}",
                                       label_visibility="collapsed")
                items.append(dict(st.session_state["ad_meta"], account=acc, format=fmt, body=txt))
            _save_to_calendar(items, user, "cp4")

    else:
        acc = st.selectbox(t("Account", "Cuenta"), ACC_KEYS, format_func=acc_label, key="rw_acc")
        text = st.text_area(t("Original caption", "Copy original"), height=180, key="rw_text")
        instr = st.selectbox(t("What should we do?", "¿Qué hacemos?"), range(len(REWRITE_OPTIONS)),
                             format_func=lambda i: t(*REWRITE_OPTIONS[i]))
        if st.button(t("✨ Rewrite", "✨ Reescribir"), type="primary", disabled=not text):
            with st.spinner(t("Rewriting…", "Reescribiendo…")):
                try:
                    st.session_state["rw_out"] = ai.rewrite(text, acc, REWRITE_OPTIONS[instr][0], lang)
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))
        if st.session_state.get("rw_out"):
            st.text_area(t("Result", "Resultado"), value=st.session_state["rw_out"], height=260)


def _save_to_calendar(items, user, key):
    c1, c2, c3 = st.columns([1, 1, 2])
    d = c1.date_input(t("Date", "Fecha"), value=dt.date.today() + dt.timedelta(days=1), key=f"{key}_d", format=date_fmt())
    tm = c2.time_input(t("Time (ET)", "Hora (ET)"), value=dt.time(11, 0), key=f"{key}_t")
    with c3:
        st.write("")
        if st.button(t("Save to calendar as Draft", "Guardar en el calendario como Borrador"), key=f"{key}_s", type="primary"):
            for it in items:
                db.insert_row(db.posts, dict(publish_date=d.isoformat(), publish_time=tm.strftime("%H:%M"),
                                             status="Draft", owner=user, created_by=user, updated_at=db.now(), **it))
            st.success(t(f"{len(items)} post(s) saved to the calendar.", f"{len(items)} post(s) guardados en el calendario."))


def page_reports():
    header("Performance", t("Reports", "Reportes"),
           t("They update on their own from the linked accounts.", "Se actualizan solos con las cuentas vinculadas."))
    last = db.get_meta("last_sync")
    c1, c2 = st.columns([3, 1])
    c1.caption(t(f"Last sync: {last or 'never'}", f"Última sincronización: {last or 'nunca'}"))
    if c2.button(t("↻ Sync now", "↻ Sincronizar ahora"), width="stretch"):
        with st.spinner(t("Fetching metrics…", "Trayendo métricas…")):
            for acc, status, n in integrations.sync_all():
                status_txt = t(status, "sin vincular") if status == "not linked" else status
                (st.success if status == "ok" else st.info)(f"{acc_label(acc)}: {status_txt} ({n} posts)")

    m = load_metrics()
    f1, f2 = st.columns([2.5, 1])
    accs = f1.multiselect(t("Accounts", "Cuentas"), ACC_KEYS, default=ACC_KEYS,
                          format_func=lambda k: ACCOUNTS[k]["short"], key="rp_acc")
    period = f2.selectbox(t("Period", "Período"), [7, 30, 90, 0], index=1,
                          format_func=lambda d: t("All time", "Todo") if d == 0 else t(f"Last {d} days", f"Últimos {d} días"))

    if m.empty:
        st.info(t("No metrics yet. Link the accounts (Accounts section) or add them manually below.",
                  "Todavía no hay métricas. Vinculá las cuentas (sección Cuentas) o cargalas a mano abajo."))
    else:
        m = m[m["account"].isin(accs)]
        if period:
            m = m[m["published_at"] >= pd.Timestamp(dt.date.today() - dt.timedelta(days=period))]
        k = st.columns(5)
        k[0].metric("Posts", len(m))
        k[1].metric("Likes", f"{m['likes'].sum():,}")
        k[2].metric(t("Comments", "Comentarios"), f"{m['comments'].sum():,}")
        k[3].metric(t("Views", "Visualizaciones"), f"{m['views'].sum():,}")
        er = m["engagement_%"].dropna()
        k[4].metric(t("Avg. engagement", "Engagement prom."), f"{er.mean():.2f}%" if len(er) else "—")

        if not m.empty:
            scale = alt.Scale(domain=[a["label"] for a in ACCOUNTS.values()],
                              range=[a["color"] for a in ACCOUNTS.values()])
            base = m.assign(date=m["published_at"].dt.strftime("%d/%m" if is_es() else "%m/%d"),
                            post=(m["caption"].fillna("").str[:40]))
            leg = alt.Legend(orient="bottom", title=None, columns=2)
            ch1, ch2 = st.columns(2)
            with ch1:
                st.subheader(t("Likes per post", "Likes por post"))
                st.altair_chart(alt.Chart(base).mark_bar(size=16).encode(
                    x=alt.X("published_at:T", title=None), y=alt.Y("likes:Q", title="Likes"),
                    color=alt.Color("account_name:N", scale=scale, legend=leg),
                    tooltip=["account_name", "date", "post", "likes", "comments", "views"]).properties(height=280),
                    width="stretch")
            with ch2:
                st.subheader(t("Views per post", "Visualizaciones por post"))
                st.altair_chart(alt.Chart(base).mark_line(point=True).encode(
                    x=alt.X("published_at:T", title=None), y=alt.Y("views:Q", title=t("Views", "Visualizaciones")),
                    color=alt.Color("account_name:N", scale=scale, legend=leg),
                    tooltip=["account_name", "date", "post", "views", "reach"]).properties(height=280),
                    width="stretch")

            st.subheader(t("By account", "Comparación por cuenta"))
            agg = m.groupby("account_name").agg(posts=("id", "count"), likes=("likes", "sum"),
                                                comments=("comments", "sum"), views=("views", "sum"),
                                                engagement=("engagement_%", "mean")).round(2)
            agg.index.name = t("account", "cuenta")
            agg.columns = ["posts", "likes", t("comments", "comentarios"), t("views", "visualizaciones"),
                           t("avg engagement %", "engagement prom. %")]
            st.dataframe(agg, width="stretch")

            posts = load_posts()
            if not posts.empty and posts["permalink"].notna().any():
                j = m.merge(posts[["permalink", "pillar", "format", "title"]].dropna(subset=["permalink"]),
                            on="permalink", how="inner")
                if not j.empty:
                    st.subheader(t("Performance by content pillar", "Rendimiento por pilar de contenido"))
                    pp = j.groupby("pillar").agg(posts=("id", "count"), avg_interactions=("interactions", "mean"),
                                                 avg_views=("views", "mean")).round(1).reset_index()
                    pp["pillar"] = pp["pillar"].map(opt)
                    st.altair_chart(alt.Chart(pp).mark_bar(color=BRAND["black"]).encode(
                        y=alt.Y("pillar:N", sort="-x", title=None),
                        x=alt.X("avg_interactions:Q", title=t("Avg. interactions", "Interacciones promedio")),
                        tooltip=list(pp.columns)).properties(height=40 * len(pp) + 40), width="stretch")

            st.subheader(t("Post by post", "Detalle por posteo"))
            tb = m.sort_values("published_at", ascending=False)[
                ["published_at", "account_name", "caption", "likes", "comments", "views", "reach", "shares", "saves",
                 "engagement_%", "permalink", "source"]]
            st.dataframe(tb, width="stretch", hide_index=True, column_config={
                "account_name": t("account", "cuenta"),
                "comments": t("comments", "comentarios"), "views": t("views", "visualizaciones"),
                "reach": t("reach", "alcance"), "shares": t("shares", "compartidos"), "saves": t("saves", "guardados"),
                "source": t("source", "origen"),
                "permalink": st.column_config.LinkColumn("link", display_text=t("view", "ver")),
                "caption": st.column_config.TextColumn("post", width="large"),
                "published_at": st.column_config.DatetimeColumn(t("date", "fecha"),
                                                                format="DD/MM/YY" if is_es() else "MM/DD/YY")})
            st.download_button(t("Download report CSV", "Descargar reporte CSV"), tb.to_csv(index=False).encode(),
                               "xb_report.csv")

    with st.expander(t("Add metrics manually or via CSV (for accounts without API access)",
                       "Cargar métricas a mano o por CSV (para cuentas sin API)")):
        st.caption(t("Useful for John's and Ximena's personal LinkedIn profiles until they get API access. "
                     "CSV columns: account (ig_xb / li_xb / li_john / li_ximena), published_at, permalink, caption, "
                     "likes, comments, views",
                     "Útil para los perfiles personales de LinkedIn mientras no tengan acceso a la API. "
                     "Columnas del CSV: account (ig_xb / li_xb / li_john / li_ximena), published_at, permalink, caption, "
                     "likes, comments, views"))
        with st.form("manual_metric", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            acc = c1.selectbox(t("Account", "Cuenta"), ACC_KEYS, format_func=acc_label)
            pub = c2.date_input(t("Post date", "Fecha del post"), format=date_fmt())
            perma = c3.text_input(t("Post link", "Link del post"))
            cap = st.text_input(t("Text / topic", "Texto / tema"))
            c4, c5, c6, c7 = st.columns(4)
            likes = c4.number_input(t("Likes / reactions", "Likes / reacciones"), 0)
            com = c5.number_input(t("Comments", "Comentarios"), 0)
            views = c6.number_input(t("Views / impressions", "Visualizaciones / impresiones"), 0)
            shares = c7.number_input(t("Shares", "Compartidos"), 0)
            if st.form_submit_button(t("Save", "Guardar")) and perma:
                db.upsert_metric(dict(account=acc, external_id=perma, permalink=perma, caption=cap,
                                      published_at=pub.isoformat(), media_type="manual", likes=likes, comments=com,
                                      views=views, reach=0, shares=shares, saves=0, source="manual"))
                st.rerun()
        up = st.file_uploader(t("Upload CSV", "Subir CSV"), type="csv")
        if up is not None and st.button(t("Import CSV", "Importar CSV")):
            c = pd.read_csv(io.BytesIO(up.getvalue()))
            for _, r in c.iterrows():
                db.upsert_metric(dict(account=r["account"], external_id=str(r["permalink"]), permalink=r["permalink"],
                                      caption=r.get("caption", ""), published_at=str(r["published_at"]),
                                      media_type="csv", likes=int(r.get("likes", 0)), comments=int(r.get("comments", 0)),
                                      views=int(r.get("views", 0)), reach=0, shares=0, saves=0, source="csv"))
            st.success(t(f"{len(c)} rows imported.", f"{len(c)} filas importadas."))


def _instagram_connect(col):
    """'Connect Instagram' button (OAuth) for the XB account."""
    if ig_oauth.stored_token():
        user = db.get_meta("ig_username") or "instagram"
        exp = (db.get_meta("ig_token_expires") or "")[:10]
        col.caption(t(f"Connected as @{user} · renews automatically (current until {exp})",
                      f"Conectada como @{user} · se renueva sola (vigente hasta {exp})"))
        if col.button(t("Disconnect", "Desconectar"), key="ig_disconnect"):
            ig_oauth.disconnect()
            st.rerun()
    elif ig_oauth.oauth_ready():
        col.link_button(t("🔗 Connect Instagram", "🔗 Conectar Instagram"), ig_oauth.auth_link())
        col.caption(t("Log in with @xb.architecture. A new tab opens; come back here when it says Connected.",
                      "Entrá con @xb.architecture. Se abre otra pestaña; volvé acá cuando diga Conectada."))
    else:
        col.caption(t("To enable the Connect button, add IG_APP_ID and IG_APP_SECRET to secrets (see README).",
                      "Para activar el botón Conectar, agregá IG_APP_ID e IG_APP_SECRET en los secrets (ver README)."))


PRIVACY_MD = """
# Privacy Policy — XB Content Studio

*Last updated: October 21, 2026*

XB Content Studio is an internal tool operated by **XB Architecture PLLC**
(2300 E Oakland Park Blvd, Suite 208, Fort Lauderdale, FL, USA) to plan, write and measure
the social media content of XB Architecture. It is used only by XB Architecture team members.

## Information we collect
- **Team accounts:** the username of each team member who signs in to the tool.
- **Content we create:** planned posts, captions, ideas and internal notes written by our team.
- **Social media metrics of our own accounts:** for the XB Architecture LinkedIn Page and the
  @xb.architecture Instagram account we read aggregated post metrics (likes/reactions, comments,
  views/impressions, reach, shares, saves), post text, publication date and post link.
  We do not collect information about individual members who engage with our posts.

## How we use it
Only to schedule and coordinate our posts and to produce internal performance reports.
We do not sell, rent or share this information with third parties, and we do not use it for advertising.

## Service providers
Data is stored in a private database (Supabase) and the tool is hosted on Streamlit Community Cloud.
Caption drafts are generated with Google Gemini from briefs written by our team; no LinkedIn or
Instagram member data is sent to the AI.

## Access tokens and retention
Access tokens are stored encrypted in our hosting provider's secret storage or private database,
and can be revoked at any time from LinkedIn or Instagram settings. Metrics are kept while they are
useful for reporting and deleted on request or when an account is disconnected.

## Contact
Questions or deletion requests: faustina@xb-architecture.com
"""


def privacy_page():
    """Public page (no login): https://<app>/?privacy"""
    if "privacy" not in st.query_params:
        return
    _, mid, _ = st.columns([1, 2.2, 1])
    with mid:
        st.markdown(f"<div style='margin-top:4vh'>{LOGO_SVG.format(w=120)}</div>", unsafe_allow_html=True)
        st.markdown(PRIVACY_MD)
    st.stop()


def handle_instagram_return():
    """Runs before login: Instagram sends the user back here with ?code=…"""
    qp = st.query_params
    if "code" not in qp and "error" not in qp:
        return
    code, state, err = qp.get("code"), qp.get("state"), qp.get("error")
    st.query_params.clear()
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown(f"<div style='text-align:center;margin-top:8vh'>{LOGO_SVG.format(w=150)}</div>",
                    unsafe_allow_html=True)
        if err:
            st.warning("Instagram: connection cancelled. / Conexión cancelada.")
        else:
            with st.spinner("Connecting Instagram… / Conectando Instagram…"):
                try:
                    ok, msg = ig_oauth.handle_callback(code, state)
                except Exception as e:  # noqa: BLE001
                    ok, msg = False, str(e)[:200]
            if ok:
                db.set_meta("last_sync", "")   # sync right away on next visit
                st.success(f"✅ Instagram connected: {msg}  ·  Instagram conectado: {msg}")
                st.caption("You can close this tab. / Ya podés cerrar esta pestaña.")
            else:
                st.error(msg)
    st.stop()


def page_accounts():
    header(t("Settings", "Configuración"), t("Linked accounts", "Cuentas vinculadas"),
           t("Connection status and each account's voice (used by the AI).",
             "Estado de conexión y voz de cada cuenta (la usa la IA)."))
    for acc in ACC_KEYS:
        ok = integrations.is_configured(acc)
        status = db.get_meta(f"sync_{acc}") or "—"
        with st.container(border=True):
            c1, c2 = st.columns([1.2, 2])
            c1.markdown(f"**{acc_label(acc)}**")
            c1.markdown(t("🟢 Linked", "🟢 Vinculada") if ok else t("⚪ Not linked (see README)", "⚪ Sin vincular (ver README)"))
            c1.caption(t(f"Last sync: {status}", f"Última sync: {status}"))
            if acc == "ig_xb":
                _instagram_connect(c1)
            v = c2.text_area(t("Account voice (write it in English or Spanish)", "Voz de la cuenta (en inglés o español)"),
                             value=ai.voice(acc), key=f"voice_{acc}", height=110)
            b1, b2, _ = c2.columns([1, 1, 2])
            if b1.button(t("Save voice", "Guardar voz"), key=f"sv_{acc}"):
                db.set_meta(f"voice_{acc}", v)
                st.success(t("Saved", "Guardado"))
            if b2.button(t("Reset", "Restaurar"), key=f"rv_{acc}"):
                db.set_meta(f"voice_{acc}", DEFAULT_VOICES[acc])
                st.session_state.pop(f"voice_{acc}", None)
                st.rerun()
    ai_ok = ai.provider() is not None
    shared = bool(get_secret("DATABASE_URL"))
    st.caption(f"AI: {t('🟢 connected', '🟢 conectada') if ai_ok else t('⚪ missing GEMINI_API_KEY', '⚪ falta GEMINI_API_KEY')}"
               f" · {t('model', 'modelo')} {ai.MODEL} · {t('Database', 'Base de datos')}: "
               f"{t('shared Postgres', 'Postgres compartida') if shared else t('local SQLite (testing only)', 'SQLite local (solo pruebas)')}")


# ======================================================================
# Main
# ======================================================================
PAGES = [
    ("home", ("Home", "Inicio"), page_home),
    ("calendar", ("Calendar", "Calendario"), page_calendar),
    ("ideas", ("Ideas", "Ideas"), page_ideas),
    ("copy", ("AI Captions", "Copys IA"), page_copy),
    ("reports", ("Reports", "Reportes"), page_reports),
    ("accounts", ("Accounts", "Cuentas"), page_accounts),
]


def main():
    inject_css()
    privacy_page()
    handle_instagram_return()
    user = login()
    if not st.session_state.get("synced_once"):
        st.session_state["synced_once"] = True
        try:
            integrations.maybe_auto_sync()
        except Exception:
            pass
    labels = {k: lbl for k, lbl, _ in PAGES}
    funcs = {k: f for k, _, f in PAGES}
    with st.sidebar:
        st.markdown(f"<div style='background:#fff;padding:14px;margin-bottom:18px'>{LOGO_SVG.format(w='100%')}</div>",
                    unsafe_allow_html=True)
        current = st.session_state.get("page", "home")
        page = st.radio("Navigation", list(labels), format_func=lambda k: t(*labels[k]),
                        index=list(labels).index(current), label_visibility="collapsed",
                        key=f"nav_{st.session_state.get('lang', 'en')}")
        st.session_state["page"] = page
        st.markdown("---")
        language_switch()
        st.caption(t(f"Signed in: {user}", f"Sesión: {user}"))
        if st.button(t("Sign out", "Salir")):
            keep = st.session_state.get("lang", "en")
            st.session_state.clear()
            st.session_state["lang"] = keep
            st.rerun()
    funcs[page]()


main()
