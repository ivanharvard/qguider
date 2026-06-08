from __future__ import annotations

from pydantic import BaseModel, Field

import enum

class ResponseRate(BaseModel):
    responded: int
    invited: int
    response_ratio: float

class Chart(BaseModel):
    path: str

class LikertDistribution(BaseModel):
    count: int
    excellent: float
    very_good: float
    good: float
    fair: float
    unsatisfactory: float
    course_mean: float
    fas_mean: float

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
    mean: float
    median: float
    stddev: float

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

class Season(str, enum.Enum):
    winter = "Winter"
    spring = "Spring"
    summer = "Summer"
    fall = "Fall"

class Semester(BaseModel):
    season: Season
    year: int

class Course(BaseModel):
    title: str
    subject: str
    number: str
    instructors: list[str] = Field(default_factory=list)
    semester: Semester

class QGuide(BaseModel):
    course: Course
    response_rate: ResponseRate
    course_feedback: CourseFeedback
    instructor_feedback: InstructorFeedback | None
    hours_per_week: HoursPerWeek
    recommendation_strength: RecommendationStrength
    reasons_for_enrollment: ReasonsForEnrollment
    most_students_open_minded: AgreementDistribution
    comfortable_expressing_views: AgreementDistribution 
    comments: list[Comment] = Field(default_factory=list)

class School(enum.Enum):
    FAS = ("FAS", "Faculty of Arts and Sciences")
    SEAS = ("SEAS", "School of Engineering and Applied Sciences")
    GSE = ("GSE", "Graduate School of Education")
    HMS = ("HMS", "Harvard Medical School")
    SPH = ("SPH", "Harvard T.H. Chan School of Public Health")
    SUMMER = ("Summer", "Summer School")


    def __init__(self, code: str, description: str):
        self.code = code
        self.description = description