# backend/profile_generator/profile_generator.py

import os
import random
import pandas as pd

from backend.course import Course
from backend.ceab_attributes import CEABAttributes
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier


# ---------------------------------------------------------
#  TECHNICAL COURSE LOADER
# ---------------------------------------------------------
class TechnicalCourseLoader:

    @staticmethod
    def get_num_credits(course_code: str) -> float:
        """
        Determine credits from the code suffix:
        - ...H* → 0.5
        - ...Y* → 1.0
        """
        code = course_code.strip()
        if len(code) < 2:
            raise ValueError(f"Invalid course code: {course_code}")

        kind = code[-2]  # e.g., 'H' or 'Y' in ECE318H1 / ECE496Y1
        if kind == "H":
            return 0.5
        if kind == "Y":
            return 1.0

        raise ValueError(f"Could not determine credit value for: {course_code}")

    @staticmethod
    def load_technical_courses(file_path: str) -> list[Course]:
        """Loads technical_courses.ods from disk and returns Course objects."""
        df = pd.read_excel(file_path, engine="odf")

        courses: list[Course] = []

        for _, row in df.iterrows():
            course_code = str(row["Course Code"]).strip()
            term = str(row["Term"]).strip()
            area = int(row["Area"])
            kernel_flag = bool(int(row["Kernel"]))

            num_credits = TechnicalCourseLoader.get_num_credits(course_code)

            courses.append(
                Course(
                    course_code=course_code,
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


# ---------------------------------------------------------
#  PROFILE GENERATOR (CONSTRAINT SATISFACTION)
# ---------------------------------------------------------
class ProfileGenerator:
    def __init__(self, technical_courses: list[Course]):
        # Keep ALL rows (including duplicates, areas 1–7, terms F/S/Y, etc.)
        # We'll enforce uniqueness by course_code only in the generated profile.
        self.courses: list[Course] = technical_courses

    # -----------------------------------------------------
    #  Main API
    # -----------------------------------------------------
    def generate_profile(self, seed: int | None = None) -> dict:
        """
        Generate a random but valid course list that satisfies constraints.
        Returns a dict with metadata.

        The generated course list will have unique course codes (no repetition),
        but self.courses may contain duplicates (same code in multiple terms/areas).
        """

        rng = random.Random(seed)

        while True:
            plan: list[Course] = []
            chosen_codes: set[str] = set()
            credits = 0.0

            # -------------------------------------------------
            # 1. Required: ECE472H1
            # -------------------------------------------------
            ece472 = self._find_course("ECE472H1")
            if ece472 is None:
                raise ValueError("ECE472H1 not found in technical courses!")

            plan.append(ece472)
            chosen_codes.add(ece472.course_code)
            credits += ece472.num_credits  # should be 0.5

            # -------------------------------------------------
            # 2. Required: 1 capstone
            # -------------------------------------------------
            capstone_codes = ["ECE496Y1", "APS490Y1", "BME498Y1"]
            capstones = [self._find_course(c) for c in capstone_codes if self._exists(c)]

            if not capstones:
                raise ValueError("No available capstone courses in dataset!")

            capstone = rng.choice(capstones)
            plan.append(capstone)
            chosen_codes.add(capstone.course_code)
            credits += capstone.num_credits  # should be 1.0

            # -------------------------------------------------
            # 3. Select 4 distinct kernel areas (from 1–6 only)
            # -------------------------------------------------
            kernel_by_area = self._group_kernel_courses_by_area()
            all_kernel_areas = list(kernel_by_area.keys())

            if len(all_kernel_areas) < 4:
                raise ValueError("Not enough kernel areas (1–6) available!")

            kernel_areas = rng.sample(all_kernel_areas, 4)

            kernel_courses: list[Course] = []
            for area in kernel_areas:
                kc = rng.choice(kernel_by_area[area])
                kernel_courses.append(kc)

                if kc.course_code not in chosen_codes:
                    plan.append(kc)
                    chosen_codes.add(kc.course_code)
                    credits += kc.num_credits

            # -------------------------------------------------
            # 4. Select 2 depth areas from the chosen kernel areas
            #    (each needs ≥ 1 kernel + ≥ 2 more courses in that area)
            # -------------------------------------------------
            depth_areas = rng.sample(kernel_areas, 2)
            depth_extra: list[Course] = []

            for area in depth_areas:
                # All courses in this area (kernel or non-kernel), area 1–6 only
                pool = [c for c in self.courses if c.area == area and not c.kernel_course]

                if len(pool) < 2:
                    break  # restart whole generation loop

                chosen_two = rng.sample(pool, 2)

                for c in chosen_two:
                    if c.course_code in chosen_codes:
                        continue
                    plan.append(c)
                    chosen_codes.add(c.course_code)
                    credits += c.num_credits
                    depth_extra.append(c)

            # If we failed to get 2 extra in each depth area (4 total), restart
            if len(depth_extra) < 4:
                continue

            # -------------------------------------------------
            # 5. Fill randomly until exactly 10.0 credits
            #    Here we can use ANY technical courses; the kernel/depth
            #    constraints are already satisfied and only required areas
            #    1–6.
            # -------------------------------------------------
            stuck_counter = 0

            while credits < 10.0:
                available = [c for c in self.courses if c.course_code not in chosen_codes]

                if not available:
                    # No more new courses to pick → restart
                    break

                candidate = rng.choice(available)

                # Try adding
                new_credits = credits + candidate.num_credits
                if new_credits > 10.0:
                    stuck_counter += 1
                    if stuck_counter > 50:
                        # Give up on this attempt and restart entire construction
                        break
                    continue

                # Accept candidate
                plan.append(candidate)
                chosen_codes.add(candidate.course_code)
                credits = new_credits

            if credits == 10.0:
                # SUCCESS — return detailed dict
                return {
                    "courses": plan,  # list[Course], unique by course_code
                    "total_credits": credits,
                    "kernel_areas_selected": kernel_areas,
                    "depth_areas_selected": depth_areas,
                    "seed_used": seed,
                }

            # Otherwise restart loop and try again

    # -----------------------------------------------------
    #  Helper utilities
    # -----------------------------------------------------
    def _find_course(self, code: str) -> Course | None:
        for c in self.courses:
            if c.course_code == code:
                return c
        return None

    def _exists(self, code: str) -> bool:
        return any(c.course_code == code for c in self.courses)

    def _group_kernel_courses_by_area(self) -> dict[int, list[Course]]:
        """
        Group kernel courses by area, but only for areas 1–6 (as per your rule).
        """
        out: dict[int, list[Course]] = {}
        for c in self.courses:
            if c.kernel_course and 1 <= c.area <= 6:
                out.setdefault(c.area, []).append(c)
        return out


# ---------------------------------------------------------
#  MAIN (manual test / demo)
# ---------------------------------------------------------
if __name__ == "__main__":
    # Determine project structure:
    # this file: backend/ProfileGenerator/profile_generator.py
    # want: project_root/data/technical_courses.ods
    current_file = os.path.abspath(__file__)
    profile_gen_dir = os.path.dirname(current_file)
    backend_dir = os.path.dirname(profile_gen_dir)
    project_root = os.path.dirname(backend_dir)

    data_dir = os.path.join(project_root, "data")
    technical_courses_file = os.path.join(data_dir, "technical_courses.ods")

    technical_courses = TechnicalCourseLoader.load_technical_courses(technical_courses_file)

    gen = ProfileGenerator(technical_courses)

    result = gen.generate_profile(seed=42)

    verifier = ConstraintVerifier(result["courses"])
    assert verifier.verify(), "Generated profile does not satisfy constraints!"

    print("\nGenerated Profile (unique course codes):")
    for c in result["courses"]:
        print(" •", c.course_code)

    print("\nTotal credits:", result["total_credits"])
    print("Kernel areas:", result["kernel_areas_selected"])
    print("Depth areas:", result["depth_areas_selected"])
    print("Seed used:", result["seed_used"])
