# backend/profile_generator/profile_course_loader.py

from backend.data_bridge.interfaces import CatalogBridge
from backend.types.course import Course
from backend.types.ceab_attributes import CEABAttributes


class ProfileCourseLoader:
    """Build Course objects for profile generation from bridge rows."""

    @staticmethod
    def get_num_credits(course_code: str) -> float:
        """
        Determine credits from the code suffix:
        - ...H* -> 0.5 credits
        - ...Y* -> 1.0 credits
        """
        code = course_code.strip()
        if len(code) < 2:
            raise ValueError(f"Invalid course code: {course_code}")

        suffix = code[-2]  # The 'H' or 'Y' in ECE318H1, ECE496Y1
        if suffix == "H":
            return 0.5
        if suffix == "Y":
            return 1.0

        raise ValueError(f"Could not determine credit value for: {course_code}")

    @staticmethod
    def load_profile_courses_from_bridge(bridge: CatalogBridge, include_excluded: bool = False) -> list[Course]:
        """
        Load all profile candidate offerings from the catalog bridge.
        Filtering by requirement role/category should happen in generator policy logic.
        """
        courses: list[Course] = []
        # Keep multi-area variants for the same (course_code, term).
        # They are needed for correct area-aware constraint solving.
        seen: set[tuple[str, str, int, bool, bool, bool, str | None, str | None]] = set()

        def add_row(row):
            key = (
                row.course_code,
                row.term,
                (row.area if row.area is not None else -1),
                bool(row.kernel_course),
                bool(row.technical_elective),
                bool(row.free_elective),
                row.course_type,
                row.non_technical_type,
            )
            if key in seen:
                return
            offering = bridge.get_course_offering(row.course_code, row.term)
            math = float((offering.math if offering else 0.0) or 0.0)
            ns = float((offering.ns if offering else 0.0) or 0.0)
            cs = float((offering.cs if offering else 0.0) or 0.0)
            es = float((offering.es if offering else 0.0) or 0.0)
            ed = float((offering.ed if offering else 0.0) or 0.0)
            ceab = CEABAttributes(
                total_AU=float(math + ns + cs + es + ed),
                mathematics=float(math),
                natural_science=float(ns),
                math_and_science=float(math + ns),
                engineering_science=float(es),
                engineering_design=float(ed),
                eng_sci_and_design=float(es + ed),
                complementary_studies=float(cs),
            )
            courses.append(
                Course(
                    course_code=row.course_code,
                    num_credits=ProfileCourseLoader.get_num_credits(row.course_code),
                    term=row.term,
                    area=row.area if row.area is not None else -1,
                    kernel_course=bool(row.kernel_course),
                    technical_elective=bool(row.technical_elective),
                    free_elective=bool(row.free_elective),
                    course_type=row.course_type,
                    non_technical_type=row.non_technical_type,
                    is_year1_year2=bool(row.is_year1_year2),
                    is_required=bool(row.is_required),
                    is_excluded=bool(row.is_excluded),
                    ceab=ceab,
                )
            )
            seen.add(key)

        for row in bridge.get_profile_candidate_courses(
            include_excluded=include_excluded,
            include_year1_year2=False,
            include_required=True,
        ):
            add_row(row)

        return courses
