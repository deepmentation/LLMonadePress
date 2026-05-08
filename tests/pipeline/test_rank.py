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
