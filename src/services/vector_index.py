from __future__ import annotations

import os
from typing import Iterable

import numpy as np

INDEX_PATH = "data/faiss.index"
META_PATH = "data/faiss_ids.npy"


def _to_f32(vec: Iterable[float]) -> np.ndarray:
    return np.asarray(list(vec), dtype="float32")


def _normalize_rows(X: np.ndarray) -> np.ndarray:
    # cosine similarity => normalize vectors to unit length and use dot product
    norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
    return X / norms


def save_index(index, ids: np.ndarray) -> None:
    import faiss

    os.makedirs("data", exist_ok=True)
    faiss.write_index(index, INDEX_PATH)
    np.save(META_PATH, ids)


def load_index():
    import faiss

    if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
        return None, None
    index = faiss.read_index(INDEX_PATH)
    ids = np.load(META_PATH)
    return index, ids


def build_index(vectors: list[list[float]], ids: list[int]):
    """
    Build an IndexFlatIP (inner product) over L2-normalized vectors => cosine similarity.
    """
    import faiss

    if not vectors:
        return None, None

    X = np.vstack([_to_f32(v) for v in vectors])
    X = _normalize_rows(X)
    dim = X.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(X)

    ids_np = np.asarray(ids, dtype="int64")
    return index, ids_np


def search(index, ids_np: np.ndarray, query_vec: list[float], k: int = 5) -> list[tuple[int, float]]:
    """
    Returns list of (item_id, similarity) sorted by similarity desc.
    Similarity is cosine similarity in [-1, 1] typically.
    """
    if index is None or ids_np is None:
        return []

    q = _to_f32(query_vec).reshape(1, -1)
    q = _normalize_rows(q)

    scores, idxs = index.search(q, k)

    out: list[tuple[int, float]] = []
    for score, i in zip(scores[0], idxs[0]):
        if i == -1:
            continue
        out.append((int(ids_np[i]), float(score)))
    return out
