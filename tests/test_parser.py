from pathlib import Path

from qguide_ex import cs50_parsed
import qguider


def test_parser():
    qgdr = qguider.Parser(Path("cs50.html")).parse()
    assert qgdr.model_dump(mode="json") == cs50_parsed


