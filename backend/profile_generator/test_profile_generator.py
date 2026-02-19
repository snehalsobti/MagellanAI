# backend/profile_generator/test_profile_generator.py

import os
import tempfile
import unittest

from backend.data_bridge.adapters.sqlite_adapter import SQLiteCatalogAdapter
from backend.data_pipeline.migrate_legacy import migrate_from_legacy
from backend.data_pipeline.schema import init_db
from backend.profile_generator.technical_course_loader import TechnicalCourseLoader
from backend.profile_generator.profile_generator import ProfileGenerator
from backend.profile_generator.profile_printer import ProfilePrinter
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.types.constants import CourseConstants

class TestProfileGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Build a temp SQLite DB from legacy files once for all tests."""
        current = os.path.abspath(__file__)
        profile_generator_dir = os.path.dirname(current)
        backend_dir = os.path.dirname(profile_generator_dir)
        project_root = os.path.dirname(backend_dir)

        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls._tmpdir.name, "test_magellan.db")
        init_db(cls.db_path)
        migrate_from_legacy(db_path=cls.db_path, data_dir=os.path.join(project_root, "data"))

        cls.bridge = SQLiteCatalogAdapter(cls.db_path)
        cls.courses = TechnicalCourseLoader.load_technical_courses_from_bridge(cls.bridge)
        cls.lookup = cls.bridge.get_course_name_index()

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def test_basic_generation(self):
        gen = ProfileGenerator(self.courses)
        result = gen.generate_profile(seed=123)
        verifier = ConstraintVerifier(
            result["semester_plan"],
            breadth_depth_codes=set(result.get("breadth_depth_codes", [])),
        )
        self.assertTrue(verifier.verify())

    def test_seed_determinism(self):
        gen = ProfileGenerator(self.courses)

        r1 = gen.generate_profile(seed=42)
        r2 = gen.generate_profile(seed=42)

        c1 = [c.course_code for c in r1["courses"]]
        c2 = [c.course_code for c in r2["courses"]]

        self.assertEqual(sorted(c1), sorted(c2))

    def test_contains_ece472(self):
        gen = ProfileGenerator(self.courses)
        result = gen.generate_profile(seed=55)

        codes = [c.course_code for c in result["courses"]]
        self.assertIn("ECE472H1", codes)

    def test_exactly_one_capstone(self):
        gen = ProfileGenerator(self.courses)
        result = gen.generate_profile(seed=202)

        caps = [
            c.course_code
            for c in result["courses"]
            if c.course_code in CourseConstants.CAPSTONE_CODES
        ]

        self.assertEqual(len(caps), 1)

    def test_no_repetition(self):
        gen = ProfileGenerator(self.courses)
        result = gen.generate_profile(seed=88)

        codes = [c.course_code for c in result["courses"]]
        self.assertEqual(len(codes), len(set(codes)))

    def test_total_credits_exact(self):
        gen = ProfileGenerator(self.courses)
        result = gen.generate_profile(seed=303)

        self.assertAlmostEqual(result["total_credits"], 10.0, places=6)

    def test_preferences_respected_soft(self):
        gen = ProfileGenerator(self.courses)

        prefs = ["ECE454H1", "ECE302H1", "ECE444H1"]
        result = gen.generate_profile(seed=99, preferences=prefs)

        used = set(result["preferences_used"])
        # At least one preference should appear (soft preference)
        self.assertGreaterEqual(len(used), 1)

        for u in used:
            self.assertIn(u, prefs)

    def test_breadth_depth_constraints(self):
        gen = ProfileGenerator(self.courses)
        result = gen.generate_profile(seed=77)

        verifier = ConstraintVerifier(result["semester_plan"])
        self.assertTrue(verifier.verify_breadth_requirement())
        self.assertTrue(verifier.verify_depth_requirement())

    def test_math_sci_requirement(self):
        gen = ProfileGenerator(self.courses)
        result = gen.generate_profile(seed=999)

        bd = set(result.get("breadth_depth_codes", []))
        unique = result["courses"]

        # At least one area-7 course NOT used for breadth/depth
        ok = any(c.area == 7 and c.course_code not in bd for c in unique)
        self.assertTrue(ok)

    def test_pretty_printer_does_not_crash(self):
        gen = ProfileGenerator(self.courses)
        prefs = ["ECE454H1", "ECE302H1", "ECE444H1", "ECE555H1", "ECE111H1"]
        result = gen.generate_profile(seed=2222, preferences=prefs)

        # Ensure printing works without errors
        try:
            printer = ProfilePrinter(self.lookup)
            printer.print_profile(result)
        except Exception as e:
            self.fail(f"Pretty printer crashed: {e}")


if __name__ == "__main__":
    unittest.main()
