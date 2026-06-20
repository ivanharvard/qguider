import dataclasses
import json
import re
from pathlib import Path
from dotenv import dotenv_values
import requests
from html import unescape
from bs4 import BeautifulSoup
import hashlib
import logging
import time
import random
from requests.exceptions import RequestException

from .parser import QGuideParser
from .models import QGuideListing, QGuideURLs
from .agg import QGuideSet

logger = logging.getLogger(__name__)

COURSE_RE = re.compile(
    r"""
    ^
    (?P<subject>.+?)
    \s+
    (?P<number>[A-Z0-9.]+)
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
        self.failed = []  # list of (listing, reason) for report_failed

    def download(
        self,
        checkpoint: bool = False,
        checkpoint_interval: int = 50,
        report_failed: bool = False,
        redownload_failed: bool = True,
        parse_failed_path: str | Path | None = "qguider_data/parse_failed.json",
        sleep_for_sec: float | tuple[float, float] = 0
    ):
        client = self._make_client()
        qguide_urls = []
        since_checkpoint = 0

        for school in self.query._schools:
            for semester in self.query._semesters:
                logger.info("Scraping QGuide URLs for %s %s...", school.code, semester)

                response = self._get_with_retries(
                    client,
                    self.BASE_URL,
                    params={"school": school.code, "calTerm": semester.to_qguide_term()},
                )

                logger.debug("Index response URL: %s", response.url)
                logger.debug("Index HTML length: %d", len(response.text))
                logger.debug("Index dept cards: %d", len(BeautifulSoup(response.text, "html.parser").select("div.card.term")))
                logger.debug("Index qguide anchors: %d", response.text.count("SelectedIDforPrint="))

                if response.status_code != 200:
                    raise ValueError(
                        f"Failed to download index for {school} {semester}: "
                        f"{response.status_code}"
                    )

                listings = self.parse_index_html(response.text)

                logger.debug("Raw listings: %d", len(listings))
                logger.debug("Query departments: %r", self.query._departments)
                logger.debug("Query subjects: %r", self.query._subjects)
                logger.debug("Query classes: %r", self.query._classes)
                logger.debug("Query instructor: %r", self.query._instructor_last_name)
                logger.debug("Query search: %r", self.query._search_term)


                listings = self._filter_listings(listings)
                listings = [dataclasses.replace(l, semester=semester) for l in listings]

                logger.info("Found %d QGuide listings after filtering.", len(listings))

                if len(listings) == 0:
                    logger.error(
                        "No listings found for %s %s. Check query parameters or SESSION cookie.",
                        school.code,
                        str(semester),
                    )

                qguide_urls.append(
                    QGuideURLs(semester=semester, school=school, listings=listings)
                )

        all_items = [
            (qguide_url, listing)
            for qguide_url in qguide_urls
            for listing in qguide_url.listings
        ]

        progress = getattr(self.query, "_progress", None)
        task_id = None        

        if progress:
            task_id = progress.add_task("Downloading QGuides", total=len(all_items))

        failed_files = set()

        if redownload_failed:
            if not parse_failed_path:
                parse_failed_path = Path(self.query._outpath) / "parse_failed.json"
            else:
                parse_failed_path = Path(parse_failed_path)

            if not parse_failed_path.exists():
                logger.warning("No parse failure file found at %s; cannot redownload failed items.", parse_failed_path)
            else:
                with open(parse_failed_path, "r", encoding="utf-8") as f:
                    failed_items = json.load(f)
                    failed_files = {item["file"] for item in failed_items}
    
        for qguide_url, listing in all_items:
            try:
                outdir = (
                    Path(self.query._outpath)
                    / str(qguide_url.semester.year)
                    / qguide_url.semester.season.value
                    / self._safe_path_part(listing.department)
                    / self._safe_path_part(listing.subject)
                )
                outdir.mkdir(parents=True, exist_ok=True)

                url_hash = hashlib.sha1(listing.url.encode()).hexdigest()[:10]
                outpath = outdir / (
                    f"{listing.course_number}_{listing.section}_{url_hash}.html"
                )

                should_redownload = str(outpath) in failed_files

                if outpath.exists() and outpath.stat().st_size > 0 and not should_redownload:
                    logger.info("Skipping existing QGuide file: %s", outpath)
                    self.downloaded_files.append((listing, outpath))
                    continue

                if should_redownload:
                    logger.info("Redownloading previously failed QGuide: %s", outpath)
                else:
                    logger.info("Downloading new QGuide file: %s", outpath)

                logger.info(
                    "Downloading QGuide for %s (%s) @ %s...",
                    listing.course_code,
                    listing.title,
                    listing.url,
                )

                self._sleep_between_requests(sleep_for_sec)

                try:
                    response = self._get_with_retries(client, listing.url)
                except RequestException as e:
                    reason = str(e)
                    logger.warning(
                        "Failed to download QGuide for %s (%s): %s",
                        listing.course_code,
                        listing.title,
                        reason,
                    )
                    if report_failed:
                        self.failed.append((listing, reason))
                    continue

                if response.status_code != 200:
                    reason = f"HTTP {response.status_code}"
                    logger.warning(
                        "Failed to download QGuide for %s (%s): %s",
                        listing.course_code,
                        listing.title,
                        reason,
                    )
                    if report_failed:
                        self.failed.append((listing, reason))
                    continue

                with open(outpath, "w", encoding="utf-8") as f:
                    f.write(response.text)

                self.downloaded_files.append((listing, outpath))
                since_checkpoint += 1

                if checkpoint and since_checkpoint >= checkpoint_interval:
                    self._save_checkpoint()
                    since_checkpoint = 0

            finally:
                if progress and task_id is not None:
                    progress.advance(task_id)

        if checkpoint:
            self._save_checkpoint()

        if report_failed and self.failed:
            self._report_failed()

        return self

    def _save_checkpoint(self) -> None:
        checkpoint_path = Path(self.query._outpath) / "checkpoint.json"

        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump([str(p) for _, p in self.downloaded_files], f, indent=2)
        logger.info("Checkpoint saved (%d files) → %s", len(self.downloaded_files), checkpoint_path)

    def _report_failed(self) -> None:
        logger.warning("Failed to download %d QGuide(s):", len(self.failed))
        for listing, reason in self.failed:
            logger.warning("  %s | %s | %s | %s", listing.course_code, listing.title, listing.url, reason)


    def _get_with_retries(
        self,
        client: requests.Session,
        url: str,
        *,
        params: dict | None = None,
        max_retries: int = 3,
        timeout: tuple[int, int] = (5, 30),
    ) -> requests.Response:
        for attempt in range(max_retries):
            try:
                response = client.get(url, params=params, timeout=timeout)

                if response.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(
                        f"Retryable status code: {response.status_code}",
                        response=response,
                    )
                
                if self._is_retryable_application_error(response):
                    raise requests.HTTPError(
                        "Application error detected in response",
                        response=response,
                    )

                return response

            except RequestException as e:
                if attempt == max_retries - 1:
                    raise

                sleep_for_sec = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "Request failed for %s: %s",
                    url,
                    e,
                )
                self._sleep_between_requests(sleep_for_sec)

        raise RuntimeError("unreachable")


    def _sleep_between_requests(self, range: float | tuple[float, float]) -> None:
        if isinstance(range, tuple):
            sleep_for = random.uniform(*range)
        else:
            sleep_for = float(range)

        logger.debug("Sleeping %.2fs before next request.", sleep_for)
        time.sleep(sleep_for)


    def _safe_path_part(self, value: str) -> str:
        return re.sub(r'[<>:"/\\|?*]+', "_", value).strip()
    
    def _is_retryable_application_error(self, response: requests.Response) -> bool:
        text = response.text.lower()
        return "an application error occurred on the server" in text


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
                href = a["href"]
                if "rpv-eng.aspx" not in href:
                    continue

                if "SelectedIDforPrint=" not in href:
                    continue

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

    def parse(self, *, skip_failed: bool = True):
        results = []
        failed = []

        progress = getattr(self.query, "_progress", None)
        task_id = None

        if progress:
            task_id = progress.add_task("Parsing QGuides", total=len(self.downloaded_files))

        for listing, file in self.downloaded_files:
            try:
                results.append(QGuideParser(file, listing=listing).parse())
            except Exception as e:
                logger.warning("Failed to parse %s: %s: %s", file, type(e).__name__, e)
                failed.append((file, type(e).__name__, str(e)))

                if not skip_failed:
                    raise
            finally:
                if progress and task_id is not None:
                    progress.advance(task_id)

        if failed:
            failed_path = Path(self.query._outpath) / "parse_failed.json"
            with open(failed_path, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "file": str(file),
                            "error_type": error_type,
                            "reason": reason,
                        }
                        for file, error_type, reason in failed
                    ],
                    f,
                    indent=2,
                )

            logger.warning("Wrote %d parse failure(s) to %s", len(failed), failed_path)

        return QGuideSet(results)
    
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