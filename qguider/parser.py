from pathlib import Path
from bs4 import BeautifulSoup, Tag
import re

from .models import *

class ParseError(Exception):
    def __init__(self, *args):
        super().__init__(*args)
        self.args = args

        if len(args) == 1 and isinstance(args[0], str):
            self.message = args[0]
        elif len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], Course):
            self.message = f"Could not parse the {args[0]} " \
                f"for {args[1].title} - {args[1].instructors[0]} " \
                f"({args[1].semester.season} {args[1].semester.year}) " \
                f"in the HTML."
        else:
            raise ValueError("Invalid arguments for ParseError")

class QGuideParser:
    def __init__(self, html: str | Path):
        if isinstance(html, Path):
            with open(html) as f:
                html = f.read()
        self.html = html
        self.soup = BeautifulSoup(html, "html.parser")

    def parse(self) -> QGuide:
        self.course = self.get_course()

        return QGuide(
            course=self.course,
            response_rate=self.get_response_rate(),
            course_feedback=self.get_course_feedback(),
            instructor_feedback=self.get_instructor_feedback(),
            hours_per_week=self.get_hours_per_week(),
            recommendation_strength=self.get_recommendation_strength(),
            reasons_for_enrollment=self.get_reasons_for_enrollment(),
            most_students_open_minded=self.get_most_students_open_minded(),
            comfortable_expressing_views=self.get_comfortable_expressing_views(),
            comments=self.get_comments()
        )
    
    def get_course(self) -> Course:
        page_text = _clean(self.soup.get_text(" ", strip=True))

        match = re.search(
            r"Feedback for\s+(?P<title>[A-Z]+(?:\s+[A-Z]+)*\s+\S+)\s+-\s+(?P<instructor>.+?)(?:\s+<br>|\s+\(click|\s+Table of Contents)",
            page_text,
        )

        if not match:
            raise ParseError("Could not find course and instructor information in the HTML.")

        title = _clean(match.group("title"))
        instructor = _clean(match.group("instructor"))

        subject, number = title.split(maxsplit=1)

        semester_match = re.search(
            r"Table of Contents for\s+(?P<season>Winter|Spring|Summer|Fall)\s+(?P<year>\d{4})\s+Term Report for Students",
            page_text,
        )

        if not semester_match:
            raise ParseError(
                f"Could not find semester information for {title} - {instructor} in the HTML."
            )

        semester = Semester(
            season=Season(semester_match.group("season")),
            year=int(semester_match.group("year")),
        )

        return Course(
            title=title,
            subject=subject,
            number=number,
            instructors=[instructor],
            semester=semester,
        )
    
    def get_response_rate(self) -> ResponseRate:
        caption = self.soup.find(
            "caption",
            string=lambda s: s and "Table for Course Response Rate" in s
        )

        if not caption:
            raise ParseError("response rate", self.course)
        
        table = caption.find_parent("table")

        if not table:
            raise ParseError("parent table for response rate", self.course)
        

        def cell_for(row_id: str) -> str:
            row_header = table.find(id=row_id)

            if not row_header:
                raise ParseError(f"Could not find response rate row: {row_id}")

            cell = row_header.find_next_sibling("td")

            if not cell:
                raise ParseError(f"Could not find value cell for response rate row: {row_id}")

            return cell.get_text(strip=True)

        responded = int(cell_for("RespCount"))
        invited = int(cell_for("InvitedCount"))
        response_ratio = _pct(cell_for("RespRatio"))

        return ResponseRate(
            responded=responded,
            invited=invited,
            response_ratio=response_ratio,
        )
    
    def _report_block(self, title_contains: str) -> Tag:
        title_contains = _clean(title_contains).lower()

        for header in self.soup.find_all(["h3", "h4"]):
            header_text = _clean(header.get_text(" ", strip=True)).lower()

            if title_contains in header_text:
                block = header.find_parent("div", class_="report-block")

                if not block:
                    raise ParseError(
                        f"Could not find parent report block for: {title_contains}"
                    )

                return block

        raise ParseError(f"Could not find report block: {title_contains}")
    
    def _maybe_report_block(self, title_contains: str) -> Tag | None:
        try:
            return self._report_block(title_contains)
        except ParseError:
            return None

    def _likert_from_row(self, row: Tag) -> LikertDistribution:
        cells = [_clean(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]

        return LikertDistribution(
            count=_int(cells[1]),
            excellent=_pct(cells[2]),
            very_good=_pct(cells[3]),
            good=_pct(cells[4]),
            fair=_pct(cells[5]),
            unsatisfactory=_pct(cells[6]),
            course_mean=_float(cells[7]),
            fas_mean=_float(cells[8]),
        )

    def _likert_rows_by_question(self, block: Tag) -> dict[str, LikertDistribution]:
        table = block.find("table")
        if not table:
            raise ParseError("Could not find Likert table.")

        out = {}

        for row in table.select("tbody tr"):
            cells = row.find_all(["th", "td"])
            if not cells:
                continue

            question = _clean(cells[0].get_text(" ", strip=True))
            out[question] = self._likert_from_row(row)

        return out

    def _stats_from_table(self, table: Tag) -> dict[str, str]:
        stats = {}

        for row in table.select("tbody tr"):
            cells = [_clean(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]
            if len(cells) >= 2:
                stats[cells[0]] = cells[1]

        return stats

    def _frequency_table(self, block: Tag) -> Tag:
        tables = block.find_all("table")

        for table in tables:
            caption = table.find("caption")
            caption_text = _clean(caption.get_text(" ", strip=True)) if caption else ""
            if "Statistics" not in caption_text:
                return table

        raise ParseError("Could not find frequency table.")

    def _statistics_table(self, block: Tag) -> Tag:
        tables = block.find_all("table")

        for table in tables:
            caption = table.find("caption")
            caption_text = _clean(caption.get_text(" ", strip=True)) if caption else ""
            if "Statistics" in caption_text:
                return table

        raise ParseError("Could not find statistics table.")

    def get_course_feedback(self) -> CourseFeedback:
        chart_block = self._report_block("Course Feedback for")
        table_block = self._report_block("Course General Questions")

        rows = self._likert_rows_by_question(table_block)

        return CourseFeedback(
            chart=_chart_from_block(chart_block),
            overall=rows.get("Evaluate the course overall."),
            materials=rows.get("Course materials (readings, audio-visual materials, textbooks, lab manuals, website, etc.)"),
            assignments=rows.get("Assignments (exams, essays, problem sets, language homework, etc.)"),
            feedback=rows.get("Feedback you received on work you produced in this course"),
            section=rows.get("Section component of the course"),
        )

    def get_instructor_feedback(self) -> InstructorFeedback:
        chart_block = self._maybe_report_block("Instructor Feedback for")
        table_block = self._maybe_report_block("General Instructor Questions")

        if chart_block is None or table_block is None:
            return None

        rows = self._likert_rows_by_question(table_block)

        return InstructorFeedback(
            chart=_chart_from_block(chart_block),
            instructor=self.course.instructors[0],
            overall=rows.get("Evaluate your Instructor overall."),
            effective_lectures=rows.get("Gives effective lectures or presentations, if applicable"),
            accessible_outside_class=rows.get("Is accessible outside of class (including after class, office hours, e-mail, etc.)"),
            generates_enthusiasm=rows.get("Generates enthusiasm for the subject matter"),
            facilitates_discussion=rows.get("Facilitates discussion and encourages participation"),
            useful_feedback=rows.get("Gives useful feedback on assignments"),
            returned_assignments_timely=rows.get("Returns assignments in a timely fashion"),
        )

    def get_hours_per_week(self) -> HoursPerWeek:
        block = self._report_block("how many hours per week")
        table = self._statistics_table(block)
        stats = self._stats_from_table(table)

        summary_stats = SummaryStatistics(
            response_ratio=_pct(stats["Response Ratio"]),
            mean=_float(stats["Mean"]),
            median=_float(stats["Median"]),
            stddev=_float(stats["Standard Deviation"]),
        )

        return HoursPerWeek(
            chart=_chart_from_block(block),
            responses=_int(stats["Response Count"]),
            summary_stats=summary_stats,
        )

    def get_recommendation_strength(self) -> RecommendationStrength:
        block = self._report_block("How strongly would you recommend this course")

        freq_table = self._frequency_table(block)
        stats_table = self._statistics_table(block)

        rows = {}

        for row in freq_table.select("tbody tr"):
            label = _clean(row.find("th").get_text(" ", strip=True))
            rows[label] = _score_distribution_from_row(row)

        stats = self._stats_from_table(stats_table)

        summary_stats = SummaryStatistics(
            response_ratio=_pct(stats["Response Ratio"]),
            mean=_float(stats["Mean"]),
            median=_float(stats["Median"]),
            stddev=_float(stats["Standard Deviation"]),
        )

        return RecommendationStrength(
            chart=_chart_from_block(block),
            with_enthusiasm=rows.get("Recommend with Enthusiasm"),
            likely=rows.get("Likely to Recommend"),
            with_reservations=rows.get("Recommend with Reservations"),
            unlikely=rows.get("Unlikely to Recommend"),
            definitely_not=rows.get("Definitely not Recommend"),
            summary_stats=summary_stats,
        )

    def get_reasons_for_enrollment(self) -> ReasonsForEnrollment:
        block = self._report_block("reason(s) for enrolling")
        table = block.find("table")

        if not table:
            raise ParseError("Could not find reasons for enrollment table.")

        rows = {}

        for row in table.select("tbody tr"):
            cells = [_clean(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]
            if len(cells) >= 2:
                rows[cells[0]] = _int(cells[1])

        return ReasonsForEnrollment(
            elective=rows.get("Elective"),
            concentration_or_dept=rows.get("Concentration or Department Requirement"),
            secondary_or_lang_citation=rows.get("Secondary Field or Language Citation Requirement"),
            gened=rows.get("Undergraduate General Education Requirement"),
            expos=rows.get("Expository Writing Requirement"),
            foreign_lang=rows.get("Foreign Language Requirement"),
            pre_med=rows.get("Pre-Med Requirement"),
            divisional_dist=rows.get("Divisional Distribution Requirement"),
            quantitative_reasoning=rows.get("Quantitative Reasoning with Data Requirement"),
        )

    def _agreement_distribution(self, title_contains: str) -> AgreementDistribution:
        block = self._report_block(title_contains)

        freq_table = self._frequency_table(block)
        stats_table = self._statistics_table(block)

        rows = {}

        for row in freq_table.select("tbody tr"):
            label = _clean(row.find("th").get_text(" ", strip=True))
            rows[label] = _score_distribution_from_row(row)

        stats = self._stats_from_table(stats_table)

        summary_stats = SummaryStatistics(
            response_ratio=_pct(stats["Response Ratio"]),
            mean=_float(stats["Mean"]),
            median=_float(stats["Median"]),
            stddev=_float(stats["Standard Deviation"]),
        )

        return AgreementDistribution(
            chart=_chart_from_block(block),
            strongly_agree=rows.get("Strongly Agree"),
            agree=rows.get("Agree"),
            neither=rows.get("Neither Agree nor Disagree"),
            disagree=rows.get("Disagree"),
            strongly_disagree=rows.get("Strongly Disagree"),
            summary_stats=summary_stats,
        )

    def get_most_students_open_minded(self) -> AgreementDistribution:
        return self._agreement_distribution("most students listen attentively")

    def get_comfortable_expressing_views(self) -> AgreementDistribution:
        return self._agreement_distribution("comfortable expressing my views")

    def get_comments(self) -> list[Comment]:
        block = self._report_block("future students about this class")
        table = block.find("table")

        if not table:
            return []

        comments = []

        for row in table.select("tbody tr"):
            cell = row.find("td")
            if not cell:
                continue

            text = _clean(cell.get_text(" ", strip=True))

            if text:
                comments.append(Comment(text=text))

        return comments


def _clean(text: str) -> str:
    return " ".join(text.split())

def _pct(text: str) -> float:
    return float(text.strip().removesuffix("%")) / 100


def _int(text: str) -> int:
    return int(text.strip().replace(",", ""))


def _float(text: str) -> float:
    return float(text.strip())


def _chart_from_block(block: Tag) -> Chart | None:
    img = block.find("img")
    if not img or not img.get("src"):
        return None
    return Chart(path=img["src"])


def _score_distribution_from_row(row: Tag) -> ScoreDistribution:
    cells = [_clean(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]
    return ScoreDistribution(
        score=_int(cells[1]),
        count=_int(cells[2]),
        percentage=_pct(cells[3]),
    )

class QGuideIndexParser:
    def __init__(self, html: str | Path):
        if isinstance(html, Path):
            with open(html) as f:
                html = f.read()
        self.html = html
        self.soup = BeautifulSoup(html, "html.parser")

    

        return courses