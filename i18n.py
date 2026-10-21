"""English / Spanish UI. English is the default; each user's choice is remembered.

Usage:  t("English text", "Texto en español")   → returns the active language
        opt(value)                              → translates a stored option (pillar, format, status…)
"""
import streamlit as st

# Stored (English) option values → Spanish label
_OPTIONS_ES = {
    # pillars
    "Finished project": "Proyecto terminado",
    "Under construction": "Obra en construcción",
    "Before & After": "Antes & Después",
    "Design process": "Proceso de diseño",
    "Details & materials": "Detalle / materiales",
    "Behind the scenes / Team": "Detrás de escena / Equipo",
    "Educational / Tips": "Educativo / Tips",
    "Client testimonial": "Testimonio de cliente",
    "Trends & Inspiration": "Tendencias & Inspiración",
    "Leadership / Opinion": "Liderazgo / Opinión",
    # formats
    "Carousel": "Carrusel",
    "Reel": "Reel",
    "Photo": "Foto",
    "Video": "Video",
    "Story": "Story",
    "Text post": "Post de texto",
    "Article": "Artículo",
    "PDF document": "Documento PDF",
    # post statuses
    "Idea": "Idea",
    "Draft": "Borrador",
    "In review": "En revisión",
    "Approved": "Aprobado",
    "Scheduled": "Programado",
    "Published": "Publicado",
    # idea statuses / sources
    "New": "Nueva",
    "Used": "Usada",
    "Archived": "Archivada",
    "Team": "Equipo",
    "AI": "IA",
    # AI output languages
    "English": "Inglés",
    "Spanish": "Español",
    "Bilingual (EN + ES)": "Bilingüe (EN + ES)",
}

LANG_OPTIONS = {"en": "🇺🇸 English", "es": "🇦🇷 Español"}


def lang():
    return st.session_state.get("lang", "en")


def is_es():
    return lang() == "es"


def t(en, es=None):
    return es if (is_es() and es is not None) else en


def opt(value):
    if value is None:
        return ""
    return _OPTIONS_ES.get(value, value) if is_es() else value


def days():
    return ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"] if is_es() else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def short_date(d):
    """dd/mm in Spanish, mm/dd in English."""
    return f"{d:%d/%m}" if is_es() else f"{d:%m/%d}"


def date_fmt():
    """Format string for st.date_input."""
    return "DD/MM/YYYY" if is_es() else "MM/DD/YYYY"
