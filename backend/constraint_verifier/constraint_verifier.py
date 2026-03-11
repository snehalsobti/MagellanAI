# backend/constraint_verifier/constraint_verifier.py

import json
import os
import re
from dataclasses import dataclass

from backend.constraint_verifier.constraint_schema import normalize_constraints
from backend.types.ceab_baseline import load_year12_ceab_baseline
from backend.types.course import Course


@dataclass(frozen=True)
class RuleCheck:
    name: str
    fn_name: str


class ConstraintVerifier:
    def __init__(self, semester_courses: list[list[Course]], json_path=None, year12_choice: str | None = None):
        # Compute default JSON path relative to THIS file
        if json_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "constraints.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Constraint JSON file not found at: {json_path}")

        with open(json_path, "r") as f:
            self.constraints = normalize_constraints(json.load(f))

        self.semester_courses = semester_courses
        # Flatten the list for existing credit and CEAB checks
        self.courses = self._unique_courses()
        self.year12_choice_override = year12_choice
        self.rule_registry: list[RuleCheck] = [
            RuleCheck("Total Credits Requirement", "verify_total_credits"),
            RuleCheck("Required Course Set", "verify_required_courses"),
            RuleCheck("ECE472 Required", "verify_ece472"),
            RuleCheck("Capstone Required", "verify_capstone"),
            RuleCheck("Breadth Requirement", "verify_breadth_requirement"),
            RuleCheck("Depth Requirement", "verify_depth_requirement"),
            RuleCheck("Math/Science (Area 7) Requirement", "verify_math_sci_requirement"),
            RuleCheck("Term Validity", "verify_term_validity"),
            RuleCheck("No H3/H5 Courses", "verify_h3_h5_exclusion"),
            RuleCheck("CSC3*/CSC4* Credit Cap", "verify_csc34_credit_cap"),
            RuleCheck("Complementary Studies Requirement", "verify_complementary_requirement"),
            RuleCheck("Year 3 Technical Course Requirement", "verify_year3_technical_requirement"),
            RuleCheck("Technical Elective Requirement", "verify_technical_elective_requirement"),
            RuleCheck("Free Elective Requirement", "verify_free_elective_requirement"),
            RuleCheck("No Repetition Requirement", "verify_no_repetition"),
            RuleCheck("Semester Count (Exactly 4)", "verify_semester_count"),
            RuleCheck("Course Load (<= 6 per semester)", "verify_courses_per_semester"),
        ]

    def _get_constraint(self, key: str, default=None):
        return self.constraints.get(key, default)

    def _load_ceab_baseline(self) -> dict[str, float]:
        include_baseline = bool(self._get_constraint("include_year12_ceab_baseline", True))
        if not include_baseline:
            return {
                "total_AU": 0.0,
                "mathematics": 0.0,
                "natural_science": 0.0,
                "math_and_science": 0.0,
                "engineering_science": 0.0,
                "engineering_design": 0.0,
                "eng_sci_and_design": 0.0,
                "complementary_studies": 0.0,
            }
        year12_choice = str(self.year12_choice_override or self._get_constraint("year12_default_choice", "ECE297H1") or "ECE297H1")
        return load_year12_ceab_baseline(year12_choice=year12_choice)

    def _is_capstone_course(self, course: Course) -> bool:
        return bool(getattr(course, "is_required", False)) and course.term == "Y"

    def _required_non_capstone_count(self) -> int:
        return sum(
            1 for c in self.courses
            if bool(getattr(c, "is_required", False)) and not self._is_capstone_course(c)
        )

    # ----------------------------------------------------------
    # 1. Total Credits = required
    # ----------------------------------------------------------
    def verify_total_credits(self) -> bool:
        total = sum(c.num_credits for c in self.courses)
        return abs(total - self.constraints["total_num_credits"]) < 1e-6
    
    def verify_no_repetition(self) -> bool:
        seen = set()
        flattened_courses = [course for semester in self.semester_courses for course in semester]
        for c in flattened_courses:
            if c.course_code in seen and not self._is_capstone_course(c):
                return False
            seen.add(c.course_code)
        return True

    # ----------------------------------------------------------
    # 2. ECE472 must exist
    # ----------------------------------------------------------
    def verify_ece472(self) -> bool:
        required = self._get_constraint("ece472_required", True)
        if not required:
            return True
        return any(c.course_code == "ECE472H1" for c in self.courses)

    # ----------------------------------------------------------
    # 3. Capstone must exist
    # ----------------------------------------------------------
    def verify_capstone(self) -> bool:
        required = self._get_constraint("capstone_required", True)
        # Count how many capstones occur
        count = sum(self._is_capstone_course(c) for c in self.courses)

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
        min_breadth_areas = self._get_constraint("min_breadth_areas", 0)
        min_kernel_per_area = self._get_constraint("min_kernel_per_breadth_area", 0)
        if min_breadth_areas <= 0:
            return True

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
        min_depth_areas = self._get_constraint("min_depth_areas", 0)
        min_kernel_per_area = self._get_constraint("min_kernel_per_depth_area", 0)
        min_courses_per_area = self._get_constraint("min_courses_per_depth_area", 0)
        if min_depth_areas <= 0:
            return True

        area_map = self._courses_by_area()

        qualifying_depth_areas = 0
        for area, clist in area_map.items():
            kernel_count = sum(1 for c in clist if c.kernel_course)
            total_count = len(clist)

            if kernel_count >= min_kernel_per_area and total_count >= min_courses_per_area:
                qualifying_depth_areas += 1

        return qualifying_depth_areas >= min_depth_areas
    
    def verify_math_sci_requirement(self) -> bool:
        min_needed = self._get_constraint("min_math_sci_courses", 0)
        if min_needed <= 0:
            return True

        # Breadth/depth is constrained to areas 1..6, so area-7 courses are inherently outside breadth/depth buckets.
        count = sum(1 for c in self.courses if c.area == 7)
        return count >= min_needed

    def verify_required_courses(self) -> bool:
        min_required_non_cap = int(self._get_constraint("min_required_non_capstone_courses", 1) or 0)
        if min_required_non_cap <= 0:
            return True
        return self._required_non_capstone_count() >= min_required_non_cap

    def verify_term_validity(self) -> bool:
        allow_non_capstone_y = bool(self._get_constraint("allow_non_capstone_y", False))
        for c in self.courses:
            if c.term == "Y" and not self._is_capstone_course(c) and not allow_non_capstone_y:
                return False
        return True

    def verify_h3_h5_exclusion(self) -> bool:
        enforce = bool(self._get_constraint("exclude_h3_h5", False))
        if not enforce:
            return True
        return all(not (c.course_code.endswith("H3") or c.course_code.endswith("H5")) for c in self.courses)

    def verify_csc34_credit_cap(self) -> bool:
        max_credits = self._get_constraint("max_csc34_credits", None)
        if max_credits is None:
            return True
        pat = re.compile(r"^CSC[34]")
        total = sum(c.num_credits for c in self.courses if pat.match(c.course_code))
        return total <= float(max_credits) + 1e-6

    def verify_complementary_requirement(self) -> bool:
        min_total = int(self._get_constraint("min_complementary_courses", 0) or 0)
        min_hss = int(self._get_constraint("min_hss_in_complementary", 0) or 0)
        if min_total <= 0 and min_hss <= 0:
            return True
        comp = [
            c for c in self.courses
            if (c.non_technical_type in ("hss", "cs"))
            and not getattr(c, "is_year1_year2", False)
            and not getattr(c, "is_required", False)
        ]
        hss_count = sum(1 for c in comp if c.non_technical_type == "hss")
        return len(comp) >= min_total and hss_count >= min_hss

    def verify_year3_technical_requirement(self) -> bool:
        if len(self.semester_courses) < 2:
            return False
        min_if_no_ece472 = int(self._get_constraint("year3_min_technical_courses", 0) or 0)
        min_if_with_ece472 = int(self._get_constraint("year3_min_technical_courses_if_ece472", min_if_no_ece472) or 0)
        if min_if_no_ece472 <= 0:
            return True

        year3_courses = self.semester_courses[0] + self.semester_courses[1]
        has_ece472 = any(c.course_code == "ECE472H1" for c in year3_courses)
        threshold = min_if_with_ece472 if has_ece472 else min_if_no_ece472
        technical_count = sum(
            1
            for c in year3_courses
            if c.course_type == "technical" or bool(getattr(c, "technical_elective", False))
        )
        return technical_count >= threshold

    def verify_technical_elective_requirement(self) -> bool:
        min_needed = int(self._get_constraint("min_technical_elective_courses", 0) or 0)
        if min_needed <= 0:
            return True
        consumed = self._technical_requirement_consumed_codes()
        if consumed is None:
            return False
        count = sum(
            1
            for c in self.courses
            if bool(getattr(c, "technical_elective", False))
            and not getattr(c, "is_year1_year2", False)
            and not getattr(c, "is_required", False)
            and c.course_code not in consumed
        )
        return count >= min_needed

    def verify_free_elective_requirement(self) -> bool:
        min_needed = int(self._get_constraint("min_free_elective_courses", 0) or 0)
        if min_needed <= 0:
            return True
        count = sum(
            1
            for c in self.courses
            if bool(getattr(c, "free_elective", False))
            and not getattr(c, "is_year1_year2", False)
            and not getattr(c, "is_required", False)
            and c.term in ("F", "S")
        )
        return count >= min_needed

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
        ceab_baseline = self._load_ceab_baseline()
        
        for req_key, pre_key, obj_prop, label in attr_mapping:
            # 1. Calculate the Net Requirement
            target = self.constraints[req_key]
            already_have = self.constraints[pre_key]
            net_needed = max(0.0, target - already_have)

            # 2. Sum up what the current courses provide
            provided = sum(getattr(c.ceab, obj_prop) for c in self.courses) + float(ceab_baseline.get(obj_prop, 0.0))

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
    def evaluate(self) -> dict:
        checks = []
        for rule in self.rule_registry:
            fn = getattr(self, rule.fn_name)
            checks.append((rule.name, bool(fn())))
        failed_checks = [name for name, ok in checks if not ok]
        ceab_failures = []
        if self._get_constraint("ceab_attributes_required", True):
            ceab_results = self.verify_ceab_requirements()
            for label, (is_ok, deficit) in ceab_results.items():
                if not is_ok:
                    ceab_failures.append({"label": label, "deficit": float(deficit)})
        return {
            "ok": len(failed_checks) == 0 and len(ceab_failures) == 0,
            "failed_checks": failed_checks,
            "ceab_failures": ceab_failures,
        }

    def verify(self) -> bool:
        report = self.evaluate()
        for name in report["failed_checks"]:
            print(f"Constraint Unsatisfied: {name}")
        for item in report["ceab_failures"]:
            print(f"Constraint Unsatisfied CEAB: {item['label']} (Missing {item['deficit']:.1f} AU)")
        if report["ok"]:
            print("✔ All constraints satisfied!")
        return bool(report["ok"])

    # -----------------------------------------------------
    # Helper utilities
    # -----------------------------------------------------
    def _courses_by_area(self) -> dict[int, list]:
        """Group courses by area, ignoring courses with no area."""
        area_map: dict[int, list] = {}
        allowed_areas = set(self._get_constraint("breadth_depth_area_domain", [1, 2, 3, 4, 5, 6, 7]))
        for c in self.courses:
            if c.area is None or c.area == -1:
                continue
            if allowed_areas and c.area not in allowed_areas:
                continue
            area_map.setdefault(c.area, []).append(c)
        return area_map

    def _technical_requirement_consumed_codes(self) -> set[str] | None:
        """
        Build one valid witness assignment for requirement-consumed technical courses:
        breadth + depth extras + math/sci minimum. Returns None if not constructible.
        """
        min_breadth_areas = int(self._get_constraint("min_breadth_areas", 0) or 0)
        min_kernel_per_breadth = int(self._get_constraint("min_kernel_per_breadth_area", 1) or 1)
        min_depth_areas = int(self._get_constraint("min_depth_areas", 0) or 0)
        min_courses_per_depth = int(self._get_constraint("min_courses_per_depth_area", 0) or 0)
        min_math_sci = int(self._get_constraint("min_math_sci_courses", 0) or 0)

        # Group technical, non-required/non-year1_year2 courses by area in 1..6.
        area_map: dict[int, list[Course]] = {}
        for c in self.courses:
            if c.area is None or c.area not in (1, 2, 3, 4, 5, 6):
                continue
            if not (bool(getattr(c, "technical_elective", False)) or c.course_type == "technical"):
                continue
            if getattr(c, "is_required", False) or getattr(c, "is_year1_year2", False):
                continue
            area_map.setdefault(c.area, []).append(c)

        kernel_area_candidates = {
            area: [c for c in clist if bool(getattr(c, "kernel_course", False))]
            for area, clist in area_map.items()
        }
        kernel_area_candidates = {a: cl for a, cl in kernel_area_candidates.items() if len(cl) >= min_kernel_per_breadth}

        if len(kernel_area_candidates) < min_breadth_areas:
            return None

        # Pick breadth areas with richest pools first.
        breadth_areas = sorted(kernel_area_candidates.keys(), key=lambda a: len(area_map[a]), reverse=True)[:min_breadth_areas]
        consumed: set[str] = set()
        for area in breadth_areas:
            # consume one kernel per breadth area
            k = sorted(kernel_area_candidates[area], key=lambda c: c.course_code)[0]
            consumed.add(k.course_code)

        # Depth areas are chosen from breadth areas; each needs min_courses_per_depth total.
        depth_candidates = [a for a in breadth_areas if len({c.course_code for c in area_map[a]}) >= min_courses_per_depth]
        if len(depth_candidates) < min_depth_areas:
            return None
        depth_areas = sorted(depth_candidates, key=lambda a: len(area_map[a]), reverse=True)[:min_depth_areas]
        for area in depth_areas:
            uniq_codes = []
            for c in sorted(area_map[area], key=lambda x: x.course_code):
                if c.course_code not in uniq_codes:
                    uniq_codes.append(c.course_code)
            # Already consumed one breadth kernel in this area. Need extras to hit min courses.
            needed_extra = max(0, min_courses_per_depth - 1)
            extras = [code for code in uniq_codes if code not in consumed][:needed_extra]
            if len(extras) < needed_extra:
                return None
            consumed.update(extras)

        # Math/sci area7 requirement consumption
        if min_math_sci > 0:
            area7 = []
            for c in sorted(self.courses, key=lambda x: x.course_code):
                if c.area != 7:
                    continue
                if getattr(c, "is_required", False) or getattr(c, "is_year1_year2", False):
                    continue
                if c.course_code in area7:
                    continue
                area7.append(c.course_code)
            if len(area7) < min_math_sci:
                return None
            consumed.update(area7[:min_math_sci])

        return consumed

    def _unique_courses(self) -> list[Course]:
        """Return one Course per course_code (first occurrence)."""
        seen = set()
        uniq = []
        flattened_courses = [course for semester in self.semester_courses for course in semester]
        for c in flattened_courses:
            if c.course_code not in seen:
                seen.add(c.course_code)
                uniq.append(c)
        return uniq

