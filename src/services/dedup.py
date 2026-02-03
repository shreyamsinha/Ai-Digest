from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.models import Embedding, Item
from src.services.ollama_client import OllamaClient
from src.services.vector_index import build_index, save_index, load_index, search


def _pack(vec: list[float]) -> bytes:
    return np.asarray(vec, dtype="float32").tobytes()


def _unpack(blob: bytes) -> list[float]:
    return np.frombuffer(blob, dtype="float32").tolist()


def embed_text(item: Item) -> str:
    # Keep it short -> faster embeddings, still good signal
    return f"{item.title}\n{item.url}\n{(item.text or '')[:600]}"


def ensure_item_embedding(session: Session, item: Item) -> None:
    exists = session.query(Embedding).filter_by(item_id=item.id).first()
    if exists:
        return
    c = OllamaClient()
    vec = c.embed(embed_text(item))
    session.add(
        Embedding(
            item_id=item.id,
            dim=len(vec),
            vector=_pack(vec),
        )
    )


def rebuild_faiss_index_from_db(session: Session) -> None:
    rows = session.query(Embedding).all()
    if not rows:
        return
    vectors = [_unpack(r.vector) for r in rows]
    ids = [r.item_id for r in rows]
    index, ids_np = build_index(vectors, ids)
    if index is not None:
        save_index(index, ids_np)


def is_semantic_duplicate(session: Session, item: Item) -> tuple[bool, int | None, float | None]:
    """
    Returns: (is_duplicate, nearest_item_id, similarity)
    """
    s = get_settings()
    index, ids_np = load_index()
    if index is None:
        return (False, None, None)

    c = OllamaClient()
    q = c.embed(embed_text(item))
    hits = search(index, ids_np, q, k=5)
    if not hits:
        return (False, None, None)

    nearest_id, sim = hits[0]
    if nearest_id != item.id and sim >= s.dedup_sim_threshold:
        return (True, nearest_id, sim)

    return (False, nearest_id, sim)
