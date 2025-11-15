# ConstraintVerifier/constraint_verifier.py

import json
import os
from typing import List
from courses import Course


class ConstraintVerifier:
    def __init__(self, courses, json_path=None):
        # Compute default JSON path relative to THIS file
        if json_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "constraints.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Constraint JSON file not found at: {json_path}")

        with open(json_path, "r") as f:
            self.constraints = json.load(f)

        self.courses = courses

    # ----------------------------------------------------------
    # 1. Total Credits = required
    # ----------------------------------------------------------
    def verify_total_credits(self) -> bool:
        total = sum(c.num_credits for c in self.courses)
        return total == self.constraints["total_num_credits"]

    # ----------------------------------------------------------
    # 2. ECE472 must exist
    # ----------------------------------------------------------
    def verify_ece472(self) -> bool:
        required = self.constraints["ECE472_required"]
        if not required:
            return True
        return any(c.course_code == "ECE472" for c in self.courses)

    # ----------------------------------------------------------
    # 3. Kernel count >= min_kernel_requirement
    # ----------------------------------------------------------
    def verify_kernel_requirement(self) -> bool:
        # Collect all areas where the student took a kernel course
        kernel_areas = {c.area for c in self.courses if c.kernel_course}

        # Requirement: at least 4 kernel courses from 4 distinct areas
        return len(kernel_areas) >= 4

    # ----------------------------------------------------------
    # 4. Depth requirement
    # A "depth-qualified" area must have:
    #    - 1 kernel course in that area
    #    - at least 2 other courses in that area
    # ----------------------------------------------------------
    def verify_depth_requirement(self) -> bool:
        min_depth = self.constraints["min_depth_requirement"]

        area_map = {}
        for c in self.courses:
            area_map.setdefault(c.area, []).append(c)

        depth_areas = 0

        for area, clist in area_map.items():
            # Must have a kernel in the area
            kernel_here = any(c.kernel_course for c in clist)
            if not kernel_here:
                continue

            # Must have >=2 non-kernel courses
            other_course_count = sum(1 for c in clist)
            if other_course_count >= 2:
                depth_areas += 1

        return depth_areas >= min_depth

    # ----------------------------------------------------------
    # Main verification function
    # ----------------------------------------------------------
    def verify(self) -> bool:
        checks = [
            ("Total Credits Requirement", self.verify_total_credits()),
            ("ECE472 Required", self.verify_ece472()),
            ("Kernel Requirement", self.verify_kernel_requirement()),
            ("Depth Requirement", self.verify_depth_requirement()),
        ]

        all_ok = True

        for name, result in checks:
            if not result:
                print(f"❌ FAILED: {name}")
                all_ok = False

        if all_ok:
            print("✔ All constraints satisfied!")

        return all_ok
