from pathlib import Path
import json
from .models import QGuide


def from_json(qguide_json: str | Path) -> list[QGuide]:
    """
    Load a QGuide object from a JSON file.

    Args:
        qguide_json: Path to the JSON file containing the QGuide data.

    Returns:
        A list of QGuide objects.
    """
    if isinstance(qguide_json, str):
        qguide_json = Path(qguide_json)

    with open(qguide_json, "r", encoding="utf-8") as f:
        qguides_data = json.load(f)

    return [QGuide.model_validate(qguide_data) for qguide_data in qguides_data]