from pathlib import Path
from bs4 import BeautifulSoup
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

class Parser:
    def __init__(self, html: str | Path):
        if isinstance(html, Path):
            with open(html) as f:
                html = f.read()
        self.html = html
        self.soup = BeautifulSoup(html, "html.parser")

    def parse(self) -> QGuide:
        self.course = self.get_course()

        return QGuide(
            course=self.course ,
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
        match = re.match(
            r"Feedback for\s+(?P<title>.+?)\s+-\s+(?P<instructor>.+)",
            self.soup.text
        )

        if not match:
            raise ParseError("Could not find course and instructor information in the HTML.")
        
        title = match.group("title")
        instructor = match.group("instructor")
        subject, number = title.split(maxsplit=1)
        
        match = re.match(
            r"Table of Contents for\s+(?P<semester>.+?)\s+Term Report for Students",
            self.soup.text
        )

        if not match:
            raise ParseError(f"Could not find semester information for {title} - {instructor} in the HTML.")
        
        semester_str = match.group("semester")
        season, year = semester_str.split()

        semester: Semester = Semester(
            season=Season(season.lower()),
            year=int(year)
        )

        return Course(
            title=title,
            subject=subject,
            number=number,
            instructors=[instructor],
            semester=semester
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
        response_ratio = self._parse_percent(cell_for("RespRatio"))

        return ResponseRate(
            responded=responded,
            invited=invited,
            response_ratio=response_ratio,
        )
    
    def get_course_feedback(self) -> CourseFeedback:
        pass

    def get_instructor_feedback(self) -> InstructorFeedback:
        pass

    def get_hours_per_week(self) -> HoursPerWeek:
        pass

    def get_recommendation_strength(self) -> RecommendationStrength:
        pass

    def get_reasons_for_enrollment(self) -> ReasonsForEnrollment:
        pass

    def get_most_students_open_minded(self) -> AgreementDistribution:
        pass

    def get_comfortable_expressing_views(self) -> AgreementDistribution:
        pass

    def get_comments(self) -> list[Comment]:
        pass

    def _parse_percent(self, value: str) -> float:
        return float(value.strip().removesuffix("%")) / 100
