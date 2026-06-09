from pathlib import Path
import requests
import pytest

import qguider


def qguide_available() -> bool:
    try:
        response = requests.get(
            "https://qreports.fas.harvard.edu",
            timeout=5,
        )
        return response.status_code < 500
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(
    not qguide_available(),
    reason="QGuide website unavailable",
)


def test_download(tmp_path):
    qgdr = qguider.QGuider(
        creds=".env",
        outpath=tmp_path,
    )

    downloader = (
        qgdr.query()
        .semesters("Spring 2025")
        .subjects("COMPSCI")
        .download()
    )

    assert len(downloader.downloaded_files) > 0

    for file in downloader.downloaded_files:
        assert Path(file).exists()
        assert Path(file).stat().st_size > 0