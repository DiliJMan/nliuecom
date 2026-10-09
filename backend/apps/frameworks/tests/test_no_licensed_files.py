"""A safety net: framework sources that are licensed or no-derivatives must never be committed."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
BLOCKED = {".pdf", ".xlsx", ".xls", ".docx", ".epub"}


@pytest.mark.skipif(
    shutil.which("git") is None or not (REPO / ".git").exists(), reason="needs a git checkout"
)
def test_no_pdf_or_spreadsheet_is_tracked():
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    offenders = [name for name in tracked if Path(name).suffix.lower() in BLOCKED]
    assert offenders == [], f"Licensed sources must stay out of the repository: {offenders}"
