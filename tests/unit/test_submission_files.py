"""The submission files: the report PDF and the package script."""

import importlib.util

import pytest


def _script(root, name):
    spec = importlib.util.spec_from_file_location(name, root / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPORT_GLOB = "Technical Report_*.pdf"
# A4 or US Letter, in points.
PAPER = {(595.3, 841.9), (612.0, 792.0)}


def test_submitted_report_is_at_most_five_pages_in_times_new_roman(root):
    pypdf = pytest.importorskip("pypdf")
    reports = sorted((root / "docs").glob(REPORT_GLOB))
    assert len(reports) == 1, reports
    reader = pypdf.PdfReader(reports[0])
    assert 1 <= len(reader.pages) <= 5
    box = reader.pages[0].mediabox
    size = (float(box.width), float(box.height))
    assert any(abs(size[0] - w) < 1 and abs(size[1] - h) < 2 for w, h in PAPER)
    fonts = {
        f.get_object()["/BaseFont"] for p in reader.pages for f in p["/Resources"]["/Font"].values()
    }
    assert any("TimesNewRoman" in str(font) for font in fonts)


def test_report_html_numbers_headings_by_style_sheet(root):
    pytest.importorskip("mistune")
    pytest.importorskip("playwright.sync_api")
    build = _script(root, "build_report_pdf")
    html = build.to_html("# Title\n\n## 1. Scope\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n")
    assert "<h2>Scope</h2>" in html and "<table>" in html
    assert "counter(h2)" in html and "11pt" in html and "Times New Roman" in html
