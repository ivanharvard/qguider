from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass

from .semester import Season, Semester, School

class ResponseRate(BaseModel):
    responded: int
    invited: int
    response_ratio: float

class Chart(BaseModel):
    path: str

class LikertDistribution(BaseModel):
    count: int
    excellent: float | None
    very_good: float | None
    good: float | None
    fair: float | None
    unsatisfactory: float | None
    course_mean: float | None
    fas_mean: float | None

class CourseFeedback(BaseModel):
    chart: Chart
    overall: LikertDistribution
    materials: LikertDistribution
    assignments: LikertDistribution
    feedback: LikertDistribution
    section: LikertDistribution

class InstructorFeedback(BaseModel):
    chart: Chart
    instructor: str

    overall: LikertDistribution
    effective_lectures: LikertDistribution
    accessible_outside_class: LikertDistribution
    generates_enthusiasm: LikertDistribution
    facilitates_discussion: LikertDistribution
    useful_feedback: LikertDistribution
    returned_assignments_timely: LikertDistribution

class SummaryStatistics(BaseModel):
    response_ratio: float
    mean: float | None
    median: float | None
    stddev: float | None

class HoursPerWeek(BaseModel):
    chart: Chart
    responses: int
    summary_stats: SummaryStatistics

class ScoreDistribution(BaseModel):
    score: int
    count: int
    percentage: float

class RecommendationStrength(BaseModel):
    chart: Chart
    with_enthusiasm: ScoreDistribution
    likely: ScoreDistribution
    with_reservations: ScoreDistribution
    unlikely: ScoreDistribution
    definitely_not: ScoreDistribution

    summary_stats: SummaryStatistics

class ReasonsForEnrollment(BaseModel):
    elective: int
    concentration_or_dept: int
    secondary_or_lang_citation: int
    gened: int
    expos: int
    foreign_lang: int
    pre_med: int
    divisional_dist: int
    quantitative_reasoning: int

class AgreementDistribution(BaseModel):
    chart: Chart

    strongly_agree: ScoreDistribution
    agree: ScoreDistribution
    neither: ScoreDistribution
    disagree: ScoreDistribution
    strongly_disagree: ScoreDistribution

    summary_stats: SummaryStatistics

class Comment(BaseModel):
    text: str

class Course(BaseModel):
    title: str
    subject: str
    department: str
    number: str
    instructors: list[str] = Field(default_factory=list)
    semester: Semester
    section: str
    aliases: list[str] = Field(default_factory=list)

class QGuide(BaseModel):
    id: str
    course: Course
    response_rate: ResponseRate | None
    course_feedback: CourseFeedback | None
    instructor_feedback: list[InstructorFeedback] = Field(default_factory=list)

    @field_validator("instructor_feedback", mode="before")
    @classmethod
    def _coerce_instructor_feedback(cls, v):
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        return v
    hours_per_week: HoursPerWeek | None
    recommendation_strength: RecommendationStrength | None
    reasons_for_enrollment: ReasonsForEnrollment | None
    most_students_open_minded: AgreementDistribution | None
    comfortable_expressing_views: AgreementDistribution | None
    comments: list[Comment] = Field(default_factory=list)

@dataclass(frozen=True)
class QGuideListing:
    department: str
    subject: str
    course_number: str
    course_code: str
    title: str
    section: str
    instructor: str | None
    qguide_id: str
    url: str
    semester: Semester | None = None

class QGuideURLs(BaseModel):
    semester: Semester
    school: School
    listings: list[QGuideListing]
