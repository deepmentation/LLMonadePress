import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from llmonadepress.render.typst_runner import render_pdf
from llmonadepress.render.profiles import DeviceProfile, PageConfig

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
    with patch("llmonadepress.render.typst_runner.subprocess.run", return_value=mock_result) as mock_run:
        render_pdf(sample_edition, sample_profile, tmp_path / "out.pdf", template=template)
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][0] == "typst"

def test_render_pdf_raises_on_failure(sample_profile, sample_edition, tmp_path):
    mock_result = MagicMock(returncode=1, stderr="error", stdout="")
    template = tmp_path / "newspaper.typ"
    template.touch()
    with patch("llmonadepress.render.typst_runner.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Typst compilation failed"):
            render_pdf(sample_edition, sample_profile, tmp_path / "out.pdf", template=template)


def test_generate_source_qrs_respects_opt_out(tmp_path):
    """If [render] qr_codes = false, no PNGs are written and no source dict
    grows a qr_filename — verifies the user's opt-out path."""
    from llmonadepress.render.typst_runner import _generate_source_qrs

    edition = {
        "render": {"qr_codes": False},
        "lead_story": {
            "headline": "h",
            "sources": [{"url": "https://example.com/a"}],
        },
        "sections": [
            {"stories": [{"sources": [{"url": "https://example.com/b"}]}]},
        ],
    }
    _generate_source_qrs(edition, tmp_path)
    assert list(tmp_path.glob("qr_*.png")) == []
    assert "qr_filename" not in edition["lead_story"]["sources"][0]
    assert "qr_filename" not in edition["sections"][0]["stories"][0]["sources"][0]


def test_generate_source_qrs_default_enabled_writes_pngs(tmp_path):
    """Default path: render = {} or missing → QRs are produced."""
    from llmonadepress.render.typst_runner import _generate_source_qrs

    edition = {
        "lead_story": {
            "headline": "h",
            "sources": [{"url": "https://example.com/a"}],
        },
        "sections": [],
    }
    _generate_source_qrs(edition, tmp_path)
    pngs = list(tmp_path.glob("qr_*.png"))
    assert len(pngs) == 1
    assert "qr_filename" in edition["lead_story"]["sources"][0]
