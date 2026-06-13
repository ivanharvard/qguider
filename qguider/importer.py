from pathlib import Path
import json
from .models import QGuide
from .agg import QGuideSet


def from_json(qguide_json: str | Path) -> QGuideSet:
    if isinstance(qguide_json, str):
        qguide_json = Path(qguide_json)

    with open(qguide_json, "r", encoding="utf-8") as f:
        qguides_data = json.load(f)

    return QGuideSet([QGuide.model_validate(d) for d in qguides_data])