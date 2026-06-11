from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from qguider.models import QGuide


def to_json(guides: list[QGuide], path: str | Path | None = None) -> str:
    records = [g.model_dump() for g in guides]
    output = json.dumps(records, default=str, indent=2)
    if path is not None:
        Path(path).write_text(output)
    return output


def to_dataframe(guides: list[QGuide]) -> "pd.DataFrame":
    import pandas as pd

    records = [g.model_dump() for g in guides]
    df = pd.json_normalize(records, sep=".")
    # list-valued columns (comments, course.instructors) become joined strings
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list)).any():
            df[col] = df[col].apply(
                lambda x: "; ".join(
                    str(item.get("text", item)) if isinstance(item, dict) else str(item)
                    for item in x
                ) if isinstance(x, list) else x
            )
    return df
