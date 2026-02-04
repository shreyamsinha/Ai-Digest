from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from src.config.settings import get_settings


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


# ---------------------------
# Tags
# ---------------------------

def _slug_tag(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (s or "").strip().lower()).strip("_")
    if not s:
        return ""
    return f"#{s[:24]}"


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

    uniq: list[str] = []
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
    rest = items_sorted[min(3, max_items):]

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
            audience = ev.get("target_audience", "")

            points = md.get("score") or md.get("points")
            comments = md.get("comments") or md.get("descendants")

            tags = build_tags(title, ev, "GENAI_NEWS")

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

            if audience:
                lines.append(f"  *For:* {mdv2_escape(audience)}")

            if tags:
                lines.append(f"  *Tags:* {mdv2_escape(' '.join(tags))}")

        lines.append("")

    # Group remaining by topic
    buckets: dict[str, list[dict]] = {}
    for it in rest:
        ev = it.get("evaluation", {}) or {}
        topic = ev.get("topic") or "Other"
        buckets.setdefault(topic, []).append(it)

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

            why = ev.get("why_it_matters", "")
            audience = ev.get("target_audience", "")
            tags = build_tags(title, ev, "GENAI_NEWS")

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

            if why:
                w = str(why).strip()
                if len(w) > 140:
                    w = w[:137] + "..."
                lines.append(f"  {mdv2_escape(w)}")

            if audience:
                lines.append(f"  *For:* {mdv2_escape(audience)}")

            if tags:
                lines.append(f"  *Tags:* {mdv2_escape(' '.join(tags))}")

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

        # ✅ "Why" for product ideas (derive if missing)
        why = ev.get("why_it_matters") or ev.get("value") or ""
        if not why:
            if problem and solution:
                why = f"{problem} → {solution}"
            elif problem:
                why = problem
            elif solution:
                why = solution

        tags = build_tags(title, ev, "PRODUCT_IDEAS")

        points = md.get("score") or md.get("points")
        comments = md.get("comments") or md.get("descendants")

        badge_parts = []
        if points is not None:
            badge_parts.append(f"⬆️ {compact_int(points)}")
        if comments is not None:
            badge_parts.append(f"💬 {compact_int(comments)}")
        badge = "  •  ".join(badge_parts)

        # ✅ escape dot in MarkdownV2
        lines.append(f"*{i}\\.* {fmt_link(title, url)}")
        if badge:
            lines.append(mdv2_escape(badge))

        if idea_type:
            lines.append(f"• *Type:* {mdv2_escape(idea_type)}")

        if why:
            w = str(why).strip()
            if len(w) > 180:
                w = w[:177] + "..."
            lines.append(f"• *Why:* {mdv2_escape(w)}")

        if problem:
            p = str(problem).strip()
            if len(p) > 180:
                p = p[:177] + "..."
            lines.append(f"• *Problem:* {mdv2_escape(p)}")

        if solution:
            sol = str(solution).strip()
            if len(sol) > 220:
                sol = sol[:217] + "..."
            lines.append(f"• *Solution:* {mdv2_escape(sol)}")

        if maturity:
            lines.append(f"• *Maturity:* {mdv2_escape(maturity)}")

        if tags:
            lines.append(f"• *Tags:* {mdv2_escape(' '.join(tags))}")

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
        body_lines = [f"*{mdv2_escape(persona)}*"]
        for it in items[:max_items]:
            body_lines.append(f"• {fmt_link(it.get('title','Item'), it.get('url',''))}")
        body = "\n".join(body_lines)

    return "\n\n".join([header, body, footer]).strip()


def build_combined_telegram_text(json_paths: list[str]) -> str:
    s = get_settings()

    digests = []
    for p in json_paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        digests.append(data)

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
            body_lines = [f"*{mdv2_escape(persona)}*"]
            for it in items[:max_items]:
                body_lines.append(f"• {fmt_link(it.get('title','Item'), it.get('url',''))}")
            parts.append("\n".join(body_lines))

    return "\n\n".join([header] + parts + [footer]).strip()


# ---------------------------
# Sender
# ---------------------------

def _chunk_telegram_message(text: str, limit: int = 3900) -> list[str]:
    """
    Telegram sendMessage limit is 4096 chars.
    Use a safe lower limit (3900) and split on blank lines first.
    If still too large, split on single newlines.
    As last resort, hard split.
    """
    text = text.strip()
    if len(text) <= limit:
        return [text]

    # First: split by double newlines (best boundary between sections/items)
    blocks = text.split("\n\n")

    chunks: list[str] = []
    buf: list[str] = []
    size = 0

    def flush():
        nonlocal buf, size
        if buf:
            chunks.append("\n\n".join(buf).strip())
            buf = []
            size = 0

    for b in blocks:
        b = b.strip()
        if not b:
            continue
        add_len = len(b) + (2 if buf else 0)  # account for "\n\n"
        if size + add_len <= limit:
            buf.append(b)
            size += add_len
        else:
            # if a single block is too large, split it further by lines
            flush()
            if len(b) <= limit:
                buf.append(b)
                size = len(b)
            else:
                lines = b.split("\n")
                line_buf: list[str] = []
                line_size = 0

                def flush_lines():
                    nonlocal line_buf, line_size
                    if line_buf:
                        chunks.append("\n".join(line_buf).strip())
                        line_buf = []
                        line_size = 0

                for ln in lines:
                    ln = ln.rstrip()
                    if not ln:
                        continue
                    ln_add = len(ln) + (1 if line_buf else 0)  # account for "\n"
                    if line_size + ln_add <= limit:
                        line_buf.append(ln)
                        line_size += ln_add
                    else:
                        flush_lines()
                        if len(ln) <= limit:
                            line_buf.append(ln)
                            line_size = len(ln)
                        else:
                            # last resort: hard split
                            for i in range(0, len(ln), limit):
                                chunks.append(ln[i:i+limit])

                flush_lines()

    flush()

    # remove empties
    return [c for c in chunks if c.strip()]


def send_telegram_message(text: str) -> None:
    s = get_settings()
    if not getattr(s, "telegram_enabled", False):
        return

    token = s.telegram_bot_token
    chat_id = s.telegram_chat_id
    parse_mode = getattr(s, "telegram_parse_mode", "MarkdownV2")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # ✅ Split long messages automatically
    chunks = _chunk_telegram_message(text, limit=3900)

    for idx, chunk in enumerate(chunks, start=1):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
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
