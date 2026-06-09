import re
from pathlib import Path
from dotenv import dotenv_values
import requests
from html import unescape
from bs4 import BeautifulSoup
import hashlib
import logging

from .parser import QGuideParser
from .models import QGuideListing, QGuideURLs

logger = logging.getLogger(__name__)

COURSE_RE = re.compile(
    r"""
    ^
    (?P<subject>.+?)
    \s+
    (?P<number>[A-Z0-9]+)
    -
    (?P<title>.*?)
    \s+
    (?P<section>\d+|[A-Z0-9]+)
    (?:\s+\((?P<instructor>[^)]+)\))?
    $
    """,
    re.VERBOSE,
)

class Downloader:
    BASE_URL = "https://qreports.fas.harvard.edu/browse/index"

    def __init__(self, query):
        self.query = query
        self.downloaded_files = []

    def download(self):
        client = self._make_client()
        qguide_urls = []
        for school in self.query._schools:
            for semester in self.query._semesters:
                url = self.BASE_URL.format(
                    schoolCode=school.code, 
                    semester=str(semester)
                )
                logger.info(
                    f"Scraping QGuide URLs for {school.code} {semester}..."
                )
                logger.debug(f"Requesting index page: {url}")
                
                response = client.get(
                    self.BASE_URL,
                    params={"school": school.code, "calTerm": str(semester)},
                )

                if response.status_code != 200:
                    raise ValueError(
                        f"Failed to download index for {school} {semester}: \
                          {response.status_code}")

                listings = self.parse_index_html(response.text)
                listings = self._filter_listings(listings)

                qguide_urls.append(QGuideURLs(semester=semester, school=school, listings=listings))

        for qguide_url in qguide_urls:
            for listing in qguide_url.listings:
                logger.info(
                    f"Downloading QGuide for {listing.course_code} \
                      ({listing.title}) @ {listing.url}..."
                )
                response = client.get(listing.url)

                if response.status_code != 200:
                    logger.warning(
                        f"Failed to download QGuide for {listing.course_code} \
                          ({listing.title}): {response.status_code}"
                    )
                    continue

                outdir = Path(self.query._outpath) / \
                            qguide_url.semester.season / \
                                str(qguide_url.semester.year) / \
                                    listing.department / \
                                        listing.subject
                outdir.mkdir(parents=True, exist_ok=True)
                
                url_hash = hashlib.sha1(listing.url.encode()).hexdigest()[:10]
                outpath = outdir / \
                    f"{listing.course_number}_{listing.section}_{url_hash}.html"

                with open(outpath, "w", encoding="utf-8") as f:
                    f.write(response.text)

                self.downloaded_files.append(outpath)

        return self

    def normalize_text(self, text: str) -> str:
        return " ".join(unescape(text).split())


    def parse_course_label(self, label: str) -> dict:
        label = self.normalize_text(label)
        match = COURSE_RE.match(label)

        if not match:
            raise ValueError(f"Could not parse course label: {label!r}")

        data = match.groupdict()
        data["course_code"] = f"{data['subject']} {data['number']}"
        return data


    def parse_index_html(self, html: str) -> list[QGuideListing]:
        soup = BeautifulSoup(html, "html.parser")
        listings: list[QGuideListing] = []

        for dept_card in soup.select("div.card.term"):
            dept_el = dept_card.select_one(".card-header b")
            if not dept_el:
                continue

            department = self.normalize_text(dept_el.get_text(" ", strip=True))

            for a in dept_card.select("a[href][id]"):
                label = self.normalize_text(a.get_text(" ", strip=True))
                parsed = self.parse_course_label(label)

                listings.append(
                    QGuideListing(
                        department=department,
                        subject=parsed["subject"],
                        course_number=parsed["number"],
                        course_code=parsed["course_code"],
                        title=parsed["title"],
                        section=parsed["section"],
                        instructor=parsed["instructor"],
                        qguide_id=a["id"],
                        url=a["href"],
                    )
                )

        return listings     

    def parse_qguide(self):
        results = []
        for file in self.downloaded_files:
            results.append(QGuideParser(file).parse())
        return results
    
    def _filter_listings(
        self,
        listings: list[QGuideListing],
    ) -> list[QGuideListing]:

        departments = set(self.query._departments or [])
        subjects = set(self.query._subjects or [])
        classes = set(self.query._classes or [])

        search_term = (
            self.query._search_term.lower()
            if self.query._search_term
            else None
        )

        filtered = []

        for listing in listings:

            if departments and listing.department not in departments:
                continue

            if subjects and listing.subject not in subjects:
                continue

            if classes and listing.course_code not in classes:
                continue

            if (
                self.query._instructor_last_name
                and (
                    not listing.instructor
                    or self.query._instructor_last_name.lower()
                    not in listing.instructor.lower()
                )
            ):
                continue

            if search_term:
                haystack = " ".join([
                    listing.department,
                    listing.subject,
                    listing.course_code,
                    listing.title,
                    listing.instructor or "",
                ]).lower()

                if search_term not in haystack:
                    continue

            filtered.append(listing)

        return filtered
    
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