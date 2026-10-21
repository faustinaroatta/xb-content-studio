"""Central config: branding, accounts, content pillars and inspiration.

Values stored in the database are always the English (canonical) ones.
Spanish labels for the UI live in i18n.py.
"""
import os

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


def get_secret(key, default=None):
    """Reads .streamlit/secrets.toml (or Streamlit Cloud Secrets) first, then environment variables."""
    if st is not None:
        try:
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass
    return os.getenv(key, default)


# ---------- XB Architecture branding ----------
BRAND = {
    "black": "#111111",
    "grey": "#8C8C8C",
    "mid": "#5C5C5C",
    "light": "#F3F2EF",
    "line": "#E2E0DC",
    "bg": "#FAFAF8",
    "white": "#FFFFFF",
}

LOGO_SVG = """
<svg viewBox="0 0 200 128" xmlns="http://www.w3.org/2000/svg" width="{w}">
  <rect x="0" y="0" width="100" height="100" fill="#111111"/>
  <rect x="100" y="0" width="100" height="100" fill="#8C8C8C"/>
  <text x="60" y="96" font-family="Helvetica Neue, Helvetica, Arial" font-size="92" font-weight="300" fill="#FFFFFF" text-anchor="middle">x</text>
  <text x="148" y="96" font-family="Helvetica Neue, Helvetica, Arial" font-size="92" font-weight="300" fill="#FFFFFF" text-anchor="middle">b</text>
  <text x="100" y="124" font-family="Helvetica Neue, Helvetica, Arial" font-size="17" letter-spacing="5.5" fill="#111111" text-anchor="middle">ARCHITECTURE</text>
</svg>
"""

BRAND_CONTEXT = """XB Architecture (XBarchitecture) is an architecture studio in Fort Lauderdale, Florida
(2300 E Oakland Park Blvd, Suite 208). Tagline: "Exceptional Service | Unparalleled Design".
They specialize in luxury residences in South Florida: waterfront homes, tropical modernism, pools,
large glazing, contemporary and coastal architecture. Featured projects: North Miami, Royal Palm,
Sea Island, Coral Ridge, Surfside and Plantation Acres. They share construction progress, before & after
and finished projects. Aesthetic: monochrome (black, grey, white), restrained, elegant, minimal.
Audience: high-net-worth homeowners, developers, builders, real estate agents and interior designers
in South Florida."""


# ---------- Accounts ----------
ACCOUNTS = {
    "ig_xb": {"label": "Instagram · XB Architecture", "short": "IG · XB", "platform": "Instagram", "color": "#111111"},
    "li_xb": {"label": "LinkedIn · XB Architecture", "short": "in · XB", "platform": "LinkedIn", "color": "#5C5C5C"},
    "li_john": {"label": "LinkedIn · John", "short": "in · John", "platform": "LinkedIn", "color": "#8C8C8C"},
    "li_ximena": {"label": "LinkedIn · Ximena", "short": "in · Ximena", "platform": "LinkedIn", "color": "#B3AEA6"},
}

# Default voice per account (the team can edit it in the app → Accounts). Used by the AI.
DEFAULT_VOICES = {
    "ig_xb": "Visual and aspirational. Short sentences, unhurried rhythm, no hype. At most 1-2 understated emojis. "
             "Ends with a soft CTA (save, DM, link in bio). 8-15 hashtags mixing niche and local "
             "(#FortLauderdaleArchitecture #MiamiLuxuryHomes #SouthFloridaDesign...).",
    "li_xb": "Institutional but warm. Tells the project story: the design or technical challenge and the outcome. "
             "Credits the team and collaborators. Short paragraphs, hook in the first line. 3-5 hashtags.",
    "li_john": "First person, voice of a leader at XB Architecture. Lessons from the craft and the business, "
               "design decisions, relationships with clients and builders. Honest, reflective, one clear idea "
               "per post. Max 3 hashtags. (Edit with his actual role.)",
    "li_ximena": "First person, voice of a leader at XB Architecture. Creative process, design details, "
                 "materials, client and team experience. Warm, inspiring and concrete. Max 3 hashtags. "
                 "(Edit with her actual role.)",
}

PILLARS = [
    "Finished project",
    "Under construction",
    "Before & After",
    "Design process",
    "Details & materials",
    "Behind the scenes / Team",
    "Educational / Tips",
    "Client testimonial",
    "Trends & Inspiration",
    "Leadership / Opinion",
]

FORMATS = ["Carousel", "Reel", "Photo", "Video", "Story", "Text post", "Article", "PDF document"]

STATUSES = ["Idea", "Draft", "In review", "Approved", "Scheduled", "Published"]

IDEA_STATUSES = ["New", "Used", "Archived"]

# Language of the AI-generated content (independent of the app language).
LANGUAGES = ["English", "Spanish", "Bilingual (EN + ES)"]

# Famous accounts used as style references (the AI borrows the approach, never the content).
INSPO = [
    {"name": "ArchDaily", "en": "Impeccable curation: carousels combining photo, plan and section; clear project data.",
     "es": "Curaduría impecable: carruseles que combinan foto, planta y corte; ficha técnica clara."},
    {"name": "Dezeen", "en": "Strong editorial headlines and storytelling around the concept behind the project.",
     "es": "Titulares editoriales fuertes y storytelling del concepto detrás del proyecto."},
    {"name": "Architectural Digest", "en": "Luxury lifestyle: home tours, the owner and the story, vertical video.",
     "es": "Lifestyle de lujo: tours de casas, el dueño y la historia, video vertical."},
    {"name": "Zaha Hadid Architects", "en": "Iconic imagery + render vs. reality; focus on form and technology.",
     "es": "Imagen icónica + render vs. realidad; foco en forma y tecnología."},
    {"name": "BIG – Bjarke Ingels Group", "en": "Ideas explained with simple diagrams and humor; the 'why' of the design.",
     "es": "Ideas explicadas con diagramas simples y humor; el 'por qué' del diseño."},
    {"name": "Olson Kundig", "en": "Materiality, craftsmanship and connection to landscape; mechanical details.",
     "es": "Materialidad, artesanía y conexión con el paisaje; detalles mecánicos."},
    {"name": "Marmol Radziner", "en": "Residential modernism: indoor-outdoor living, natural light, walkthrough sequences.",
     "es": "Modernismo residencial: indoor-outdoor, luz natural, secuencias de recorrido."},
    {"name": "Studio MK27", "en": "Pure architectural photography, minimal compositions, wood and concrete.",
     "es": "Fotografía arquitectónica pura, composiciones minimalistas y madera/hormigón."},
    {"name": "Kengo Kuma & Associates", "en": "Textures and layers; material as the protagonist.",
     "es": "Texturas y capas; el material como protagonista."},
    {"name": "STRANG (Miami)", "en": "South Florida tropical modernism: shade, ventilation, vegetation.",
     "es": "Modernismo tropical del sur de Florida: sombra, ventilación, vegetación."},
    {"name": "Kobi Karp (Miami)", "en": "Large-scale coastal projects, aspirational renders and skyline.",
     "es": "Proyectos costeros de gran escala, renders aspiracionales y skyline."},
    {"name": "Choeff Levy Fischman (Miami)", "en": "Contemporary waterfront homes; drone shots and pools.",
     "es": "Casas contemporáneas frente al agua; drone shots y piscinas."},
]

SYNC_EVERY_HOURS = int(os.getenv("SYNC_EVERY_HOURS", "6"))
