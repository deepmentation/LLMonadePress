import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from lemonade.render.typst_runner import render_pdf
from lemonade.render.profiles import DeviceProfile, PageConfig

@pytest.fixture
def sample_profile():
    return DeviceProfile(
        id="test",
        display_name="Test",
        page=PageConfig(width_mm=100, height_mm=150),
    )

@pytest.fixture
def sample_edition():
    return {
        "edition_date": "2026-05-08",
        "lead_story": {"headline": "Test", "body": "Body"},
        "sections": [],
    }

def test_render_pdf_calls_typst(sample_profile, sample_edition, tmp_path):
    mock_result = MagicMock(returncode=0, stderr="", stdout="")
    template = tmp_path / "newspaper.typ"
    template.touch()
    with patch("lemonade.render.typst_runner.subprocess.run", return_value=mock_result) as mock_run:
        render_pdf(sample_edition, sample_profile, tmp_path / "out.pdf", template=template)
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][0] == "typst"

def test_render_pdf_raises_on_failure(sample_profile, sample_edition, tmp_path):
    mock_result = MagicMock(returncode=1, stderr="error", stdout="")
    template = tmp_path / "newspaper.typ"
    template.touch()
    with patch("lemonade.render.typst_runner.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Typst compilation failed"):
            render_pdf(sample_edition, sample_profile, tmp_path / "out.pdf", template=template)
