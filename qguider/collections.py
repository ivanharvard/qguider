from __future__ import annotations

from collections import defaultdict
from typing import Iterator, Callable, Any

from .models import QGuide


class QGuideSet:
    def __init__(self, qguides: list[QGuide]):
        self._qguides = qguides

    def __iter__(self) -> Iterator[QGuide]:
        return iter(self._qguides)

    def __len__(self) -> int:
        return len(self._qguides)

    def __repr__(self) -> str:
        return f"QGuideSet({len(self._qguides)} QGuides)"

    def __getitem__(self, index):
        return self._qguides[index]

    def agg(self, by: str = "id") -> "QGuideSet":
        """
        Aggregate QGuides by any field on QGuide.

        Merges instructor_feedback, comments, and course aliases across
        entries that share the same value for the given field.
        """
        if by not in QGuide.model_fields:
            valid = list(QGuide.model_fields.keys())
            raise ValueError(f"Unknown aggregation key: {by!r}. Expected one of: {valid}")
        return QGuideSet(_merge_by_field(self._qguides, by))

    def filter(self, predicate: Callable[[QGuide], Any | bool]) -> "QGuideSet":
        return QGuideSet([q for q in self._qguides if predicate(q)])

def _merge_by_field(qguides: list[QGuide], field: str) -> list[QGuide]:
    groups: dict = defaultdict(list)
    for g in qguides:
        groups[getattr(g, field)].append(g)

    result = []
    for group in groups.values():
        first = group[0]

        # Union all known course codes across the group into aliases.
        all_codes: set[str] = set()
        for q in group:
            all_codes.add(f"{q.course.subject} {q.course.number}")
            all_codes.update(q.course.aliases)

        primary = f"{first.course.subject} {first.course.number}"
        merged_aliases = sorted(all_codes - {primary})

        # Collect instructor feedbacks, deduplicating by instructor name.
        seen: set[str] = set()
        instructor_feedback = []
        for q in group:
            for fb in q.instructor_feedback:
                if fb.instructor not in seen:
                    instructor_feedback.append(fb)
                    seen.add(fb.instructor)

        # Collect all comments, deduplicating by text.
        seen_comments: set[str] = set()
        comments = []
        for q in group:
            for c in q.comments:
                if c.text not in seen_comments:
                    comments.append(c)
                    seen_comments.add(c.text)

        merged_course = first.course.model_copy(update={"aliases": merged_aliases})

        result.append(first.model_copy(update={
            "course": merged_course,
            "instructor_feedback": instructor_feedback,
            "comments": comments,
        }))

    return result
