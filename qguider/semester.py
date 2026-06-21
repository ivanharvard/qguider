from __future__ import annotations

import enum
from datetime import date
from typing import Callable, Iterator

from pydantic import BaseModel


class Season(str, enum.Enum):
    """
    The four academic seasons.

    Also a str subclass so Pydantic accepts plain strings like "Fall"
    without a custom validator.
    """

    winter = "Winter"
    spring = "Spring"
    summer = "Summer"
    fall = "Fall"

    @classmethod
    def from_string(cls, value: str) -> Season:
        """
        Parse a season from a string.

        Args:
            value (str): Season name, e.g. "Fall" or "spring".

        Returns:
            Season: The matching Season member.

        Raises:
            ValueError: If the value does not match any known season.
        """
        value = value.strip().capitalize()
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(
            f"Invalid season: {value!r}. "
            f"Expected one of: {[s.value for s in cls]}"
        )


# Canonical ordering used by Semester._step for arithmetic across season/year boundaries.
_SEASON_ORDER = [Season.winter, Season.spring, Season.summer, Season.fall]


class School(enum.Enum):
    """
    Harvard schools supported by QGuider.

    Each member carries a short code, a full description, and the set of
    seasons that school runs. The seasons field is used by SemesterCalendar
    to skip irrelevant seasons when stepping or ranging.
    """

    FAS    = ("FAS",    "Faculty of Arts and Sciences",               frozenset({Season.spring, Season.fall}))
    SEAS   = ("SEAS",   "School of Engineering and Applied Sciences", frozenset({Season.spring, Season.fall}))
    GSE    = ("GSE",    "Graduate School of Education",               frozenset({Season.spring, Season.fall}))
    HMS    = ("HMS",    "Harvard Medical School",                     frozenset({Season.spring, Season.fall}))
    SPH    = ("SPH",    "Harvard T.H. Chan School of Public Health",  frozenset({Season.spring, Season.fall}))
    SUMMER = ("Summer", "Summer School",                              frozenset({Season.summer}))

    def __init__(self, code: str, description: str, seasons: frozenset):
        self.code = code
        self.description = description
        self.seasons = seasons

    @classmethod
    def from_string(cls, value: str) -> School:
        """
        Parse a school from a code or full name.

        Args:
            value (str): School code (e.g. "FAS") or full name
                (e.g. "Faculty of Arts and Sciences"). Case-insensitive.

        Returns:
            School: The matching School member.

        Raises:
            ValueError: If the value does not match any known school.
        """
        value = value.strip().upper()
        for member in cls:
            if member.code == value or member.description.upper() == value:
                return member
        raise ValueError(
            f"Invalid school: {value!r}. "
            f"Expected one of: {[s.code for s in cls]} or {[s.description for s in cls]}"
        )


class Semester(BaseModel):
    """A single academic semester identified by a season and a calendar year."""

    season: Season
    year: int

    @classmethod
    def from_string(cls, value: str) -> Semester:
        """
        Parse a semester from a human-readable string.

        Args:
            value (str): Semester string, e.g. "Fall 2020" or "Spring 2021".

        Returns:
            Semester: The parsed semester.

        Raises:
            ValueError: If the string is not in the expected "Season Year" format.
        """
        parts = value.strip().split()
        if len(parts) != 2:
            raise ValueError(
                f"Invalid semester format: {value!r}. "
                "Expected a format like 'Fall 2020'."
            )
        season, year = parts
        return cls(season=Season(season.capitalize()), year=int(year))

    @classmethod
    def from_date(cls, d: date) -> Semester:
        """
        Derive the semester that contains a given calendar date.

        Mapping:
            Jan          -> Winter
            Feb - May    -> Spring
            Jun - Aug    -> Summer
            Sep - Dec    -> Fall

        Args:
            d (date): The date to map.

        Returns:
            Semester: The semester containing that date.
        """
        if d.month == 1:
            season = Season.winter
        elif d.month <= 5:
            season = Season.spring
        elif d.month <= 8:
            season = Season.summer
        else:
            season = Season.fall
        return cls(season=season, year=d.year)

    @classmethod
    def for_school(cls, school: School = School.FAS) -> SemesterCalendar:
        """
        Entry point for the fluent calendar API.

        Defaults to FAS since that is the only school currently supported.
        Returns an unanchored SemesterCalendar; call .latest() before
        navigating.

        Args:
            school (School): The school whose valid seasons define navigation.
                Defaults to School.FAS.

        Returns:
            SemesterCalendar: An unanchored calendar scoped to the given school.

        Example:
            Semester.for_school().latest().range(back=4)
            Semester.for_school(School.SUMMER).latest() - 1
        """
        return SemesterCalendar(school)

    def _step(self, n: int) -> Semester:
        # Moves n positions through _SEASON_ORDER, carrying over the year when
        # wrapping past Winter (backwards) or Fall (forwards).
        # Python's floor-division and modulo always return consistent signs for
        # a positive divisor, so negative n works correctly.
        idx = _SEASON_ORDER.index(self.season)
        total = idx + n
        return Semester(
            season=_SEASON_ORDER[total % len(_SEASON_ORDER)],
            year=self.year + total // len(_SEASON_ORDER),
        )

    def __repr__(self) -> str:
        return f"Semester({self.season.value} {self.year})"

    def __str__(self) -> str:
        return f"{self.season.value} {self.year}"

    def to_qguide_term(self) -> str:
        """
        Format this semester as expected by the QGuide URL and query API.

        Returns:
            str: e.g. "2020 Fall"
        """
        return f"{self.year} {self.season.value}"


class SemesterCalendar:
    """
    A school-scoped semester pointer for fluent date-agnostic navigation.

    Immutable -- every method returns a new SemesterCalendar instance.
    Call .latest() first to anchor the calendar before using any navigation
    methods.

    Typical usage:
        cal = Semester.for_school()
        cal.latest()                    # anchor to the most recent valid semester
        cal.latest() - 2               # two valid semesters before latest
        cal.latest().range(back=4)     # latest + 4 prior semesters -> SemesterRange
    """

    def __init__(self, school: School, _current: Semester | None = None):
        self._school = school
        self._current = _current

    @property
    def semester(self) -> Semester:
        """
        Unwrap to a plain Semester value.

        Returns:
            Semester: The currently anchored semester.

        Raises:
            ValueError: If .latest() has not been called yet.
        """
        if self._current is None:
            raise ValueError("Call .latest() first to anchor the calendar.")
        return self._current

    def latest(self, as_of: date | None = None) -> SemesterCalendar:
        """
        Anchor to the most recent valid semester for this school.

        Steps backwards from the given date until landing on a season
        included in school.seasons.

        Args:
            as_of (date | None): Reference date. Defaults to today.

        Returns:
            SemesterCalendar: A new calendar anchored to the latest valid semester.
        """
        current = Semester.from_date(as_of or date.today())
        while current.season not in self._school.seasons:
            current = current._step(-1)
        return SemesterCalendar(self._school, current)

    def back(self, n: int) -> SemesterCalendar:
        """
        Step back n valid semesters, skipping seasons not in school.seasons.

        back(0) returns a calendar at the same position.

        Args:
            n (int): Number of valid semesters to step back.

        Returns:
            SemesterCalendar: A new calendar n valid semesters before the current one.
        """
        current = self.semester
        for _ in range(n):
            current = current._step(-1)
            while current.season not in self._school.seasons:
                current = current._step(-1)
        return SemesterCalendar(self._school, current)

    def forward(self, n: int) -> SemesterCalendar:
        """
        Step forward n valid semesters, skipping seasons not in school.seasons.

        Args:
            n (int): Number of valid semesters to step forward.

        Returns:
            SemesterCalendar: A new calendar n valid semesters after the current one.
        """
        current = self.semester
        for _ in range(n):
            current = current._step(1)
            while current.season not in self._school.seasons:
                current = current._step(1)
        return SemesterCalendar(self._school, current)

    def __sub__(self, n: int) -> SemesterCalendar:
        return self.back(n)

    def __add__(self, n: int) -> SemesterCalendar:
        return self.forward(n)

    def range(self, back: int = 0, forward: int = 0, step: int = 1) -> SemesterRange:
        """
        Collect a window of valid semesters relative to the current position.

        The window extends `back` semesters into the past and `forward`
        semesters into the future, inclusive on both ends. `step` samples
        every nth semester within that window. Results are ordered newest
        to oldest.

        range(back=4) produces the current semester plus 4 prior = 5 total.
        range(back=2, forward=1) produces 1 ahead + current + 2 back = 4 total.
        range(back=6, step=2) produces every other semester going back 6 = 4 total.

        Args:
            back (int): Number of valid semesters to include going backwards.
                Defaults to 0.
            forward (int): Number of valid semesters to include going forwards.
                Defaults to 0.
            step (int): Stride between included semesters. Defaults to 1
                (every semester).

        Returns:
            SemesterRange: The collected semesters ordered newest to oldest.
        """
        fwd_cal = self.forward(forward) if forward else self
        total = back + forward
        semesters = []
        cursor = fwd_cal
        for i in range(total + 1):
            if i % step == 0:
                semesters.append(cursor.semester)
            if i < total:
                cursor = cursor.back(1)
        return SemesterRange(semesters)


class SemesterRange:
    """
    An ordered sequence of Semester values produced by SemesterCalendar.range().

    Iterable, so it can be passed directly to Query.semesters(). Ordered
    newest to oldest by default.
    """

    def __init__(self, semesters: list[Semester]):
        self._semesters = semesters

    def __iter__(self) -> Iterator[Semester]:
        return iter(self._semesters)

    def __len__(self) -> int:
        return len(self._semesters)

    def __repr__(self) -> str:
        return f"SemesterRange({len(self._semesters)} semesters)"

    def filter(self, predicate: Callable[[Semester], bool]) -> SemesterRange:
        """
        Keep only semesters where predicate returns True.

        Args:
            predicate (Callable[[Semester], bool]): Filter function.

        Returns:
            SemesterRange: A new range containing only the matching semesters.
        """
        return SemesterRange([s for s in self._semesters if predicate(s)])

    def exclude(self, predicate: Callable[[Semester], bool]) -> SemesterRange:
        """
        Remove semesters where predicate returns True. Inverse of filter().

        Args:
            predicate (Callable[[Semester], bool]): Exclusion function.

        Returns:
            SemesterRange: A new range with the matching semesters removed.
        """
        return SemesterRange([s for s in self._semesters if not predicate(s)])
