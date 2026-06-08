from pathlib import Path

from .query import Query

class QGuider:
    def __init__(self, creds: str | Path, outpath: str | Path = Path("qguider_data")):
        self._outpath = outpath
        self._creds = creds

    def query(self):
        return Query(self._creds, self._outpath)