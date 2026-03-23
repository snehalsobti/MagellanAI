from __future__ import annotations

from dataclasses import dataclass

from backend.types.course import Course


@dataclass(frozen=True)
class CoursePoolBuilder:
    courses: list[Course]
    # Read from SSOT (hard_requirements.exclude_h3_h5).  Defaults to True so
    # that callers that do not yet pass a policy stay safe.
    exclude_h3_h5: bool = True

    def is_excluded(self, course: Course) -> bool:
        if bool(getattr(course, "is_excluded", False)):
            return True
        if self.exclude_h3_h5 and (
            course.course_code.endswith("H3") or course.course_code.endswith("H5")
        ):
            return True
        return False

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
