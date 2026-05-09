import pytest
from unittest.mock import AsyncMock, patch
from lemonade.pipeline.rank import rank_clusters
from lemonade.pipeline.cluster import Cluster
from lemonade.llm.client import LLMClient, LLMResponse

@pytest.mark.asyncio
async def test_rank_clusters():
    clusters = [
        Cluster(id="c1", title="Story A", text="Text A"),
        Cluster(id="c2", title="Story B", text="Text B"),
    ]
    mock_result = {"ranked": [{"cluster_id": "c1", "score": 25, "reason": "important"}]}
    client = LLMClient()
    with patch.object(client, "complete_json", new_callable=AsyncMock, return_value=(mock_result, LLMResponse(content="", model="test"))):
        ranked, resp = await rank_clusters(clusters, max_stories=1, client=client)
        assert len(ranked) == 1
        assert ranked[0]["cluster_id"] == "c1"


import pytest as _pytest
from unittest.mock import AsyncMock as _AsyncMock, patch as _patch
from lemonade.llm.client import LLMResponse as _LLMResp
from lemonade.pipeline.rank import rank_clusters as _rank
from lemonade.pipeline.cluster import Cluster as _Cluster


@_pytest.mark.asyncio
async def test_rank_passes_source_count_and_types_to_prompt():
    """Cluster size + source-type breadth is the popularity signal — make
    sure it ends up in the prompt the ranker sees."""
    clusters = [
        _Cluster(
            id="c1", title="A", text="x",
            item_ids=["i1", "i2", "i3"],
            sources=[
                {"type": "rss"}, {"type": "rss"}, {"type": "youtube"},
            ],
        ),
    ]
    captured = {}

    async def fake_complete_json(prompt, model=None, system=None, **_):
        captured["prompt"] = prompt
        return ({"ranked": []}, _LLMResp(content="", model="t"))

    from lemonade.llm.client import LLMClient
    client = LLMClient()
    with _patch.object(client, "complete_json", side_effect=fake_complete_json):
        await _rank(clusters, max_stories=5, client=client)

    assert "rss+youtube" in captured["prompt"]
    assert "(3x)" in captured["prompt"]
