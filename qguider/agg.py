from __future__ import annotations

from collections import defaultdict
from typing import Iterator

from .models import QGuide


class QGuideSet:
    def __init__(self, guides: list[QGuide]):
        self._guides = guides

    def __iter__(self) -> Iterator[QGuide]:
        return iter(self._guides)

    def __len__(self) -> int:
        return len(self._guides)

    def __repr__(self) -> str:
        return f"QGuideSet({len(self._guides)} guides)"

    def __getitem__(self, index):
        return self._guides[index]

    def agg(self, by: str = "id") -> "QGuideSet":
        """
        Aggregate QGuides by a grouping key.

        by="id"  — group by qguide_id, merging instructor_feedback across
                   entries that share the same ID (same course offering,
                   multiple instructors).
        """
        if by == "id":
            return QGuideSet(_merge_by_id(self._guides))
        raise ValueError(f"Unknown aggregation key: {by!r}. Expected 'id'.")


def _merge_by_id(guides: list[QGuide]) -> list[QGuide]:
    groups: dict[str, list[QGuide]] = defaultdict(list)
    for g in guides:
        groups[g.id].append(g)

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
