from __future__ import annotations

import time
import requests
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from src.db.database import get_engine
from src.db.models import Item


HN_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


def fetch_top_story_ids(limit: int = 50) -> list[int]:
    r = requests.get(HN_TOP_STORIES, timeout=20)
    r.raise_for_status()
    return r.json()[:limit]


def fetch_story(story_id: int) -> dict | None:
    r = requests.get(HN_ITEM.format(id=story_id), timeout=20)
    r.raise_for_status()
    data = r.json()

    if not data or data.get("type") != "story":
        return None

    if "url" not in data:
        return None

    return data


def ingest_hackernews(limit: int = 30) -> int:
    engine = get_engine()
    inserted = 0

    ids = fetch_top_story_ids(limit)

    with Session(engine) as session:
        for sid in ids:
            data = fetch_story(sid)
            if not data:
                continue

            item = Item(
                source="hackernews",
                url=data["url"],
                title=data.get("title", ""),
                text=data.get("text"),
                published_at=datetime.fromtimestamp(
                    data["time"], tz=timezone.utc
                ),
                metadata_json={
                    "hn_id": data["id"],
                    "score": data.get("score"),
                    "by": data.get("by"),
                    "descendants": data.get("descendants"),
                },
            )

            # avoid duplicates (URL is unique)
            session.add(item)
            try:
                session.commit()
                inserted += 1
            except Exception:
                session.rollback()

            time.sleep(0.2)  # be polite to HN

    return inserted
