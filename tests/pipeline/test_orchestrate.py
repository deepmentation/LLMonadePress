from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llmonadepress.config import LLMonadePressConfig
from llmonadepress.pipeline.cluster import Cluster
from llmonadepress.pipeline.write import WrittenStory


@pytest.fixture
def basic_config(tmp_path):
    from llmonadepress.config import DeliveryConfig, FilesystemDeliveryConfig

    return LLMonadePressConfig(
        delivery=DeliveryConfig(
            filesystem=FilesystemDeliveryConfig(output_dir=str(tmp_path / "output"))
        )
    )


@pytest.fixture
def mock_clusters():
    return [
        Cluster(
            id="c1",
            title="Test Story",
            text="Some text about testing.",
            source_type="rss",
            urls=["https://example.com/1"],
            item_ids=[str(uuid.uuid4())],
            embedding=[0.1] * 1024,
        )
    ]


@pytest.fixture
def mock_stories():
    return [
        WrittenStory(
            headline="Test Headline",
            deck="A short deck",
            body="Body text here.",
            category="Tech",
            sources=[{"url": "https://example.com/1"}],
            cluster_id="c1",
        )
    ]


@patch("llmonadepress.pipeline.orchestrate.ingest", new_callable=AsyncMock)
@patch("llmonadepress.pipeline.orchestrate.cluster_items")
@patch("llmonadepress.pipeline.orchestrate.rank_clusters", new_callable=AsyncMock)
@patch("llmonadepress.pipeline.orchestrate.write_edition", new_callable=AsyncMock)
@patch("llmonadepress.pipeline.orchestrate.render_pdf")
@patch("llmonadepress.pipeline.orchestrate.load_profile")
@patch("llmonadepress.pipeline.orchestrate.get_session_factory")
def test_run_pipeline_mocked(
    mock_session_factory,
    mock_load_profile,
    mock_render_pdf,
    mock_write_edition,
    mock_rank_clusters,
    mock_cluster_items,
    mock_ingest,
    basic_config,
    mock_clusters,
    mock_stories,
):
    """Test the pipeline with all stages mocked out."""
    import asyncio

    from llmonadepress.llm.client import LLMResponse
    from llmonadepress.pipeline.orchestrate import run_pipeline

    # Setup mocks
    mock_ingest.return_value = []

    # Mock session and query results
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=mock_session)

    mock_cluster_items.return_value = mock_clusters
    mock_rank_clusters.return_value = (
        [{"cluster_id": "c1", "rank": 1}],
        LLMResponse(content="", model="test"),
    )
    mock_write_edition.return_value = (
        mock_stories,
        [LLMResponse(content="", model="test")],
    )
    mock_load_profile.return_value = MagicMock()
    mock_render_pdf.return_value = Path("/tmp/test.pdf")

    ids = asyncio.run(
        run_pipeline(basic_config, edition_date=date(2025, 1, 1), devices=["generic_a5"], deliver=False)
    )

    assert len(ids) == 1
    mock_ingest.assert_awaited_once()
    mock_cluster_items.assert_called_once()
    mock_rank_clusters.assert_awaited_once()
    mock_write_edition.assert_awaited_once()
    mock_render_pdf.assert_called_once()
