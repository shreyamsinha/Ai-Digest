from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.config.settings import get_settings
from urllib.parse import quote

# ---------------------------
# MarkdownV2 escaping helpers
# ---------------------------

def mdv2_escape(text: str) -> str:
    if text is None:
        return ""
    # Escape Telegram MarkdownV2 special chars
    return re.sub(r"([_\*\[\]\(\)~`>#+\-=|{}\.!])", r"\\\1", str(text))




def fmt_link(title: str, url: str) -> str:
    safe_title = mdv2_escape(title)
    # Encode URL characters that break MarkdownV2 parsing.
    # Keep : / ? & = # % . - _ ~ safe, encode everything else.
    safe_url = quote(str(url), safe=":/?&=#+%.-_~")
    return f"[{safe_title}]({safe_url})"




def compact_int(x: Any) -> str:
    try:
        n = int(x)
    except Exception:
        return ""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)

def _slug_tag(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (s or "").strip().lower()).strip("_")
    if not s:
        return ""
    # Telegram hashtags must start with # and contain only letters/digits/underscore
    return f"#{s[:24]}"  # keep short


def build_tags(title: str, ev: dict, persona: str) -> list[str]:
    tags: list[str] = []

    if persona == "GENAI_NEWS":
        topic = ev.get("topic", "")
        if topic:
            tags.append(_slug_tag(topic))

    if persona == "PRODUCT_IDEAS":
        idea_type = ev.get("idea_type", "")
        if idea_type:
            tags.append(_slug_tag(idea_type))

    # lightweight keyword tags from title
    title_l = (title or "").lower()
    common = [
        ("rag", "rag"),
        ("agent", "agents"),
        ("agents", "agents"),
        ("llm", "llm"),
        ("inference", "inference"),
        ("embedding", "embeddings"),
        ("vector", "vector_db"),
        ("eval", "evals"),
        ("finetune", "finetuning"),
        ("fine-tune", "finetuning"),
        ("openai", "openai"),
        ("anthropic", "anthropic"),
        ("gemma", "gemma"),
        ("llama", "llama"),
    ]
    for needle, tag in common:
        if needle in title_l:
            tags.append(_slug_tag(tag))

    # de-dup, keep max 5 tags
    uniq = []
    for t in tags:
        if t and t not in uniq:
            uniq.append(t)
    return uniq[:5]


# ---------------------------
# Rendering per persona
# ---------------------------

def _render_genai_news(items: list[dict], max_items: int) -> str:
    # Sort by eval score desc then HN points desc
    def key_fn(it: dict):
        score = it.get("score") or 0
        md = it.get("metadata", {}) or {}
        points = md.get("score") or md.get("points") or 0
        return (score, points)

    items_sorted = sorted(items, key=key_fn, reverse=True)

    # Top picks (first 3)
    top = items_sorted[: min(3, max_items)]
    rest = items_sorted[min(3, max_items) :]

    lines: list[str] = []
    lines.append("🧠 *GENAI NEWS*")
    lines.append("_Top technical updates worth your time_")
    lines.append("")

    if top:
        lines.append("🔥 *Top picks*")
        for it in top:
            title = it.get("title", "Untitled")
            url = it.get("url", "")
            ev = it.get("evaluation", {}) or {}
            md = it.get("metadata", {}) or {}

            why = ev.get("why_it_matters", "")
            topic = ev.get("topic", "")

            points = md.get("score") or md.get("points")
            comments = md.get("comments") or md.get("descendants")

            badge_parts = []
            if points is not None:
                badge_parts.append(f"⬆️ {compact_int(points)}")
            if comments is not None:
                badge_parts.append(f"💬 {compact_int(comments)}")
            badge = "  •  ".join(badge_parts)

            line = f"• {fmt_link(title, url)}"
            if topic:
                line += f" — _{mdv2_escape(topic)}_"
            lines.append(line)
            if badge:
                lines.append(mdv2_escape(badge))

            if why:
                w = str(why).strip()
                if len(w) > 160:
                    w = w[:157] + "..."
                lines.append(f"  {mdv2_escape(w)}")
        lines.append("")

    # Group remaining by topic
    buckets: dict[str, list[dict]] = {}
    for it in rest:
        ev = it.get("evaluation", {}) or {}
        topic = ev.get("topic") or "Other"
        buckets.setdefault(topic, []).append(it)

    # Cap total items shown (top + rest)
    remaining_budget = max_items - len(top)
    shown = 0

    for topic, group in sorted(buckets.items(), key=lambda kv: kv[0].lower()):
        if shown >= remaining_budget:
            break

        lines.append(f"📌 *{mdv2_escape(topic)}*")

        for it in group:
            if shown >= remaining_budget:
                break

            title = it.get("title", "Untitled")
            url = it.get("url", "")
            ev = it.get("evaluation", {}) or {}
            md = it.get("metadata", {}) or {}

            points = md.get("score") or md.get("points")
            comments = md.get("comments") or md.get("descendants")

            badge_parts = []
            if points is not None:
                badge_parts.append(f"⬆️ {compact_int(points)}")
            if comments is not None:
                badge_parts.append(f"💬 {compact_int(comments)}")
            badge = "  •  ".join(badge_parts)

            lines.append(f"• {fmt_link(title, url)}")
            if badge:
                lines.append(mdv2_escape(badge))

            why = ev.get("why_it_matters", "")
            if why:
                w = str(why).strip()
                if len(w) > 140:
                    w = w[:137] + "..."
                lines.append(f"  {mdv2_escape(w)}")

            shown += 1

        lines.append("")

    return "\n".join(lines).strip()



def _render_product_ideas(items: list[dict], max_items: int) -> str:
    def key_fn(it: dict):
        s = it.get("score")
        return (s is not None, s or 0)

    items = sorted(items, key=key_fn, reverse=True)[:max_items]

    lines: list[str] = []
    lines.append("💡 *PRODUCT IDEAS*")
    lines.append("_Signals, patterns, and launchable opportunities_")
    lines.append("")

    for i, it in enumerate(items, start=1):
        title = it.get("title", "Idea")
        url = it.get("url", "")
        ev = it.get("evaluation", {}) or {}
        md = it.get("metadata", {}) or {}

        idea_type = ev.get("idea_type", "")
        problem = ev.get("problem_statement", "")
        solution = ev.get("solution_summary", "")
        maturity = ev.get("maturity_level", "")

        points = md.get("score") or md.get("points")
        comments = md.get("comments") or md.get("descendants")

        badge_parts = []
        if points is not None:
            badge_parts.append(f"⬆️ {compact_int(points)}")
        if comments is not None:
            badge_parts.append(f"💬 {compact_int(comments)}")
        badge = "  •  ".join(badge_parts)

        lines.append(f"*{i}\\.* {fmt_link(title, url)}")
        if badge:
            lines.append(mdv2_escape(badge))

        if idea_type:
            lines.append(f"• *Type:* {mdv2_escape(idea_type)}")

        if problem:
            p = str(problem).strip()
            if len(p) > 180:
                p = p[:177] + "..."
            lines.append(f"• *Problem:* {mdv2_escape(p)}")

        if solution:
            s = str(solution).strip()
            if len(s) > 220:
                s = s[:217] + "..."
            lines.append(f"• *Solution:* {mdv2_escape(s)}")

        if maturity:
            lines.append(f"• *Maturity:* {mdv2_escape(maturity)}")

        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------
# Main: build from digest JSON
# ---------------------------

def build_telegram_text_from_digest_json(json_path: str) -> str:
    s = get_settings()
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))

    persona = data.get("persona", "DIGEST")
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    items = data.get("items", []) or []

    max_items = getattr(s, "telegram_max_items", 6)

    header = f"📬 *AI Digest* — {mdv2_escape(date)}"
    footer = mdv2_escape("Built locally • No external AI APIs • Have a good day ✨")

    if persona == "GENAI_NEWS":
        body = _render_genai_news(items, max_items=max_items)
    elif persona == "PRODUCT_IDEAS":
        body = _render_product_ideas(items, max_items=max_items)
    else:
        # generic fallback
        body_lines = [f"*{mdv2_escape(persona)}*"]
        for it in items[:max_items]:
            body_lines.append(f"• {fmt_link(it.get('title','Item'), it.get('url',''))}")
        body = "\n".join(body_lines)

    return "\n\n".join([header, body, footer]).strip()

def build_combined_telegram_text(json_paths: list[str]) -> str:
    """
    Combine multiple persona digests into one Telegram message.
    Expects json_paths like: ["out/genai_news_YYYY-MM-DD.json", "out/product_ideas_YYYY-MM-DD.json"]
    """
    s = get_settings()

    # Read all digests
    digests = []
    for p in json_paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        digests.append(data)

    # Prefer the date from the first digest
    date = digests[0].get("date", datetime.now().strftime("%Y-%m-%d"))

    header = "\n".join([
        "📬 *AI Digest*",
        f"📅 {mdv2_escape(date)}",
    ])

    footer = mdv2_escape("Built locally • No external AI APIs • Have a good day ✨")

    parts = []
    for d in digests:
        persona = d.get("persona", "DIGEST")
        items = d.get("items", []) or []
        max_items = getattr(s, "telegram_max_items", 6)

        if persona == "GENAI_NEWS":
            parts.append(_render_genai_news(items, max_items=max_items))
        elif persona == "PRODUCT_IDEAS":
            parts.append(_render_product_ideas(items, max_items=max_items))
        else:
            # generic fallback
            body_lines = [f"*{mdv2_escape(persona)}*"]
            for it in items[:max_items]:
                body_lines.append(f"• {fmt_link(it.get('title','Item'), it.get('url',''))}")
            parts.append("\n".join(body_lines))

    return "\n\n".join([header] + parts + [footer]).strip()



# ---------------------------
# Sender
# ---------------------------

def send_telegram_message(text: str) -> None:
    s = get_settings()
    if not getattr(s, "telegram_enabled", False):
        return

    token = s.telegram_bot_token
    chat_id = s.telegram_chat_id
    parse_mode = getattr(s, "telegram_parse_mode", "MarkdownV2")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=30)
    if not r.ok:
        try:
            print("Telegram error:", r.json())
        except Exception:
            print("Telegram error:", r.text)
    r.raise_for_status()
