import unittest
from backend.types.course import Course
from backend.types.ceab_attributes import CEABAttributes
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.types.constants import CourseConstants
from io import StringIO
from unittest.mock import patch

class TestConstraintVerifier(unittest.TestCase):
    def _wrap_into_semesters(self, courses):
        """Helper to wrap a flat list into exactly 4 semesters."""
        if not courses:
            return [[], [], [], []]
        # Distribute courses across 4 lists
        semesters = [[], [], [], []]
        for i, course in enumerate(courses):
            semesters[i % 4].append(course)
        return semesters

    # Category 1: Integration Tests (2 tests)
    def test_fail_case(self):
        print("\n--- Running Legacy Fail Case (including CEAB) ---")
        
        courses = [
            Course("ECE101H1", area=1, num_credits=0.5, kernel_course=True),
            Course("ECE102H1", area=1, num_credits=0.5),
            Course("ECE201H1", area=2, num_credits=0.5, kernel_course=True),
            Course("ECE472H1", num_credits=0.5),
            Course("ECE496Y1", num_credits=1.0),
        ]
        # Wrap into 4 semesters
        semesters = self._wrap_into_semesters(courses)
        verifier = ConstraintVerifier(semesters)
        verifier.constraints["ceab_attributes_required"] = True

        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = verifier.verify()
            output = fake_out.getvalue()

        self.assertFalse(result)

        expected_failures = [
            "Constraint Unsatisfied: Total Credits Requirement",
            "Constraint Unsatisfied: Breadth Requirement",
            "Constraint Unsatisfied: Depth Requirement",
            "Constraint Unsatisfied CEAB: Total AU (Missing 780.7 AU)",
            "Constraint Unsatisfied CEAB: Natural Science (Missing 18.9 AU)",
            "Constraint Unsatisfied CEAB: Math & NS (Missing 25.2 AU)",
            "Constraint Unsatisfied CEAB: Eng Design (Missing 107.5 AU)",
            "Constraint Unsatisfied CEAB: ES & ED (Missing 427.6 AU)",
            "Constraint Unsatisfied CEAB: Comp Studies (Missing 149.9 AU)"
        ]

        for failure in expected_failures:
            self.assertIn(failure, output)

    def test_pass_case(self):
        print("--- Running Legacy Pass Case (including CEAB) ---")
        
        courses = [
            Course("ECE101H1", area=1, num_credits=1.0, kernel_course=True,
                ceab=CEABAttributes(total_AU=80, engineering_design=30, natural_science=20)),
            Course("ECE102H1", area=1, num_credits=1.0,
                ceab=CEABAttributes(total_AU=80, eng_sci_and_design=50, natural_science=10)),
            Course("ECE103H1", area=1, num_credits=1.0,
                ceab=CEABAttributes(total_AU=80, engineering_design=40)),
            Course("ECE201H1", area=2, num_credits=1.0, kernel_course=True,
                ceab=CEABAttributes(total_AU=80, eng_sci_and_design=60)),
            Course("ECE202H1", area=2, num_credits=1.0,
                ceab=CEABAttributes(total_AU=80, eng_sci_and_design=60)),
            Course("ECE203H1", area=2, num_credits=1.0,
                ceab=CEABAttributes(total_AU=80, eng_sci_and_design=60)),
            Course("ECE104H1", area=3, num_credits=1.0, kernel_course=True,
                ceab=CEABAttributes(total_AU=80, eng_sci_and_design=170)),
            Course("ECE205H1", area=4, num_credits=0.5, kernel_course=True,
                ceab=CEABAttributes(total_AU=80, eng_sci_and_design=60, math_and_science=30)),
            Course("ECE305H1", area=7, num_credits=0.5, kernel_course=True,
                ceab=CEABAttributes(total_AU=80, eng_sci_and_design=60, math_and_science=30)),
            Course("ECE472H1", num_credits=1.0,
                ceab=CEABAttributes(total_AU=80, complementary_studies=80)),
            Course("ECE496Y1", num_credits=1.0, 
                ceab=CEABAttributes(total_AU=100, engineering_design=50, complementary_studies=80))
        ]

        semesters = self._wrap_into_semesters(courses)
        verifier = ConstraintVerifier(semesters)
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = verifier.verify()
            output = fake_out.getvalue()
        
        self.assertTrue(result)
        self.assertIn("✔ All constraints satisfied!", output)

    def test_semester_count_output_fail(self):
        print("\n--- Running Semester Count Output Test ---")
        # Provide only 2 semesters instead of 4
        semesters = [
            [Course("C1", num_credits=1.0)],
            [Course("C2", num_credits=1.0)]
        ]
        verifier = ConstraintVerifier(semesters)

        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = verifier.verify()
            output = fake_out.getvalue()

        self.assertFalse(result)
        # Check for the specific semester count failure keyword
        self.assertIn("Constraint Unsatisfied: Semester Count (Exactly 4)", output)

class TestConstraintVerifierExtended(unittest.TestCase):
    printed_categories = set()

    def _print_header(self, category):
        if category not in self.printed_categories:
            print(f"\n  RUNNING: {category.upper()}")
            self.printed_categories.add(category)

    def _wrap(self, courses):
        """Helper to ensure we always provide exactly 4 semesters."""
        semesters = [[], [], [], []]
        for i, c in enumerate(courses):
            semesters[i % 4].append(c)
        return semesters

    def create_base_valid_semesters(self):
        courses = [
            Course("C1", area=1, num_credits=1.0, kernel_course=True),
            Course("C1_extra_1", area=1, num_credits=1.0),
            Course("C1_extra_2", area=1, num_credits=1.0),
            Course("C2", area=2, num_credits=1.0, kernel_course=True),
            Course("C2_extra_1", area=2, num_credits=1.0),
            Course("C2_extra_2", area=2, num_credits=1.0),
            Course("C3", area=3, num_credits=1.0, kernel_course=True),
            Course("C4", area=4, num_credits=0.5, kernel_course=True),
            Course("ECE472H1", area=5, num_credits=0.5),
            Course("ECE496Y1", area=6, num_credits=1.0),
            Course("C5", area=7, num_credits=0.5),
            Course("C6", area=8, num_credits=0.5),
        ]
        return self._wrap(courses)

    # --- SEMESTER STRUCTURE (2 tests) ---
    def test_semester_count_fail(self):
        self._print_header("Semester Structure")
        v = ConstraintVerifier([[Course("C1", 1.0)], [Course("C2", 1.0)]]) # Only 2 rows
        self.assertFalse(v.verify_semester_count())

    def test_course_load_overload(self):
        self._print_header("Courses Overload")
        semesters = self.create_base_valid_semesters()
        
        # Force 7 courses to be absolutely sure we are over the limit of 6
        semesters[0] = [Course(f"T{i}", 0.1) for i in range(7)] 
        
        v = ConstraintVerifier(semesters)
        self.assertFalse(v.verify_courses_per_semester())

    # --- TOTAL CREDITS (4 tests) ---
    def test_credits_low(self):
        self._print_header("Total Credits")
        sem = self.create_base_valid_semesters()
        sem[0][0].num_credits = 0.5
        self.assertFalse(ConstraintVerifier(sem).verify_total_credits())

    def test_credits_high(self):
        self._print_header("Total Credits")
        sem = self.create_base_valid_semesters()
        sem[3].append(Course("Extra", 1.0))
        self.assertFalse(ConstraintVerifier(sem).verify_total_credits())

    def test_credits_float_pass(self):
        self._print_header("Total Credits")
        courses = [Course(f"T{i}", 0.5) for i in range(20)]
        self.assertTrue(ConstraintVerifier(self._wrap(courses)).verify_total_credits())

    def test_credits_float_near_miss(self):
        self._print_header("Total Credits")
        courses = [Course(f"T{i}", 0.50001) for i in range(20)]
        self.assertFalse(ConstraintVerifier(self._wrap(courses)).verify_total_credits())

    # --- ECE472 (2 tests) ---
    def test_ece472_missing(self):
        self._print_header("Required Courses")
        sem = [[c for c in s if c.course_code != "ECE472H1"] for s in self.create_base_valid_semesters()]
        self.assertFalse(ConstraintVerifier(sem).verify_ece472())

    def test_ece472_not_required_pass(self):
        self._print_header("Required Courses")
        sem = [[c for c in s if c.course_code != "ECE472H1"] for s in self.create_base_valid_semesters()]
        v = ConstraintVerifier(sem); v.constraints["ece472_required"] = False
        self.assertTrue(v.verify_ece472())

    # --- CAPSTONE (4 tests) ---
    def test_capstone_missing(self):
        self._print_header("Capstone")
        sem = [[c for c in s if c.course_code not in CourseConstants.CAPSTONE_CODES] for s in self.create_base_valid_semesters()]
        self.assertFalse(ConstraintVerifier(sem).verify_capstone())

    def test_capstone_not_required(self):
        self._print_header("Capstone")
        sem = [[c for c in s if c.course_code not in CourseConstants.CAPSTONE_CODES] for s in self.create_base_valid_semesters()]
        v = ConstraintVerifier(sem); v.constraints["capstone_required"] = False
        self.assertTrue(v.verify_capstone())

    def test_capstone_exactly_one(self):
        self._print_header("Capstone")
        self.assertTrue(ConstraintVerifier(self.create_base_valid_semesters()).verify_capstone())

    def test_capstone_multiple_fail(self):
        self._print_header("Capstone")
        sem = self.create_base_valid_semesters()
        sem[0].append(Course("APS490Y1", 1.0))
        self.assertFalse(ConstraintVerifier(sem).verify_capstone())

    # --- BREADTH & DEPTH (5 tests) ---
    def test_kernel_distinct_fail(self):
        self._print_header("Breadth & Depth")
        sem = self.create_base_valid_semesters()
        for s in sem: 
            for c in s: 
                if c.kernel_course: c.area = 1
        self.assertFalse(ConstraintVerifier(sem).verify_breadth_requirement())

    def test_kernel_count_pass(self):
        self._print_header("Breadth & Depth")
        self.assertTrue(ConstraintVerifier(self.create_base_valid_semesters()).verify_breadth_requirement())

    def test_depth_missing_extra(self):
        self._print_header("Breadth & Depth")
        sem = [[c for c in s if "_extra" not in c.course_code] for s in self.create_base_valid_semesters()]
        self.assertFalse(ConstraintVerifier(sem).verify_depth_requirement())

    def test_depth_no_kernel(self):
        self._print_header("Breadth & Depth")
        sem = self._wrap([Course("A", 1, 1.0, kernel_course=False), Course("B", 1, 1.0, kernel_course=False)])
        self.assertFalse(ConstraintVerifier(sem).verify_depth_requirement())

    def test_depth_pass(self):
        self._print_header("Breadth & Depth")
        self.assertTrue(ConstraintVerifier(self.create_base_valid_semesters()).verify_depth_requirement())

    # --- Math & Science (2 tests) ---
    def test_math_sci_pass(self):
        self._print_header("Math & Science")
        sem = self.create_base_valid_semesters()
        v = ConstraintVerifier(sem, breadth_depth_codes=set())
        v.constraints["min_math_sci_courses"] = 1
        self.assertTrue(v.verify_math_sci_requirement())

    def test_math_sci_fail_if_area7_used_in_breadth_depth(self):
        self._print_header("Math & Science")
        sem = self.create_base_valid_semesters()
        # Find the area-7 course code
        area7_codes = {c.course_code for s in sem for c in s if c.area == 7}
        self.assertTrue(area7_codes)  # sanity

        v = ConstraintVerifier(sem, breadth_depth_codes=area7_codes)
        v.constraints["min_math_sci_courses"] = 1
        self.assertFalse(v.verify_math_sci_requirement())

    # --- REPETITION & DYNAMIC (3 tests) ---
    def test_repetition_fail(self):
        self._print_header("Repetition & Dynamic")
        sem = self.create_base_valid_semesters()
        sem[0].append(Course("C1", 0.0))
        self.assertFalse(ConstraintVerifier(sem).verify_no_repetition())

    def test_dynamic_depth_mod(self):
        self._print_header("Repetition & Dynamic")
        v = ConstraintVerifier(self.create_base_valid_semesters())
        v.constraints["min_depth_areas"] = 10
        self.assertFalse(v.verify_depth_requirement())

    def test_empty_verifier_fail(self):
        self._print_header("Repetition & Dynamic")
        v = ConstraintVerifier([[], [], [], []])
        
        with patch('sys.stdout', new=StringIO()):
            result = v.verify()
            
        self.assertFalse(result)

class TestCEABAccreditation(unittest.TestCase):
    printed_categories = set()

    def _print_header(self, category):
        if category not in self.printed_categories:
            print(f"  RUNNING: {category.upper()}")
            self.printed_categories.add(category)

    def _wrap(self, courses):
        semesters = [[], [], [], []]
        for i, c in enumerate(courses):
            semesters[i % 4].append(c)
        return semesters

    def test_ceab_math_ns_combined_pool_fail(self):
        self._print_header("CEAB Attribute Logic Tests")
        courses = [
            Course("MATH101", num_credits=1.0, ceab=CEABAttributes(total_AU=50, mathematics=50)),
            Course("PHYS101", num_credits=1.0, ceab=CEABAttributes(total_AU=50, natural_science=50))
        ]
        v = ConstraintVerifier(self._wrap(courses))
        v.constraints["ceab_attributes_required"] = True
        v.constraints.update({"ceab_math": 50, "preobtained_math": 0, 
                             "ceab_ns": 50, "preobtained_ns": 0, 
                             "ceab_math_ns": 150, "preobtained_math_ns": 0})
        results = v.verify_ceab_requirements()
        self.assertFalse(results["Math & NS"][0])

    def test_ceab_total_au_deficit_fail(self):
        self._print_header("CEAB Attribute Logic Tests")
        courses = [Course("C1", 1.0, ceab=CEABAttributes(total_AU=50, mathematics=50))]
        v = ConstraintVerifier(self._wrap(courses))
        v.constraints["ceab_attributes_required"] = True
        v.constraints.update({"ceab_math": 50, "preobtained_math": 0, 
                             "ceab_total_au": 200, "preobtained_total_au": 0})
        results = v.verify_ceab_requirements()
        self.assertFalse(results["Total AU"][0])

if __name__ == "__main__":
    unittest.main()