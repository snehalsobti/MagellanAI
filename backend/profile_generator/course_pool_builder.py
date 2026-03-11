from __future__ import annotations

from dataclasses import dataclass

from backend.types.course import Course


@dataclass(frozen=True)
class CoursePoolBuilder:
    courses: list[Course]

    @staticmethod
    def is_excluded(course: Course) -> bool:
        return bool(getattr(course, "is_excluded", False)) or course.course_code.endswith("H3") or course.course_code.endswith("H5")

    @staticmethod
    def is_capstone(course: Course) -> bool:
        return bool(getattr(course, "is_required", False)) and course.term == "Y"

    def capstone_codes(self) -> list[str]:
        return sorted(
            {
                c.course_code
                for c in self.courses
                if self.is_capstone(c) and not self.is_excluded(c)
            }
        )

    def required_non_capstone_codes(self) -> list[str]:
        return sorted(
            {
                c.course_code
                for c in self.courses
                if bool(getattr(c, "is_required", False))
                and not self.is_capstone(c)
                and not self.is_excluded(c)
            }
        )

