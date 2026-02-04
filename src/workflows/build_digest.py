from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.database import get_engine
from src.db.models import Evaluation, Item


@dataclass
class DigestRow:
    title: str
    url: str
    score: int | None
    payload: dict
    metadata: dict
    summary: str


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def build_digest_for_persona(persona: str, out_dir: str = "out") -> dict:
    """
    Build digest artifacts for a persona from evaluations with decision == 'keep'.
    Writes both JSON + Markdown.
    Returns summary stats.
    """
    engine = get_engine()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ✅ Only include items from the last TIME_WINDOW_HOURS
    s = get_settings()
    cutoff = datetime.utcnow() - timedelta(hours=s.time_window_hours)

    # 1) Load kept rows for this persona within time window
    with Session(engine) as session:
        rows = (
            session.query(Evaluation, Item)
            .join(Item, Item.id == Evaluation.item_id)
            .filter(Evaluation.persona == persona)
            .filter(Evaluation.decision == "keep")
            .filter(Item.created_at >= cutoff)
            .order_by(Evaluation.score.desc().nullslast(), Evaluation.created_at.desc())
            .all()
        )

    # 2) Build digest rows (add summary + metadata)
    digest_rows: list[DigestRow] = []
    for ev, it in rows:
        payload = ev.payload_json or {}
        metadata = it.metadata_json or {}

        # ✅ Summary (NO extra model call)
        # Prefer payload["summary"] if you add it later in evaluator schema.
        # For now, fallback to good signals from existing fields.
        if persona == "GENAI_NEWS":
            summary = payload.get("summary") or payload.get("topic") or ""
        else:
            summary = payload.get("summary") or payload.get("solution_summary") or ""

        summary = str(summary).strip()

        digest_rows.append(
            DigestRow(
                title=it.title,
                url=it.url,
                score=ev.score,
                payload=payload,
                metadata=metadata,
                summary=summary,
            )
        )

    date_s = _today_str()
    slug = persona.lower()

    # 3) JSON output (includes summary + metadata for Telegram)
    json_path = out / f"{slug}_{date_s}.json"
    json_data = {
        "persona": persona,
        "date": date_s,
        "window_hours": s.time_window_hours,
        "cutoff_utc": cutoff.isoformat(timespec="seconds"),
        "count": len(digest_rows),
        "items": [
            {
                "title": r.title,
                "url": r.url,
                "score": r.score,
                "summary": r.summary,         # ✅ NEW
                "evaluation": r.payload,
                "metadata": r.metadata,       # ✅ NEW
            }
            for r in digest_rows
        ],
    }
    json_path.write_text(
        json.dumps(json_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4) Markdown output (also show HN points/comments if present)
    md_path = out / f"{slug}_{date_s}.md"
    lines: list[str] = []
    lines.append(f"# {persona} Digest — {date_s}\n")
    lines.append(f"_Window: last {s.time_window_hours} hours_\n\n")

    if not digest_rows:
        lines.append("_No items kept today._\n")
    else:
        for i, r in enumerate(digest_rows, start=1):
            lines.append(f"## {i}. {r.title}\n")
            lines.append(f"- Link: {r.url}\n")
            if r.score is not None:
                lines.append(f"- Score: {r.score}\n")

            if r.summary:
                lines.append(f"- Summary: {r.summary}\n")

            # Engagement badges (HN points/comments) if present in metadata_json
            points = r.metadata.get("score") or r.metadata.get("points")
            comments = r.metadata.get("comments") or r.metadata.get("descendants")
            if points is not None or comments is not None:
                badge_parts = []
                if points is not None:
                    badge_parts.append(f"⬆️ {points}")
                if comments is not None:
                    badge_parts.append(f"💬 {comments}")
                lines.append(f"- Engagement: {' | '.join(badge_parts)}\n")

            # Persona-specific fields
            if persona == "GENAI_NEWS":
                lines.append(f"- Topic: {r.payload.get('topic','')}\n")
                lines.append(f"- Why it matters: {r.payload.get('why_it_matters','')}\n")
                lines.append(f"- Audience: {r.payload.get('target_audience','')}\n")
            elif persona == "PRODUCT_IDEAS":
                lines.append(f"- Idea type: {r.payload.get('idea_type','')}\n")
                lines.append(f"- Problem: {r.payload.get('problem_statement','')}\n")
                lines.append(f"- Solution: {r.payload.get('solution_summary','')}\n")
                lines.append(f"- Maturity: {r.payload.get('maturity_level','')}\n")

            lines.append("\n---\n")

    md_path.write_text("".join(lines), encoding="utf-8")

    return {
        "persona": persona,
        "kept": len(digest_rows),
        "json_path": str(json_path),
        "md_path": str(md_path),
    }
