from __future__ import annotations

from typing import Iterable
from src.db.models import Item
from src.config.settings import get_settings


def _contains_any(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def prefilter_items(items: Iterable[Item]) -> list[Item]:
    """
    Cheap rules: blocklist + min score + optional keyword requirement.
    """
    s = get_settings()
    kept: list[Item] = []

    for it in items:
        title = (it.title or "").strip()
        if not title:
            continue

        # blocklist check (title)
        if s.hn_blocklist and _contains_any(title, s.hn_blocklist):
            continue

        # engagement threshold (HN score stored in metadata_json)
        score = None
        try:
            score = it.metadata_json.get("score")
        except Exception:
            score = None

        if isinstance(score, int) and score < s.hn_min_score:
            continue

        # keyword requirement (optional)
        if s.hn_require_keywords and s.hn_keywords:
            hay = title
            if it.text:
                hay += " " + it.text
            if not _contains_any(hay, s.hn_keywords):
                continue

        kept.append(it)

    return kept
