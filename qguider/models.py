from __future__ import annotations

from pydantic import BaseModel
from typing import Optional

import enum

class ResponseRate(BaseModel):
    responded: int
    invited: int
    response_ratio: int

class Chart(BaseModel):
    path: str

class LikertDistribution(BaseModel):
    count: int
    excellent: int
    very_good: int
    good: int
    fair: int
    unsatisfactory: int
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
    overall: LikertDistribution
    effective_lectures: LikertDistribution
    accessible_outside_class: LikertDistribution
    generates_enthusiasm: LikertDistribution
    facilitates_discussion: LikertDistribution
    useful_feedback: LikertDistribution
    returned_assignments_timely: LikertDistribution

class HoursPerWeek(BaseModel):
    chart: Chart
    responses: int
    response_ratio: int
    mean: float
    median: float
    stddev: float

class ScoreDistribution(BaseModel):
    score: int
    count: int
    percentage: int

class RecommendationStrength(BaseModel):
    chart: Chart
    with_enthusiasm: ScoreDistribution
    likely: ScoreDistribution
    with_reservations: ScoreDistribution
    unlikely: ScoreDistribution
    definitely_not: ScoreDistribution

    response_ratio: int
    mean: float
    median: float
    stddev: float

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

class MostStudentsOpenMinded(BaseModel):
    chart: Chart

    strongly_agree: ScoreDistribution
    agree: ScoreDistribution
    neither: ScoreDistribution
    disagree: ScoreDistribution
    strongly_disagree: ScoreDistribution

    response_ratio: int
    mean: float
    median: float
    stddev: float

class ComfortableExpressingViews(BaseModel):
    chart: Chart

    strongly_agree: ScoreDistribution
    agree: ScoreDistribution
    neither: ScoreDistribution
    disagree: ScoreDistribution
    strongly_disagree: ScoreDistribution

    response_ratio: int
    mean: float
    median: float
    stddev: float

class Comment(BaseModel):
    text: str

class Season(enum.Enum):
    Winter = "Winter"
    Spring = "Spring"
    Summer = "Summer"
    Fall = "Fall"

class Semester(BaseModel):
    season: Season
    year: int

class Course(BaseModel):
    title: str
    department: str
    number: str
    instructor: str
    semester: Semester

class QGuide(BaseModel):
    course: Course
    response_rate: ResponseRate
    course_feedback: CourseFeedback
    instructor_feedback: InstructorFeedback
    hours_per_week: HoursPerWeek
    recommendation_strength: RecommendationStrength
    reasons_for_enrollment: ReasonsForEnrollment
    most_students_open_minded: MostStudentsOpenMinded
    comfortable_expressing_views: ComfortableExpressingViews
    comments: list[Comment]