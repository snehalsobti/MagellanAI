import unittest
from backend.types.course import Course
from backend.types.ceab_attributes import CEABAttributes
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.types.constants import CourseConstants
from io import StringIO
from unittest.mock import patch

class TestConstraintVerifier(unittest.TestCase):
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
        verifier = ConstraintVerifier(courses)

        # Redirect stdout to capture print statements
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = verifier.verify()
            output = fake_out.getvalue()

        # 1. Ensure the overall verification returned False
        self.assertFalse(result)

        # 2. Check for the specific failure keywords in the captured output
        expected_failures = [
            "❌ FAILED: Total Credits Requirement",
            "❌ FAILED: Kernel Requirement",
            "❌ FAILED: Depth Requirement",
            "❌ FAILED CEAB: Total AU (Missing 780.7 AU)",
            "❌ FAILED CEAB: Natural Science (Missing 18.9 AU)",
            "❌ FAILED CEAB: Math & NS (Missing 25.2 AU)",
            "❌ FAILED CEAB: Eng Design (Missing 107.5 AU)",
            "❌ FAILED CEAB: ES & ED (Missing 427.6 AU)",
            "❌ FAILED CEAB: Comp Studies (Missing 149.9 AU)"
        ]

        for failure in expected_failures:
            self.assertIn(failure, output, f"Expected keyword '{failure}' was not found in output.")

    def test_pass_case(self):
            print("--- Running Legacy Pass Case (including CEAB) ---")
            
            # We need to satisfy a total deficit of ~781 AU. 
            # With 10 courses, we can average about 80 AU per course.
            courses = [
                # Area 1: High Design and Science focus
                Course("ECE101H1", area=1, num_credits=1.0, kernel_course=True,
                    ceab=CEABAttributes(total_AU=80, engineering_design=30, natural_science=20)),
                Course("ECE102H1", area=1, num_credits=1.0,
                    ceab=CEABAttributes(total_AU=80, eng_sci_and_design=50, natural_science=10)),
                Course("ECE103H1", area=1, num_credits=1.0,
                    ceab=CEABAttributes(total_AU=80, engineering_design=40)),

                # Area 2: Design and ES+ED focus
                Course("ECE201H1", area=2, num_credits=1.0, kernel_course=True,
                    ceab=CEABAttributes(total_AU=80, eng_sci_and_design=60)),
                Course("ECE202H1", area=2, num_credits=1.0,
                    ceab=CEABAttributes(total_AU=80, eng_sci_and_design=60)),
                Course("ECE203H1", area=2, num_credits=1.0,
                    ceab=CEABAttributes(total_AU=80, eng_sci_and_design=60)),

                # Area 3 & 4: General ES+ED
                Course("ECE104H1", area=3, num_credits=1.0, kernel_course=True,
                    ceab=CEABAttributes(total_AU=80, eng_sci_and_design=170)),
                Course("ECE205H1", area=4, num_credits=1.0, kernel_course=True,
                    ceab=CEABAttributes(total_AU=80, eng_sci_and_design=60, math_and_science=30)),

                # Complementary Studies Focus (Needs 150 total)
                Course("ECE472H1", num_credits=1.0,
                    ceab=CEABAttributes(total_AU=80, complementary_studies=80)),
                Course("ECE496Y1", num_credits=1.0, # Capstone: High Design and Comp Studies
                    ceab=CEABAttributes(total_AU=100, engineering_design=50, complementary_studies=80))
            ]

            verifier = ConstraintVerifier(courses)
            # Redirect stdout to capture print statements
            with patch('sys.stdout', new=StringIO()) as fake_out:
                result = verifier.verify()
                output = fake_out.getvalue()
            # This will now check both your structural credits AND the AU totals
            # 1. Ensure the overall verification returned True
            self.assertTrue(result)

            # 2. Check for the specific failure keywords in the captured output
            expected_string = [
                "✔ All constraints satisfied!",
            ]

            for success in expected_string:
                self.assertIn(success, output, f"Expected keyword '{success}' was not found in output.")

class TestConstraintVerifierExtended(unittest.TestCase):
    printed_categories = set()

    def _print_header(self, category):
        if category not in self.printed_categories:
            print(f"  RUNNING: {category.upper()}")
            self.printed_categories.add(category)

    def create_base_valid_courses(self):
        return [
            Course("C1", area=1, num_credits=1.0, kernel_course=True),
            Course("C1_extra", area=1, num_credits=1.0, kernel_course=False),
            Course("C2", area=2, num_credits=1.0, kernel_course=True),
            Course("C2_extra", area=2, num_credits=1.0, kernel_course=False),
            Course("C3", area=3, num_credits=1.0, kernel_course=True),
            Course("C4", area=4, num_credits=1.0, kernel_course=True),
            Course("ECE472H1", area=5, num_credits=1.0),
            Course("ECE496Y1", area=6, num_credits=1.0),
            Course("C5", area=7, num_credits=1.0),
            Course("C6", area=8, num_credits=1.0),
        ]

    # --- TOTAL CREDITS TESTS (4 tests) ---
    def test_total_credits_too_low(self):
        self._print_header("Total Credits Tests")
        courses = self.create_base_valid_courses()
        courses[0].num_credits = 0.5
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_total_credits())

    def test_total_credits_too_high(self):
        self._print_header("Total Credits Tests")
        courses = self.create_base_valid_courses()
        courses.append(Course("Extra", num_credits=1.0))
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_total_credits())

    def test_credit_float_precision_pass(self):
        self._print_header("Total Credits Tests")
        courses = [Course(f"T{i}", num_credits=0.5) for i in range(20)]
        v = ConstraintVerifier(courses)
        self.assertTrue(v.verify_total_credits())

    def test_credit_float_near_miss_fail(self):
        self._print_header("Total Credits Tests")
        courses = [Course(f"T{i}", num_credits=0.50001) for i in range(20)]
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_total_credits())

    # --- ECE472 TESTS (2 tests) ---
    def test_ece472_missing(self):
        self._print_header("ECE472 Specific Tests")
        courses = [c for c in self.create_base_valid_courses() if c.course_code != "ECE472H1"]
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_ece472())

    def test_ece472_not_required_passes_if_missing(self):
        self._print_header("ECE472 Specific Tests")
        courses = [c for c in self.create_base_valid_courses() if c.course_code != "ECE472H1"]
        v = ConstraintVerifier(courses)
        v.constraints["ece472_required"] = False
        self.assertTrue(v.verify_ece472())

    # --- CAPSTONE TESTS (4 tests) ---
    def test_capstone_missing(self):
        self._print_header("Capstone Requirement Tests")
        courses = [c for c in self.create_base_valid_courses() if c.course_code not in CourseConstants.CAPSTONE_CODES]
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_capstone())

    def test_capstone_not_required_zero_is_fine(self):
        self._print_header("Capstone Requirement Tests")
        courses = [c for c in self.create_base_valid_courses() if c.course_code not in CourseConstants.CAPSTONE_CODES]
        v = ConstraintVerifier(courses)
        v.constraints["capstone_required"] = False
        self.assertTrue(v.verify_capstone())

    def test_capstone_exactly_one(self):
        self._print_header("Capstone Requirement Tests")
        courses = self.create_base_valid_courses()
        v = ConstraintVerifier(courses)
        self.assertTrue(v.verify_capstone())

    def test_multiple_capstones_fail(self):
            self._print_header("Capstone Requirement Tests")
            courses = self.create_base_valid_courses()
            courses.append(Course("APS490Y1", area=6, num_credits=1.0))
            
            v = ConstraintVerifier(courses)
            self.assertFalse(v.verify_capstone())

    # --- KERNEL TESTS (3 tests) ---
    def test_kernel_not_distinct_areas(self):
        self._print_header("Kernel Requirement Tests")
        courses = self.create_base_valid_courses()
        for c in courses:
            if c.kernel_course: c.area = 1
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_kernel_requirement())

    def test_kernel_insufficient_count(self):
        self._print_header("Kernel Requirement Tests")
        courses = self.create_base_valid_courses()
        for c in courses: c.kernel_course = False
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_kernel_requirement())

    def test_kernel_exactly_four_distinct(self):
        self._print_header("Kernel Requirement Tests")
        courses = self.create_base_valid_courses()
        v = ConstraintVerifier(courses)
        self.assertTrue(v.verify_kernel_requirement())

    # --- DEPTH TESTS (3 tests) ---
    def test_depth_missing_extra_course(self):
        self._print_header("Depth Requirement Tests")
        courses = self.create_base_valid_courses()
        courses = [c for c in courses if "_extra" not in c.course_code]
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_depth_requirement())

    def test_depth_area_no_kernel(self):
        self._print_header("Depth Requirement Tests")
        courses = [
            Course("A1", area=1, num_credits=5.0, kernel_course=False),
            Course("A2", area=1, num_credits=5.0, kernel_course=False)
        ]
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_depth_requirement())

    def test_depth_threshold_met_exactly(self):
        self._print_header("Depth Requirement Tests")
        courses = self.create_base_valid_courses()
        v = ConstraintVerifier(courses)
        self.assertTrue(v.verify_depth_requirement())

    # --- REPETITION TESTS (1 test) ---
    def test_repetition_fail(self):
        self._print_header("Repetition Tests")
        courses = self.create_base_valid_courses()
        courses.append(Course("C1", num_credits=0.0))
        v = ConstraintVerifier(courses)
        self.assertFalse(v.verify_no_repetition())

    # --- DYNAMIC CONSTRAINT TESTS (1 test) ---
    def test_min_depth_increase(self):
        self._print_header("Dynamic JSON Tests")
        courses = self.create_base_valid_courses()
        v = ConstraintVerifier(courses)
        v.constraints["min_depth_requirement"] = 5
        self.assertFalse(v.verify_depth_requirement())

    # --- EDGE CASES (1 test) ---
    def test_empty_courses(self):
        self._print_header("Edge Cases")
        v = ConstraintVerifier([])
                # Redirect stdout to capture print statements
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = v.verify()
            output = fake_out.getvalue()

        # 1. Ensure the overall verification returned False
        self.assertFalse(result)

        # 2. Check for the specific failure keywords in the captured output
        expected_failures = [
            "❌ FAILED: Total Credits Requirement",
            "❌ FAILED: ECE472 Required",
            "❌ FAILED: Capstone Required",
            "❌ FAILED: Kernel Requirement",
            "❌ FAILED: Depth Requirement",
            "❌ FAILED CEAB: Total AU (Missing 780.7 AU)",
            "❌ FAILED CEAB: Natural Science (Missing 18.9 AU)",
            "❌ FAILED CEAB: Math & NS (Missing 25.2 AU)",
            "❌ FAILED CEAB: Eng Design (Missing 107.5 AU)",
            "❌ FAILED CEAB: ES & ED (Missing 427.6 AU)",
            "❌ FAILED CEAB: Comp Studies (Missing 149.9 AU)"
        ]

        for failure in expected_failures:
            self.assertIn(failure, output, f"Expected keyword '{failure}' was not found in output.")

class TestCEABAccreditation(unittest.TestCase):
    printed_categories = set()

    def _print_header(self, category):
        if category not in self.printed_categories:
            print(f"  RUNNING: {category.upper()}")
            self.printed_categories.add(category)

    def test_ceab_all_preobtained_satisfied(self):
        self._print_header("CEAB Attribute Logic Tests")
        # Scenario: Requirements are very low, preobtained is high.
        # Student takes 10 empty courses (0 AU). Should pass.
        courses = [Course(f"EX{i}", num_credits=1.0) for i in range(10)]
        v = ConstraintVerifier(courses)
        
        # Override constraints for this test to simulate "Already Satisfied"
        v.constraints["ceab_math"] = 100
        v.constraints["preobtained_math"] = 150 # 150 > 100, deficit is 0
        
        self.assertTrue(v.verify_ceab_requirements()["Math"][0])

    def test_ceab_math_ns_combined_pool_fail(self):
        self._print_header("CEAB Attribute Logic Tests")
        # Scenario: Math and NS individual requirements met, 
        # but the combined 'math_ns' pool is still short.
        courses = [
            Course("MATH101", num_credits=1.0, ceab=CEABAttributes(total_AU=50, mathematics=50)),
            Course("PHYS101", num_credits=1.0, ceab=CEABAttributes(total_AU=50, natural_science=50))
        ]
        v = ConstraintVerifier(courses)
        # Needed: Math 50, NS 50, Combined 150.
        # Provided: Math 50, NS 50, Combined 100 -> Should fail combined.
        v.constraints["ceab_math"] = 50; v.constraints["preobtained_math"] = 0
        v.constraints["ceab_ns"] = 50; v.constraints["preobtained_ns"] = 0
        v.constraints["ceab_math_ns"] = 150; v.constraints["preobtained_math_ns"] = 0
        
        results = v.verify_ceab_requirements()
        self.assertTrue(results["Math"][0])
        self.assertTrue(results["Natural Science"][0])
        self.assertFalse(results["Math & NS"][0])

    def test_ceab_es_ed_hierarchy_pass(self):
        self._print_header("CEAB Attribute Logic Tests")
        # Scenario: Student takes a heavy Design course. 
        # This should contribute to both 'Eng Design' and the 'ES & ED' pool.
        courses = [
            Course("DESIGN_PROJ", num_credits=1.0, 
                   ceab=CEABAttributes(total_AU=100, engineering_design=100, eng_sci_and_design=100))
        ]
        v = ConstraintVerifier(courses)
        v.constraints["ceab_ed"] = 80; v.constraints["preobtained_ed"] = 0
        v.constraints["ceab_es_ed"] = 90; v.constraints["preobtained_es_ed"] = 0
        
        results = v.verify_ceab_requirements()
        self.assertTrue(results["Eng Design"][0])
        self.assertTrue(results["ES & ED"][0])

    def test_ceab_total_au_deficit_fail(self):
        self._print_header("CEAB Attribute Logic Tests")
        # Scenario: All sub-categories (Math, ES, etc.) pass, 
        # but the overall Total AU is insufficient.
        courses = [
            Course("C1", num_credits=1.0, ceab=CEABAttributes(total_AU=50, mathematics=50))
        ]
        v = ConstraintVerifier(courses)
        v.constraints["ceab_math"] = 50; v.constraints["preobtained_math"] = 0
        v.constraints["ceab_total_au"] = 200; v.constraints["preobtained_total_au"] = 0
        
        results = v.verify_ceab_requirements()
        self.assertTrue(results["Math"][0])
        self.assertFalse(results["Total AU"][0])

    def test_ceab_complementary_studies_pass(self):
        self._print_header("CEAB Attribute Logic Tests")
        # Scenario: Specifically checking the CS bucket.
        courses = [
            Course("PHIL101", num_credits=1.0, ceab=CEABAttributes(total_AU=30, complementary_studies=30)),
            Course("HIST101", num_credits=1.0, ceab=CEABAttributes(total_AU=30, complementary_studies=30))
        ]
        v = ConstraintVerifier(courses)
        v.constraints["ceab_cs"] = 50; v.constraints["preobtained_cs"] = 0
        
        results = v.verify_ceab_requirements()
        self.assertTrue(results["Comp Studies"][0])

if __name__ == "__main__":
    unittest.main()