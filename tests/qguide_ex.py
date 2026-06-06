import json
import os
import sys
from pathlib import Path

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
from qguider.models import *


cs50_parsed = json.loads(Path("cs50_parsed.json").read_text())