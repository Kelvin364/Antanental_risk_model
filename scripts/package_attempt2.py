"""Write the attempt two submission zip.

Usage: ``python scripts/package_attempt2.py VIDEO [--out dist/attempt2.zip]``.
The zip holds every file in ``git archive HEAD``, the built report PDF, the
video file given as the argument and a RUN.md with the install, test and
serve commands, all under one top level folder. Uncommitted changes are not
included, so the script warns when the working tree is not clean. It prints
the zip size and the listing.
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = "antenatal-caseload-attempt2"
# The submitted technical report, committed in docs/ under the name it was exported with.
PDF = next(
    iter(sorted((ROOT / "docs").glob("Technical Report_*.pdf"))), ROOT / "docs" / "report.pdf"
)
PDF_NAME = f"docs/{PDF.name}"
RUN = """# Running the submission

Python 3.12 and make are needed. From this folder:

```
make install      # a .venv with the dependencies and the antenatal package
make test         # unit, integration and browser tests with coverage
make serve        # the API and interface at http://127.0.0.1:8000/
```

The browser tests are skipped unless `make browsers` has been run once.
`python -m antenatal derive-cohort` prints the cohort flow counts.
The report is the PDF in `docs/` and the video is in `video/`.
"""


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def build(video: Path, out: Path) -> Path:
    if not PDF.exists():
        raise SystemExit("The technical report PDF is missing from docs/")
    if not video.is_file():
        raise SystemExit(f"video file not found: {video}")
    if _git("status", "--porcelain", "--untracked-files=no").strip():
        print("warning: uncommitted changes are not in the zip", file=sys.stderr)
    tar = io.BytesIO(_git("archive", "--format=tar", "HEAD"))
    out.parent.mkdir(parents=True, exist_ok=True)
    with (
        tarfile.open(fileobj=tar) as archive,
        zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as bundle,
    ):
        for member in archive.getmembers():
            if member.isfile() and member.name != PDF_NAME:
                info = zipfile.ZipInfo(f"{FOLDER}/{member.name}", _date(member))
                info.external_attr = (member.mode & 0o777) << 16
                bundle.writestr(info, archive.extractfile(member).read(), zipfile.ZIP_DEFLATED)
        bundle.write(PDF, f"{FOLDER}/{PDF_NAME}")
        bundle.write(video, f"{FOLDER}/video/{video.name}")
        bundle.writestr(f"{FOLDER}/RUN.md", RUN)
    return out


def _date(member: tarfile.TarInfo) -> tuple[int, ...]:
    return datetime.fromtimestamp(member.mtime).timetuple()[:6]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("video", type=Path, help="the walkthrough video file")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "attempt2.zip")
    args = parser.parse_args(argv)
    out = build(args.video.resolve(), args.out.resolve())
    with zipfile.ZipFile(out) as bundle:
        for info in bundle.infolist():
            print(f"{info.file_size:>12,}  {info.filename}")
        print(f"{len(bundle.infolist())} files")
    print(f"{out}: {out.stat().st_size / 1024**2:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
