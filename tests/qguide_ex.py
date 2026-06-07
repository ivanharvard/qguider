import json
import os
import sys
from pathlib import Path


from qguider.models import *


cs50_parsed     = json.loads(Path("cs50_parsed.json").read_text())
zuluaa_parsed   = json.loads(Path("zuluaa_parsed.json").read_text())
phs2000a_parsed = json.loads(Path("phs2000a_parsed.json").read_text())