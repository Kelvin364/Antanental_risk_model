"""The submission files: report PDF, package script and video outline."""

import importlib.util
import re

import pytest


def _script(root, name):
    spec = importlib.util.spec_from_file_location(name, root / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_report_pdf_is_a4_and_at_most_five_pages(root):
    pypdf = pytest.importorskip("pypdf")
    reader = pypdf.PdfReader(root / "docs" / "Technical-Report.pdf")
    assert 1 <= len(reader.pages) <= 5
    box = reader.pages[0].mediabox
    assert abs(float(box.width) - 595.3) < 1 and abs(float(box.height) - 841.9) < 2
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


def test_video_outline_fits_eight_to_twelve_minutes(root):
    text = (root / "docs" / "VIDEO_SCRIPT.md").read_text()
    ends = [int(m) * 60 + int(s) for m, s in re.findall(r"to (\d+):(\d\d) \|", text)]
    assert 8 * 60 <= max(ends) <= 12 * 60
    for part in "ABCDE":
        assert f"### Part {part}" in text
