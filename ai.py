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
placeholder in brackets like [project sq ft]. No empty clichés ("dream home", "stunning").
Write like a premium architecture studio: precise, sensory, confident.
Always write the content in the language requested in each message."""


def _ask_gemini(prompt, max_tokens):
    key = get_secret("GEMINI_API_KEY")
    body = {"system_instruction": {"parts": [{"text": SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max(max_tokens, 4096)}}
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
                               "aistudio.google.com/api-keys y pegala en Secrets → GEMINI_API_KEY.")
        if r.ok:
            parts = (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()
            if text:
                return text
            last = "empty response"
        else:
            last = f"{r.status_code}: {r.text[:200]}"
    raise RuntimeError(f"Gemini error / error de Gemini — {last}")


def _ask_claude(prompt, max_tokens):
    from anthropic import Anthropic
    msg = Anthropic(api_key=get_secret("ANTHROPIC_API_KEY")).messages.create(
        model=CLAUDE_MODEL, max_tokens=max_tokens, system=SYSTEM,
        messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def _ask(prompt, max_tokens=2500):
    p = provider()
    if p == "gemini":
        return _ask_gemini(prompt, max_tokens)
    if p == "anthropic":
        return _ask_claude(prompt, max_tokens)
    raise _missing_key()


def _json(text):
    m = re.search(r"(\[.*\]|\{.*\})", text, re.S)
    if not m:
        raise ValueError("The AI did not return JSON, please try again. / La IA no devolvió JSON, probá de nuevo.")
    return json.loads(m.group(1))


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
    return _json(_ask(p, 4000))


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
Use the real projects when it makes sense (North Miami, Royal Palm, Sea Island, Coral Ridge, Surfside, Plantation Acres).
Write "title", "description" and "inspo" in {language if not language.startswith('Bilingual') else 'English'}.
Return ONLY a JSON list of objects with keys
"title" (short hook), "description" (how to execute it: shots, slides, script in 2-4 sentences),
"pillar" (exactly one of {PILLARS}), "format" (exactly one of {FORMATS}), "account" (one of {list(accounts)}),
"inspo" (which reference account inspires it and why, one sentence)."""
    return _json(_ask(p, 4000))


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
    return _json(_ask(p, 8000))


def adapt_inspo(title, summary, source, studio, accounts, language):
    """Turns a news item about another studio into a concrete XB post idea (no copying)."""
    acc_txt = ", ".join(f"{k} ({ACCOUNTS[k]['label']})" for k in accounts)
    p = f"""A reference studio just published this ({source}):
Title: {title}
Studio: {studio or 'unknown'}
Summary: {summary}

Propose ONE concrete post idea for XB Architecture inspired by the APPROACH or topic of this news
(format, angle, storytelling, innovation) — never copy it or claim their work. Connect it to XB's real
projects (North Miami, Royal Palm, Sea Island, Coral Ridge, Surfside, Plantation Acres) when it makes sense.
Possible accounts: {acc_txt}.
Write everything in {language if not language.startswith('Bilingual') else 'English'}.
Return ONLY JSON: {{"title": "...", "why": "what to borrow from the reference, 1 sentence",
"description": "how to execute it, 2-4 sentences", "caption": "a ready-to-edit caption draft",
"pillar": one of {PILLARS}, "format": one of {FORMATS}, "account": one of {list(accounts)}}}"""
    return _json(_ask(p, 2500))
