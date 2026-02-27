# backend/profile_generator/technical_course_loader.py

import pandas as pd
from backend.data_bridge.interfaces import CatalogBridge
from backend.types.course import Course
from backend.types.ceab_attributes import CEABAttributes
from backend.types.constants import CourseConstants

class TechnicalCourseLoader:

    @staticmethod
    def get_num_credits(course_code: str) -> float:
        """
        Determine credits from the code suffix:
        - ...H* → 0.5 credits
        - ...Y* → 1.0 credits
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
    def load_technical_courses(file_path: str) -> list[Course]:
        df = pd.read_excel(file_path, engine="odf")

        courses: list[Course] = []
        for _, row in df.iterrows():
            code = str(row["Course Code"]).strip()
            term = str(row["Term"]).strip()
            area = int(row["Area"])
            kernel_flag = bool(int(row["Kernel"]))

            num_credits = TechnicalCourseLoader.get_num_credits(code)

            courses.append(
                Course(
                    course_code=code,
                    num_credits=num_credits,
                    term=term,
                    area=area,
                    kernel_course=kernel_flag,
                    technical_elective=True,
                    free_elective=True,
                    ceab=None,
                )
            )

        return courses

    @staticmethod
    def load_technical_courses_from_bridge(bridge: CatalogBridge, include_excluded: bool = False) -> list[Course]:
        records = bridge.get_technical_courses(include_excluded=include_excluded)
        courses: list[Course] = []

        for row in records:
            ceab = CEABAttributes(
                total_AU=int((row.math + row.ns + row.cs + row.es + row.ed)),
                mathematics=int(row.math),
                natural_science=int(row.ns),
                math_and_science=int(row.math + row.ns),
                engineering_science=int(row.es),
                engineering_design=int(row.ed),
                eng_sci_and_design=int(row.es + row.ed),
                complementary_studies=int(row.cs),
            )
            courses.append(
                Course(
                    course_code=row.course_code,
                    num_credits=TechnicalCourseLoader.get_num_credits(row.course_code),
                    term=row.term,
                    area=row.area,
                    kernel_course=row.kernel_course,
                    technical_elective=row.technical_elective,
                    free_elective=row.free_elective,
                    ceab=ceab,
                )
            )
        return courses

    @staticmethod
    def load_profile_courses_from_bridge(bridge: CatalogBridge, include_excluded: bool = False) -> list[Course]:
        """
        ProfileGenerator requires:
        - all technical offerings (for breadth/depth selection)
        - required ECE472H1 (F/S offerings)
        - capstone Y offerings
        """
        courses: list[Course] = []
        seen: set[tuple[str, str]] = set()

        def add_offering(code: str, term: str):
            key = (code, term)
            if key in seen:
                return
            offering = bridge.get_course_offering(code, term)
            if offering is None:
                return
            # CEAB values are course-level in DB; map with derived fields.
            math = float(offering.math or 0.0)
            ns = float(offering.ns or 0.0)
            cs = float(offering.cs or 0.0)
            es = float(offering.es or 0.0)
            ed = float(offering.ed or 0.0)
            ceab = CEABAttributes(
                total_AU=int(math + ns + cs + es + ed),
                mathematics=int(math),
                natural_science=int(ns),
                math_and_science=int(math + ns),
                engineering_science=int(es),
                engineering_design=int(ed),
                eng_sci_and_design=int(es + ed),
                complementary_studies=int(cs),
            )
            courses.append(
                Course(
                    course_code=offering.course_code,
                    num_credits=TechnicalCourseLoader.get_num_credits(offering.course_code),
                    term=offering.term,
                    area=offering.area if offering.area is not None else -1,
                    kernel_course=bool(offering.kernel_course),
                    technical_elective=bool(offering.technical_elective),
                    free_elective=bool(offering.free_elective),
                    ceab=ceab,
                )
            )
            seen.add(key)

        # 1) Technical offerings
        for row in bridge.get_technical_courses(include_excluded=include_excluded):
            add_offering(row.course_code, row.term)

        # 2) Required ECE472H1 offerings (F/S)
        for row in bridge.search_courses("ECE472H1", limit=20):
            if row.course_code == "ECE472H1":
                add_offering("ECE472H1", row.term)

        # 3) Capstones (Y)
        for cap in CourseConstants.CAPSTONE_CODES:
            for row in bridge.search_courses(cap, limit=20):
                if row.course_code == cap:
                    add_offering(cap, row.term)

        return courses
