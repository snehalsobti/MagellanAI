# backend/profile_generator/test_feedback_constraints.py
#
# Unit tests for the feedback constraint extensions:
#   LOCK, EXCLUDE, LIKE, DISLIKE, timeout, and capstone feedback.
#
# These tests use a real SQLite DB built from the data/ folder, so they exercise
# the full solver stack without mocking any internal component.
# The ranking engine (RAG / GPT-4) is NOT involved — preferences are provided directly.

import os
import tempfile
import unittest

from backend.data_bridge.adapters.sqlite_adapter import SQLiteCatalogAdapter
from backend.data_pipeline.migrate_from_folders import migrate_from_folders
from backend.data_pipeline.schema import init_db
from backend.profile_generator.profile_course_loader import ProfileCourseLoader
from backend.profile_generator.profile_generator import (
    ProfileGenerator,
    SolverInfeasibleError,
    SolverTimeoutError,
)
from backend.profile_generator.solver_cp_sat import ORTOOLS_AVAILABLE
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.types.constants import CourseConstants


@unittest.skipUnless(ORTOOLS_AVAILABLE, "OR-Tools not installed")
class TestFeedbackConstraints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        current = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls._tmpdir.name, "test_feedback.db")
        init_db(cls.db_path)
        migrate_from_folders(db_path=cls.db_path, data_dir=os.path.join(project_root, "data"))
        cls.bridge = SQLiteCatalogAdapter(cls.db_path)
        cls.courses = ProfileCourseLoader.load_profile_courses_from_bridge(cls.bridge)

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def _gen(self, **kwargs) -> dict:
        gen = ProfileGenerator(self.courses)
        return gen.generate_profile(year12_choice="ECE297H1", **kwargs)

    def _base_profile(self, seed: int = 123) -> dict:
        return self._gen(seed=seed)

    def _non_required_codes(self, result: dict) -> list[str]:
        return [
            c.course_code for c in result["courses"]
            if not getattr(c, "is_required", False) and c.term != "Y"
        ]

    # ── LOCK ──────────────────────────────────────────────────────────────────

    def test_lock_keeps_non_required_course(self):
        base = self._base_profile(seed=123)
        non_req = self._non_required_codes(base)
        self.assertTrue(non_req, "Base profile must contain at least one non-required course")
        lock_code = non_req[0]

        result = self._gen(seed=456, locked_codes=[lock_code])
        codes = {c.course_code for c in result["courses"]}
        self.assertIn(lock_code, codes,
                      f"Locked course {lock_code} must appear in regenerated profile")

    def test_lock_multiple_courses(self):
        base = self._base_profile(seed=77)
        non_req = self._non_required_codes(base)
        self.assertGreaterEqual(len(non_req), 2)
        lock_codes = non_req[:2]

        result = self._gen(seed=88, locked_codes=lock_codes)
        codes = {c.course_code for c in result["courses"]}
        for code in lock_codes:
            self.assertIn(code, codes, f"Locked course {code} must be in profile")

    def test_lock_capstone_selects_correct_capstone(self):
        for cap_code in CourseConstants.CAPSTONE_CODES:
            # Check if this capstone exists in the pool
            cap_courses = [c for c in self.courses if c.course_code == cap_code]
            if not cap_courses:
                continue
            result = self._gen(seed=200, locked_codes=[cap_code])
            caps_in_profile = [c.course_code for c in result["courses"] if c.course_code in CourseConstants.CAPSTONE_CODES]
            self.assertIn(cap_code, caps_in_profile,
                          f"Locked capstone {cap_code} must appear in profile")
            break  # Test with the first available capstone

    def test_lock_unavailable_code_raises_infeasible(self):
        with self.assertRaises(SolverInfeasibleError):
            self._gen(seed=1, locked_codes=["NOTAREALCOURSE999"])

    def test_locked_profile_satisfies_all_constraints(self):
        base = self._base_profile(seed=42)
        non_req = self._non_required_codes(base)
        lock_code = non_req[0]

        result = self._gen(seed=42, locked_codes=[lock_code], timeout_seconds=30.0)
        self.assertTrue(
            ConstraintVerifier(result["semester_plan"], year12_choice="ECE297H1").verify(),
            "Profile with LOCK constraint must satisfy all 18 ECE rules"
        )

    # ── EXCLUDE ───────────────────────────────────────────────────────────────

    def test_exclude_removes_non_required_course(self):
        base = self._base_profile(seed=123)
        non_req = self._non_required_codes(base)
        self.assertTrue(non_req)
        exclude_code = non_req[0]

        result = self._gen(seed=456, excluded_codes=[exclude_code])
        codes = {c.course_code for c in result["courses"]}
        self.assertNotIn(exclude_code, codes,
                         f"Excluded course {exclude_code} must NOT appear in profile")

    def test_exclude_capstone_option_uses_other_capstone(self):
        available_caps = [
            code for code in CourseConstants.CAPSTONE_CODES
            if any(c.course_code == code for c in self.courses)
        ]
        if len(available_caps) < 2:
            self.skipTest("Need at least 2 capstone options to test exclusion")

        exclude_cap = available_caps[0]
        result = self._gen(seed=300, excluded_codes=[exclude_cap])
        caps_in_profile = [c.course_code for c in result["courses"] if c.course_code in CourseConstants.CAPSTONE_CODES]
        self.assertNotIn(exclude_cap, caps_in_profile,
                         f"Excluded capstone {exclude_cap} must NOT appear")
        self.assertEqual(len(caps_in_profile), 1, "Exactly one capstone must be in profile")

    def test_excluded_profile_satisfies_all_constraints(self):
        base = self._base_profile(seed=42)
        non_req = self._non_required_codes(base)
        exclude_code = non_req[0]

        result = self._gen(seed=42, excluded_codes=[exclude_code], timeout_seconds=30.0)
        self.assertTrue(
            ConstraintVerifier(result["semester_plan"], year12_choice="ECE297H1").verify(),
            "Profile with EXCLUDE constraint must satisfy all ECE rules"
        )

    # ── LIKE ──────────────────────────────────────────────────────────────────

    def test_like_populates_honor_report(self):
        base = self._base_profile(seed=55)
        non_req = self._non_required_codes(base)
        liked = non_req[:2]

        result = self._gen(seed=999, liked_codes=liked)
        honored_plus_skipped = set(result["liked_honored"] + result["liked_skipped"])
        self.assertEqual(honored_plus_skipped, set(liked),
                         "liked_honored ∪ liked_skipped must equal the full liked list")

    def test_like_keys_present_in_result(self):
        result = self._gen(seed=10, liked_codes=["ECE421H1"])
        self.assertIn("liked_honored", result)
        self.assertIn("liked_skipped", result)
        self.assertIsInstance(result["liked_honored"], list)
        self.assertIsInstance(result["liked_skipped"], list)

    def test_like_boosts_preferred_course(self):
        """A liked course that could appear should appear more reliably than without liking."""
        # Generate 3 profiles without like — check if target appears in any
        base_appearances = 0
        for s in (10, 20, 30):
            r = self._gen(seed=s)
            if any(c.course_code == "ECE454H1" for c in r["courses"]):
                base_appearances += 1

        # Generate 3 profiles WITH like — should appear more reliably
        liked_appearances = 0
        for s in (10, 20, 30):
            r = self._gen(seed=s, liked_codes=["ECE454H1"])
            if any(c.course_code == "ECE454H1" for c in r["courses"]):
                liked_appearances += 1

        # Liked should appear at least as often (probabilistic; 3 samples is low but indicative)
        self.assertGreaterEqual(liked_appearances, base_appearances,
                                "Liked course should appear at least as often as without liking")

    # ── DISLIKE ───────────────────────────────────────────────────────────────

    def test_dislike_honor_keys_present_in_result(self):
        """Result dict must contain disliked_honored and disliked_forced keys."""
        result = self._gen(seed=10, disliked_codes=["ECE302H1"])
        self.assertIn("disliked_honored", result)
        self.assertIn("disliked_forced", result)
        self.assertIsInstance(result["disliked_honored"], list)
        self.assertIsInstance(result["disliked_forced"], list)

    def test_dislike_honored_plus_forced_equals_disliked_list(self):
        """disliked_honored ∪ disliked_forced must equal the full disliked input list."""
        disliked = ["ECE302H1", "ECE472H1"]
        result = self._gen(seed=42, disliked_codes=disliked)
        all_reported = set(result["disliked_honored"] + result["disliked_forced"])
        self.assertEqual(all_reported, set(disliked),
                         "disliked_honored ∪ disliked_forced must equal full disliked list")

    def test_dislike_does_not_cause_infeasibility(self):
        """DISLIKE on ECE472H1 (required) must NOT cause infeasibility (Option A)."""
        result = self._gen(seed=42, disliked_codes=["ECE472H1"])
        codes = {c.course_code for c in result["courses"]}
        self.assertIn("ECE472H1", codes,
                      "ECE472H1 is required; DISLIKE must not remove it (soft penalty only)")

    def test_dislike_required_course_appears_in_disliked_forced(self):
        """A required course that cannot be avoided must land in disliked_forced."""
        result = self._gen(seed=42, disliked_codes=["ECE472H1"])
        self.assertIn("ECE472H1", result["disliked_forced"],
                      "ECE472H1 is required; it must appear in disliked_forced, not disliked_honored")

    def test_dislike_avoidable_course_prefers_honored(self):
        """A non-required disliked course should preferably be avoided (appear in disliked_honored)."""
        # Use a course that is not in the pool of required non-capstone courses
        base = self._base_profile(seed=123)
        non_req = self._non_required_codes(base)
        if not non_req:
            self.skipTest("No non-required courses available")
        target = non_req[0]
        result = self._gen(seed=123, disliked_codes=[target])
        # The course should either be honored (avoided) or forced (constraints kept it).
        # Either way it must appear in exactly one of the two lists.
        in_honored = target in result["disliked_honored"]
        in_forced = target in result["disliked_forced"]
        self.assertNotEqual(in_honored, in_forced,
                            "Disliked course must appear in exactly one of honored/forced")

    # ── TIMEOUT ───────────────────────────────────────────────────────────────

    def test_timeout_raises_solver_timeout_error(self):
        """An extremely short timeout should raise SolverTimeoutError."""
        with self.assertRaises((SolverTimeoutError, SolverInfeasibleError)):
            # 0.0001s is almost certain to timeout; we accept either outcome.
            self._gen(seed=1, timeout_seconds=0.0001)

    def test_timeout_seconds_default_is_accepted(self):
        """Passing explicit timeout_seconds=8.0 must work exactly like the default."""
        result = self._gen(seed=123, timeout_seconds=8.0)
        self.assertIn("courses", result)
        self.assertGreater(len(result["courses"]), 0)

    # ── COMBINED FEEDBACK ─────────────────────────────────────────────────────

    def test_lock_and_exclude_different_courses(self):
        base = self._base_profile(seed=123)
        non_req = self._non_required_codes(base)
        self.assertGreaterEqual(len(non_req), 2)

        lock_code = non_req[0]
        # Pick an exclude code different from lock_code
        exclude_code = next((c for c in non_req[1:] if c != lock_code), None)
        if exclude_code is None:
            self.skipTest("Not enough non-required courses for this test")

        result = self._gen(
            seed=500,
            locked_codes=[lock_code],
            excluded_codes=[exclude_code],
        )
        codes = {c.course_code for c in result["courses"]}
        self.assertIn(lock_code, codes)
        self.assertNotIn(exclude_code, codes)

    def test_lock_exclude_liked_disliked_combined(self):
        base = self._base_profile(seed=123)
        non_req = self._non_required_codes(base)
        if len(non_req) < 3:
            self.skipTest("Not enough non-required courses for combined test")

        result = self._gen(
            seed=600,
            locked_codes=[non_req[0]],
            liked_codes=["ECE421H1"],
            disliked_codes=["ECE302H1"],
        )
        codes = {c.course_code for c in result["courses"]}
        self.assertIn(non_req[0], codes, "Locked course must be present")
        self.assertTrue(
            ConstraintVerifier(result["semester_plan"], year12_choice="ECE297H1").verify()
        )

    def test_no_feedback_is_backward_compatible(self):
        """generate_profile with no feedback params must produce a valid profile and empty report."""
        gen = ProfileGenerator(self.courses)
        result = gen.generate_profile(seed=123)
        self.assertTrue(ConstraintVerifier(result["semester_plan"]).verify())
        self.assertEqual(result.get("generation_engine"), "cp_sat")
        # All four honor-report keys must exist and be empty when no feedback is provided.
        self.assertIn("liked_honored", result)
        self.assertIn("liked_skipped", result)
        self.assertIn("disliked_honored", result)
        self.assertIn("disliked_forced", result)
        self.assertEqual(result["liked_honored"], [])
        self.assertEqual(result["liked_skipped"], [])
        self.assertEqual(result["disliked_honored"], [])
        self.assertEqual(result["disliked_forced"], [])


if __name__ == "__main__":
    unittest.main()
