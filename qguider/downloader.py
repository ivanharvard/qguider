import json
from pathlib import Path
from dotenv import dotenv_values
import requests

from .parser import QGuideParser

class Downloader:
    def __init__(self, query):
        self.query = query
        self.downloaded_files = []

    def download(self):
        client = self._make_client()
        

    def parse(self):
        results = []
        for file in self._downloaded_files:
            results.append(QGuideParser(file).parse())
        return results
    
    def _load_session_cookie(self, creds: str | Path) -> str:
        values = dotenv_values(creds)

        session = values.get("SESSION")
        if not session:
            raise ValueError(f"Missing SESSION key in {creds}")

        return session
    
    def _make_client(self) -> requests.Session:
        session_cookie = self._load_session_cookie(self.query._creds)

        client = requests.Session()
        client.cookies.set("SESSION", session_cookie)

        return client