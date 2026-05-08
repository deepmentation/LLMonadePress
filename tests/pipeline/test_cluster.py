import pytest
from lemonade.pipeline.cluster import cluster_items, cosine_similarity

def test_cosine_similarity_identical():
    assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

def test_cosine_similarity_orthogonal():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

def test_cluster_items_groups_similar():
    items = [
        {"id": "1", "title": "A", "text": "Hello", "url": "u1", "source_type": "rss", "embedding": [1, 0, 0]},
        {"id": "2", "title": "B", "text": "Hello world", "url": "u2", "source_type": "rss", "embedding": [0.99, 0.1, 0]},
        {"id": "3", "title": "C", "text": "Different", "url": "u3", "source_type": "rss", "embedding": [0, 1, 0]},
    ]
    clusters = cluster_items(items, threshold=0.85)
    assert len(clusters) == 2

def test_cluster_items_empty():
    assert cluster_items([]) == []
