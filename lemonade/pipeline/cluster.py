from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Cluster:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    text: str = ""
    source_type: str = ""
    urls: list[str] = field(default_factory=list)
    item_ids: list[str] = field(default_factory=list)
    embedding: list[float] | None = None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    dot = np.dot(a_arr, b_arr)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def cluster_items(
    items: list[dict],
    threshold: float = 0.85,
) -> list[Cluster]:
    """Cluster items by embedding similarity. Each item dict must have 'embedding', 'title', 'text', 'url', 'id', 'source_type'."""
    if not items:
        return []

    clusters: list[Cluster] = []
    assigned = set()

    for i, item in enumerate(items):
        if i in assigned:
            continue
        cluster = Cluster(
            title=item.get("title", ""),
            text=item.get("text", ""),
            source_type=item.get("source_type", ""),
            urls=[item["url"]],
            item_ids=[item["id"]],
            embedding=item.get("embedding"),
        )
        assigned.add(i)

        if cluster.embedding:
            for j, other in enumerate(items):
                if j in assigned or not other.get("embedding"):
                    continue
                sim = cosine_similarity(cluster.embedding, other["embedding"])
                if sim >= threshold:
                    cluster.urls.append(other["url"])
                    cluster.item_ids.append(other["id"])
                    if len(other.get("text", "")) > len(cluster.text):
                        cluster.text = other["text"]
                        cluster.title = other.get("title", cluster.title)
                    assigned.add(j)

        clusters.append(cluster)

    return clusters
