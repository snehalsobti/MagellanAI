# backend/constraint_verifier/constraint_verifier.py

import json
import os
from backend.types.constants import CourseConstants
from backend.types.course import Course

class ConstraintVerifier:
    def __init__(self, semester_courses: list[list[Course]], json_path=None):
        # Compute default JSON path relative to THIS file
        if json_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "constraints.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Constraint JSON file not found at: {json_path}")

        with open(json_path, "r") as f:
            self.constraints = json.load(f)

        self.semester_courses = semester_courses
        # Flatten the list for existing credit and CEAB checks
        self.courses = [course for semester in semester_courses for course in semester]

    # ----------------------------------------------------------
    # 1. Total Credits = required
    # ----------------------------------------------------------
    def verify_total_credits(self) -> bool:
        total = sum(c.num_credits for c in self.courses)
        return abs(total - self.constraints["total_num_credits"]) < 1e-6
    
    def verify_no_repetition(self) -> bool:
        seen = set()
        for c in self.courses:
            if c.course_code in seen:
                return False
            seen.add(c.course_code)
        return True

    # ----------------------------------------------------------
    # 2. ECE472 must exist
    # ----------------------------------------------------------
    def verify_ece472(self) -> bool:
        required = self.constraints["ece472_required"]
        if not required:
            return True
        return any(c.course_code == "ECE472H1" for c in self.courses)

    # ----------------------------------------------------------
    # 3. Capstone must exist
    # ----------------------------------------------------------
    def verify_capstone(self) -> bool:
        required = self.constraints["capstone_required"]

        # Count how many capstones occur
        count = sum(c.course_code in CourseConstants.CAPSTONE_CODES for c in self.courses)

        if not required:
            # If not required, then 0 or 1 is okay, but 2+ should still fail
            return count <= 1

        # If required -> must be exactly 1
        return count == 1


    # ----------------------------------------------------------
    # 4. Breadth / Kernel requirement
    #    "min_breadth_areas" distinct areas with at least
    #    "min_kernel_per_breadth_area" kernel courses in each area
    # ----------------------------------------------------------
    def verify_breadth_requirement(self) -> bool:
        min_breadth_areas = self.constraints["min_breadth_areas"]
        min_kernel_per_area = self.constraints["min_kernel_per_breadth_area"]

        area_map = self._courses_by_area()

        qualifying_areas = 0
        for area, clist in area_map.items():
            kernel_count = sum(1 for c in clist if c.kernel_course)
            if kernel_count >= min_kernel_per_area:
                qualifying_areas += 1

        return qualifying_areas >= min_breadth_areas

    # ----------------------------------------------------------
    # 5. Depth requirement
    #    "min_depth_areas" areas must have:
    #    - "min_kernel_per_depth_area" kernel courses AND
    #    - "min_courses_per_depth_area" total courses
    # ----------------------------------------------------------
    def verify_depth_requirement(self) -> bool:
        min_depth_areas = self.constraints["min_depth_areas"]
        min_kernel_per_area = self.constraints["min_kernel_per_depth_area"]
        min_courses_per_area = self.constraints["min_courses_per_depth_area"]

        area_map = self._courses_by_area()

        qualifying_depth_areas = 0
        for area, clist in area_map.items():
            kernel_count = sum(1 for c in clist if c.kernel_course)
            total_count = len(clist)

            if kernel_count >= min_kernel_per_area and total_count >= min_courses_per_area:
                qualifying_depth_areas += 1

        return qualifying_depth_areas >= min_depth_areas
    
    # ----------------------------------------------------------
    # 6. CEAB Accreditation Attributes
    # ----------------------------------------------------------
    def verify_ceab_requirements(self) -> dict:
        """
        Returns a dictionary of results for each CEAB attribute.
        Key: Attribute Name, Value: (Boolean success, float deficit)
        """
        # Mapping: (JSON Required Key, JSON Preobtained Key, CEABAttributes property name, Display Name)
        attr_mapping = [
            ("ceab_total_au", "preobtained_total_au", "total_AU", "Total AU"),
            ("ceab_math", "preobtained_math", "mathematics", "Math"),
            ("ceab_ns", "preobtained_ns", "natural_science", "Natural Science"),
            ("ceab_math_ns", "preobtained_math_ns", "math_and_science", "Math & NS"),
            ("ceab_es", "preobtained_es", "engineering_science", "Eng Science"),
            ("ceab_ed", "preobtained_ed", "engineering_design", "Eng Design"),
            ("ceab_es_ed", "preobtained_es_ed", "eng_sci_and_design", "ES & ED"),
            ("ceab_cs", "preobtained_cs", "complementary_studies", "Comp Studies"),
        ]

        results = {}
        
        for req_key, pre_key, obj_prop, label in attr_mapping:
            # 1. Calculate the Net Requirement
            target = self.constraints[req_key]
            already_have = self.constraints[pre_key]
            net_needed = max(0.0, target - already_have)

            # 2. Sum up what the current courses provide
            provided = sum(getattr(c.ceab, obj_prop) for c in self.courses)

            # 3. Verify
            is_ok = provided >= net_needed
            deficit = max(0.0, net_needed - provided)
            results[label] = (is_ok, deficit)

        return results

    # ----------------------------------------------------------
    # 7. Semester Structure Checks
    # ----------------------------------------------------------
    def verify_semester_count(self) -> bool:
        # Constraint: Exactly 4 semesters (rows)
        return len(self.semester_courses) == 4

    def verify_courses_per_semester(self) -> bool:
        # Constraint: Each semester has <= 6 courses
        return all(len(semester) <= 6 for semester in self.semester_courses)

    # ----------------------------------------------------------
    # Main verification function
    # ----------------------------------------------------------
    def verify(self) -> bool:
        checks = [
            ("Total Credits Requirement", self.verify_total_credits()),
            ("ECE472 Required", self.verify_ece472()),
            ("Capstone Required", self.verify_capstone()),
            ("Breadth Requirement", self.verify_breadth_requirement()),
            ("Depth Requirement", self.verify_depth_requirement()),
            ("No Repetition Requirement", self.verify_no_repetition()),
            ("Semester Count (Exactly 4)", self.verify_semester_count()),
            ("Course Load (<= 6 per semester)", self.verify_courses_per_semester()),
        ]

        all_ok = True

        for name, result in checks:
            if not result:
                print(f"Constraint Unsatisfied: {name}")
                all_ok = False

        # Run CEAB Checks
        ceab_results = self.verify_ceab_requirements()
        for label, (is_ok, deficit) in ceab_results.items():
            if not is_ok:
                print(f"Constraint Unsatisfied CEAB: {label} (Missing {deficit:.1f} AU)")
                all_ok = False

        if all_ok:
            print("✔ All constraints satisfied!")

        return all_ok

    # -----------------------------------------------------
    # Helper utilities
    # -----------------------------------------------------
    def _courses_by_area(self) -> dict[int, list]:
        """Group courses by area, ignoring courses with no area."""
        area_map: dict[int, list] = {}
        for c in self.courses:
            if c.area is None or c.area == -1:
                continue
            area_map.setdefault(c.area, []).append(c)
        return area_map
