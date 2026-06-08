from pathlib import Path
import os
import sys
import json

import pytest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
import qguider

FIXTURES = [
    "cs50",
    "zuluaa",
    "phs2000a"
]

@pytest.mark.parametrize("name", FIXTURES)
def test_parser_fixtures(name):
    html_path = Path("tests/fixtures") / f"{name}.html"
    json_path = Path("tests/fixtures") / f"{name}.json"

    expected = json.loads(json_path.read_text())
    actual = qguider.QGuideParser(html_path).parse().model_dump(mode="json")

    assert actual == expected

def dump_json_fixtures():
    for name in FIXTURES:
        html_path = Path("tests/fixtures") / f"{name}.html"
        json_path = Path("tests/fixtures") / f"{name}.json"

        qguide = qguider.QGuideParser(html_path).parse()

        json_path.write_text(
            qguide.model_dump_json(indent=2),
            encoding="utf-8",
        )
    
if __name__ == "__main__":
    dump_json_fixtures()