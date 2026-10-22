"""Content AI (Anthropic's Claude): copy, multi-account adaptations, ideas and weekly planning.

The output language is chosen per request (English / Spanish / Bilingual), independent of the app language.
"""
import json
import re

import db
from config import (ACCOUNTS, BRAND_CONTEXT, DEFAULT_VOICES, FORMATS, INSPO,
                    PILLARS, get_secret)

import requests

# Provider: Google Gemini (free tier) if GEMINI_API_KEY is set, otherwise Anthropic Claude (paid).
GEMINI_MODELS = [m for m in [get_secret("GEMINI_MODEL"), "gemini-3.8-flash", "gemini-3.5-flash-lite"] if m]
CLAUDE_MODEL = get_secret("ANTHROPIC_MODEL") or "claude-sonnet-5-5"


def provider():
    if get_secret("GEMINI_API_KEY"):
        return "gemini"
    if get_secret("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


MODEL = GEMINI_MODELS[0] if provider() == "gemini" else CLAUDE_MODEL


def voice(account):
    return db.get_meta(f"voice_{account}") or DEFAULT_VOICES[account]


def _missing_key():
    return RuntimeError("Missing AI key: add GEMINI_API_KEY (free) to secrets. / "
                        "Falta la clave de IA: agregá GEMINI_API_KEY (gratis) en los secrets.")


SYSTEM = f"""You are the social media strategist and copywriter for XB Architecture.
{BRAND_CONTEXT}
Rules: never invent concrete facts (square footage, prices, client names, awards) — if needed, leave a
placeholder in brackets like [project sq ft]. PRIVACY: never write a street address, house number or client name in
any content — refer to projects only by neighborhood/city and type (e.g. "a waterfront residence in Fort Lauderdale"). No empty clichés ("dream home", "stunning").
Write like a premium architecture studio: precise, sensory, confident.
Always write the content in the language requested in each message."""


def _system():
    try:
        import projects
        ctx = projects.context_for_ai()
    except Exception:  # noqa: BLE001
        ctx = ""
    return SYSTEM + ("\n\n" + ctx if ctx else "")


def _ask_gemini(prompt, max_tokens, image=None, json_mode=False):
    import base64
    key = get_secret("GEMINI_API_KEY")
    parts = [{"text": prompt}]
    for img in (image if isinstance(image, list) else [image] if image else []):
        parts.append({"inline_data": {"mime_type": img[1], "data": base64.b64encode(img[0]).decode()}})
    body = {"system_instruction": {"parts": [{"text": _system()}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"maxOutputTokens": max(max_tokens, 4096),
                                 **({"responseMimeType": "application/json"} if json_mode else {})}}
    last = ""
    for model in GEMINI_MODELS:   # if one model is busy or retired, try the next free one
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        r = requests.post(url, headers={"x-goog-api-key": str(key).strip(), "Content-Type": "application/json"},
                          json=body, timeout=120)
        if r.status_code in (400, 401, 403):
            r = requests.post(url, params={"key": str(key).strip()}, json=body, timeout=120)
        if r.status_code in (400, 401, 403):
            r = requests.post(url, headers={"Authorization": f"Bearer {str(key).strip()}",
                                            "Content-Type": "application/json"}, json=body, timeout=120)
        if r.status_code in (401, 403):
            raise RuntimeError("Gemini rejected the key (it may have been deleted or mistyped). Create a new key in "
                               "aistudio.google.com/api-keys and paste it in Secrets → GEMINI_API_KEY. / "
                               "Gemini rechazó la clave (puede estar borrada o mal copiada). Creá una nueva en "
                               "aistudio.google.com/api-keys y pegala en Secrets → GEMINI_API_KEY. "
                               f"[Google: {r.text[:180]}]")
        if r.ok:
            parts = (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()
            if text:
                return text
            last = "empty response"
        else:
            last = f"{r.status_code}: {r.text[:200]}"
    raise RuntimeError(f"Gemini error / error de Gemini — {last}")


def _ask_claude(prompt, max_tokens, image=None):
    import base64
    from anthropic import Anthropic
    content = prompt
    imgs = image if isinstance(image, list) else [image] if image else []
    if imgs:
        content = [{"type": "image", "source": {"type": "base64", "media_type": m, "data": base64.b64encode(b).decode()}}
                   for b, m in imgs] + [{"type": "text", "text": prompt}]
    msg = Anthropic(api_key=get_secret("ANTHROPIC_API_KEY")).messages.create(
        model=CLAUDE_MODEL, max_tokens=max_tokens, system=_system(),
        messages=[{"role": "user", "content": content}])
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def _ask(prompt, max_tokens=2500, image=None, json_mode=False):
    p = provider()
    if p == "gemini":
        return _ask_gemini(prompt, max_tokens, image, json_mode)
    if p == "anthropic":
        return _ask_claude(prompt, max_tokens, image)
    raise _missing_key()


def _json(text):
    """Robust JSON reader: handles code fences, extra text, several arrays/objects in a row."""
    text = re.sub(r"```(?:json)?", "", text or "").strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    dec, i, found = json.JSONDecoder(), 0, []
    while i < len(text):
        m = re.search(r"[\[{]", text[i:])
        if not m:
            break
        start = i + m.start()
        try:
            obj, end = dec.raw_decode(text, start)
            found.append(obj)
            i = end
        except ValueError:
            i = start + 1
    if not found:
        raise ValueError("The AI did not return valid data, please try again. / La IA no devolvió datos válidos, probá de nuevo.")
    if len(found) == 1:
        return found[0]
    items = []
    for f in found:
        items.extend(f if isinstance(f, list) else [f])
    if all(isinstance(x, dict) for x in items) and isinstance(found[0], dict) and len(items) == 1:
        return items[0]
    return items


def _as_list(data):
    """Accepts [..], {"projects": [..]}, {"ideas": [..]} or a single object."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list) and all(isinstance(x, dict) for x in v):
                return v
        return [data]
    return []


def _acc_block(account):
    a = ACCOUNTS[account]
    return f"Account: {a['label']} ({a['platform']}). Voice: {voice(account)}"


def _lang_rule(language):
    if language.startswith("Bilingual"):
        return "Write it in English first, then the full Spanish version below it."
    return f"Write it in {language}."


def generate_copy(account, topic, fmt, pillar, language, tone="", extra=""):
    p = f"""{_acc_block(account)}
Write the caption, ready to publish. {_lang_rule(language)}
Topic / brief: {topic}
Format: {fmt} · Pillar: {pillar}
Extra tone: {tone or '—'}
Extra notes: {extra or '—'}
If it's a carousel or reel, add a final "SCRIPT" section with what goes on each slide/scene.
Return only the caption (and script if applicable), no explanations."""
    return _ask(p)


def rewrite(text, account, instruction, language):
    p = f"""{_acc_block(account)}
Rewrite this caption following the instruction: {instruction}. {_lang_rule(language)}
CAPTION:
{text}
Return only the new caption."""
    return _ask(p)


def adapt_all(topic, pillar, language, extra=""):
    blocks = "\n".join(f"- {k}: {_acc_block(k)}" for k in ACCOUNTS)
    p = f"""We have one topic and need a different version for each account, respecting each voice.
Topic: {topic} · Pillar: {pillar} · Extra: {extra or '—'}
Language: {_lang_rule(language)}
Accounts:
{blocks}
Return ONLY a JSON with this shape:
{{"ig_xb": {{"format": "...", "copy": "..."}}, "li_xb": {{...}}, "li_john": {{...}}, "li_ximena": {{...}}}}
format must be one of: {FORMATS}"""
    return _json(_ask(p, 4000, json_mode=True))


def generate_ideas(n, pillars, inspo_names, accounts, language, extra=""):
    insp = [i for i in INSPO if i["name"] in inspo_names] or INSPO
    insp_txt = "\n".join(f"- {i['name']}: {i['en']}" for i in insp)
    acc_txt = ", ".join(f"{k} ({ACCOUNTS[k]['label']})" for k in accounts)
    p = f"""Propose {n} concrete, executable content ideas for XB Architecture.
Take inspiration from the APPROACH (not the content) of these reference accounts:
{insp_txt}
Pillars to cover: {', '.join(pillars) or 'any'}
Possible accounts: {acc_txt}
Extra context: {extra or '—'}
Use XB's real projects from the project list (and match the idea to each project's phase) when it makes sense.
Write "title", "description" and "inspo" in {language if not language.startswith('Bilingual') else 'English'}.
Return ONLY a JSON list of objects with keys
"title" (short hook), "description" (how to execute it: shots, slides, script in 2-4 sentences),
"pillar" (exactly one of {PILLARS}), "format" (exactly one of {FORMATS}), "account" (one of {list(accounts)}),
"inspo" (which reference account inspires it and why, one sentence)."""
    return _as_list(_json(_ask(p, 4000, json_mode=True)))


def plan_weeks(start, days, per_account, language, notes, taken_titles):
    acc_txt = "\n".join(f"- {k}: {n} posts/week. {_acc_block(k)}" for k, n in per_account.items() if n)
    p = f"""Build XB Architecture's content calendar starting {start} for {days} days.
Frequency per account:
{acc_txt}
Team notes: {notes or '—'}
Avoid repeating these already scheduled topics: {taken_titles[:40]}
Vary pillars and formats and coordinate accounts (e.g. a project posted on IG can get John's or Ximena's
personal take on LinkedIn the same or next day). Recommended times for a South Florida audience (ET):
IG 11:00-13:00 or 18:00-20:00; LinkedIn Tue-Thu 8:00-10:00.
Captions: {_lang_rule(language)} Titles in English.
Return ONLY a JSON list of objects with
"date" (YYYY-MM-DD), "time" (HH:MM), "account" (one of {list(per_account)}), "format" (exactly one of {FORMATS}),
"pillar" (exactly one of {PILLARS}), "title" (short), "copy" (full caption ready for review)."""
    return _as_list(_json(_ask(p, 8000, json_mode=True)))


def adapt_inspo(title, summary, source, studio, accounts, language):
    """Turns a news item about another studio into a concrete XB post idea (no copying)."""
    acc_txt = ", ".join(f"{k} ({ACCOUNTS[k]['label']})" for k in accounts)
    p = f"""A reference studio just published this ({source}):
Title: {title}
Studio: {studio or 'unknown'}
Summary: {summary}

Propose ONE concrete post idea for XB Architecture inspired by the APPROACH or topic of this news
(format, angle, storytelling, innovation) — never copy it or claim their work. Connect it to XB's real
projects from the project list when it makes sense.
Possible accounts: {acc_txt}.
Write everything in {language if not language.startswith('Bilingual') else 'English'}.
Return ONLY JSON: {{"title": "...", "why": "what to borrow from the reference, 1 sentence",
"description": "how to execute it, 2-4 sentences", "caption": "a ready-to-edit caption draft",
"pillar": one of {PILLARS}, "format": one of {FORMATS}, "account": one of {list(accounts)}}}"""
    return _json(_ask(p, 2500, json_mode=True))



def extract_projects(text="", image=None):
    """Reads a Monograph export (table text, pasted text or screenshot) and returns a clean project list."""
    p = f"""This is an export / copy / screenshot of XB Architecture's project list from their project
management software (Monograph). Extract every PROJECT (ignore totals, invoices, hours, fees, money and people).
Monograph names look like "2417_2717 NE 26th Ter_Ex..." (job number _ street address _ client/description).
For each project return: "name" (job number + short street/description as written, e.g. "2417 · NE 26th Ter"; drop
client surnames), "location" (neighborhood/city if you can infer it — e.g. NE/SE streets with no city → "Fort Lauderdale area",
"Pompano" → "Pompano Beach" — else ""),
"phase" (one of: Design, Permits, Under construction, Finished, On hold, Other — infer from status/phase columns or
phase labels: CA/Construction Administration → Under construction; SD/DD/CD/Schematic/Design Development/Construction
Documents → Design; Permit/Permitting/Bidding → Permits; Closed/Archived/Complete → Finished),
"type" (e.g. single-family residence, renovation, multifamily — if present, else ""), "notes" (max 1 short line or "").
Never include fees, budgets, client names or personal data.
Return ONLY a JSON list.
DATA:
{text[:28000]}"""
    return _as_list(_json(_ask(p, 6000, image, json_mode=True)))


def project_ideas(project, accounts, language, n=4):
    acc_txt = ", ".join(f"{k} ({ACCOUNTS[k]['label']})" for k in accounts)
    p = f"""Propose {n} post ideas about this XB project, perfect for its current phase:
Project: {project.get('name')} · Location: {project.get('location') or '—'} · Phase: {project.get('phase')}
Type: {project.get('type') or '—'} · Notes: {project.get('notes') or '—'}
Phase guide: Design → process, sketches, renders, design decisions; Permits → behind the scenes, challenges;
Under construction → progress, structure, details, site visits, team; Finished → reveal, walkthrough, before & after,
details, client experience, awards-style storytelling.
Possible accounts: {acc_txt}. Write in {language if not language.startswith('Bilingual') else 'English'}.
Return ONLY a JSON list of objects with "title", "description" (2-3 sentences on how to execute it),
"pillar" (one of {PILLARS}), "format" (one of {FORMATS}), "account" (one of {list(accounts)}), "inspo" ("")."""
    return _as_list(_json(_ask(p, 3000, json_mode=True)))



def caption_from_photos(images, project, account, fmt, language, extra=""):
    """Looks at the selected photos and writes the post (and slide order for carousels)."""
    p = f"""{_acc_block(account)}
Look at these {len(images)} photo(s) of an XB Architecture project and write a ready-to-publish post.
Project: {project or 'XB project'} · Format: {fmt} · {_lang_rule(language)}
Extra notes: {extra or '—'}
Describe what is really visible (materials, light, spaces, views) — no invented facts, no addresses or client names.
If it's a carousel, end with "ORDER:" suggesting the best photo order (1, 2, 3…) and why the first one hooks.
Return only the post text."""
    return _ask(p, 2500, images)
