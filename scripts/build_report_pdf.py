"""Convert docs/Technical-Report.md to docs/Technical-Report.pdf.

Usage: ``python scripts/build_report_pdf.py`` (needs ``make browsers`` once).
The Markdown is converted to HTML with mistune and printed by Chromium on A4
in Times New Roman 11 point, with section headings numbered by the style
sheet. The script prints the page count and exits with status 1 when the
PDF is longer than five pages, the limit set by the assignment.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import mistune
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "Technical-Report.md"
TARGET = ROOT / "docs" / "Technical-Report.pdf"
MAX_PAGES = 5
STYLE = """
@page { size: A4; margin: 20mm 18mm 18mm 18mm; }
body { font-family: "Times New Roman", Times, serif; font-size: 11pt; line-height: 1.25; }
body { counter-reset: h2; }
h1 { font-size: 15pt; margin: 0 0 6pt; }
h2 { font-size: 12.5pt; margin: 12pt 0 4pt; counter-reset: h3; }
h3 { font-size: 11pt; margin: 8pt 0 3pt; }
h2::before { counter-increment: h2; content: counter(h2) ". "; }
h3::before { counter-increment: h3; content: counter(h2) "." counter(h3) " "; }
p, li { margin: 0 0 5pt; text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 8pt; break-inside: auto; }
th, td { border: 0.5pt solid #777; padding: 2pt 4pt; vertical-align: top; text-align: left; }
th { background: #eee; }
tr { break-inside: avoid; }
code { font-family: "Courier New", monospace; font-size: 9.5pt; }
a { color: inherit; text-decoration: none; }
"""
FOOTER = (
    '<div style="font-family: Times New Roman; font-size: 9pt; width: 100%; '
    'text-align: center;"><span class="pageNumber"></span> of <span class="totalPages">'
    "</span></div>"
)


def to_html(markdown: str) -> str:
    """Report HTML, with typed heading numbers removed so the style sheet numbers them."""
    markdown = re.sub(r"^(#{2,3}) \d+(?:\.\d+)*\.? ", r"\1 ", markdown, flags=re.MULTILINE)
    body = mistune.create_markdown(plugins=["table", "strikethrough"])(markdown)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<style>{STYLE}</style></head><body>{body}</body></html>"
    )


def print_pdf(html: str, target: Path) -> None:
    with sync_playwright() as session:
        browser = session.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.pdf(
            path=str(target),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=FOOTER,
            margin={"top": "20mm", "bottom": "18mm", "left": "18mm", "right": "18mm"},
        )
        browser.close()


def main() -> int:
    print_pdf(to_html(SOURCE.read_text()), TARGET)
    pages = len(PdfReader(TARGET).pages)
    print(f"{TARGET.relative_to(ROOT)}: {pages} pages (limit {MAX_PAGES})")
    if pages > MAX_PAGES:
        print(f"FAIL: the report is {pages - MAX_PAGES} pages over the limit")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
