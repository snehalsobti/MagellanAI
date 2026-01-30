# backend/profile_generator/profile_printer.py

from backend.types.course import Course
from backend.types.constants import CourseConstants

class ProfilePrinter:
    """
    Pretty-print a generated profile in the exact grouped format:
      • ECE472H1 first
      • Capstone
      • Depth areas (kernel first in each)
      • Other areas (kernel first)
      • Semester grid (4x5)
      • Metadata
    """

    def __init__(self, course_name_lookup: dict[str, str]):
        self.course_name_lookup = course_name_lookup

    def get_name(self, code: str) -> str:
        return self.course_name_lookup.get(code, "(Name unavailable)")

    def print_profile(self, result: dict):
        courses: list[Course] = result["courses"]
        kernel_areas = result["kernel_areas_selected"]
        depth_areas = result["depth_areas_selected"]

        print("\n==================== Generated Profile ==========================\n")

        # ---------------------------------------------------------
        # Group by area (ignore area == -1)
        # ---------------------------------------------------------
        by_area: dict[int, list[Course]] = {}
        for c in courses:
            if c.area is not None and c.area != -1:
                by_area.setdefault(c.area, []).append(c)


        # ---------------------------------------------------------
        # 1. Print ECE472H1 first
        # ---------------------------------------------------------
        ece472 = next((c for c in courses if c.course_code == "ECE472H1"), None)
        if ece472:
            print("ECE472H1 (Required):")
            print(f" • {ece472.course_code} - {self.get_name(ece472.course_code)}")
            print()

        # ---------------------------------------------------------
        # 2. Capstone
        # ---------------------------------------------------------
        capstone = next(
            (c for c in courses if c.course_code in CourseConstants.CAPSTONE_CODES),
            None,
        )
        if capstone:
            print("Capstone (Required):")
            print(f" • {capstone.course_code} - {self.get_name(capstone.course_code)}")
            print()

        # ---------------------------------------------------------
        # 3. Depth Areas
        # ---------------------------------------------------------
        for area in depth_areas:
            print(f"Depth Area {area}:")

            print_courses = sorted(
                by_area.get(area, []),
                key=lambda x: (not x.kernel_course, x.course_code)
            )

            for c in print_courses:
                tag = " (kernel)" if c.kernel_course else ""
                print(f" • {c.course_code}{tag} - {self.get_name(c.course_code)}")
            print()

        # ---------------------------------------------------------
        # 4. Remaining Areas
        # ---------------------------------------------------------
        remaining_areas = sorted(a for a in by_area.keys() if a not in depth_areas)

        for area in remaining_areas:
            print(f"Area {area}:")
            area_list = sorted(
                by_area[area],
                key=lambda x: (not x.kernel_course, x.course_code)
            )
            for c in area_list:
                tag = " (kernel)" if c.kernel_course else ""
                print(f" • {c.course_code}{tag} - {self.get_name(c.course_code)}")
            print()

        # ---------------------------------------------------------
        # 5. Semester Grid (NEW)
        # ---------------------------------------------------------
        if "semester_plan" in result:
            print("=========================== Semester Plan ======================")

            labels = ["3F", "3S", "4F", "4S"]
            semester_plan = result["semester_plan"]

            for label, semester in zip(labels, semester_plan):
                codes = [c.course_code for c in semester]
                padded = codes + [""] * (5 - len(codes))  # safety
                row = " | ".join(f"{c:<10}" for c in padded)
                print(f"{label}: {row}")

            print("================================================================\n")

        # ---------------------------------------------------------
        # Metadata
        # ---------------------------------------------------------
        print("======================== Metadata ==============================")
        print(f"Total Credits: {result['total_credits']}")
        print(f"Kernel Areas Selected: {result['kernel_areas_selected']}")
        print(f"Depth Areas Selected: {result['depth_areas_selected']}")
        print(f"Seed Used: {result['seed_used']}")
        print(f"Preferences Requested: {result['preferences_requested']}")
        print(f"Preferences Used: {result['preferences_used']}")
        print(f"Preferences Skipped: {result['preferences_skipped']}")
        print("================================================================\n")
