# integration_test/test_feedback_flow.py
#
# End-to-end tests for the interactive feedback loop feature.
# Exercises the full pipeline: ProfileGenerator → ConstraintVerifier
# without involving the ranking engine (GPT-4 / RAG).
#
# These tests are the primary automation coverage for the feedback loop because
# the ranking engine is not involved in regeneration — feedback regeneration is
# fully deterministic (modulo CP-SAT search order) and testable end-to-end.

import unittest
from pathlib import Path

from backend.data_bridge.adapters.sqlite_adapter import SQLiteCatalogAdapter
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.profile_generator.profile_generator import (
    ProfileGenerator,
    SolverInfeasibleError,
    SolverTimeoutError,
)
from backend.profile_generator.profile_course_loader import ProfileCourseLoader
from backend.profile_generator.solver_cp_sat import ORTOOLS_AVAILABLE
from backend.types.constants import CourseConstants


@unittest.skipUnless(ORTOOLS_AVAILABLE, "OR-Tools not installed")
class TestFeedbackFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.db_path = root / "data" / "magellan.db"
        if not cls.db_path.exists():
            raise FileNotFoundError(
                f"{cls.db_path} not found. Build it with:\n"
                "python3 -m backend.data_pipeline.cli init-db && "
                "python3 -m backend.data_pipeline.cli migrate-from-folders --data-dir data"
            )
        cls.bridge = SQLiteCatalogAdapter(cls.db_path)
        cls.profile_courses = ProfileCourseLoader.load_profile_courses_from_bridge(cls.bridge)

    def _gen(self, **kwargs) -> dict:
        return ProfileGenerator(self.profile_courses).generate_profile(
            year12_choice="ECE297H1", **kwargs
        )

    def _base(self, seed: int = 123) -> dict:
        return self._gen(seed=seed, preferences=["ECE421H1", "ECE454H1", "ECE444H1",
                                                  "ECE302H1", "ECE345H1", "ECE472H1"])

    def _non_required(self, result: dict) -> list[str]:
        return [
            c.course_code for c in result["courses"]
            if not getattr(c, "is_required", False) and c.term != "Y"
        ]

    # ── LOCK integration ──────────────────────────────────────────────────────

    def test_lock_constraint_end_to_end(self):
        """LOCK a course from a generated profile, regenerate, verify it still appears."""
        base = self._base()
        non_req = self._non_required(base)
        self.assertTrue(non_req)
        lock_code = non_req[0]

        result = self._gen(seed=456, preferences=["ECE421H1", "ECE444H1"], locked_codes=[lock_code])
        codes = {c.course_code for c in result["courses"]}
        self.assertIn(lock_code, codes)
        self.assertTrue(ConstraintVerifier(result["semester_plan"], year12_choice="ECE297H1").verify())

    def test_lock_preserves_preference_matching(self):
        """Locking a course that is also a preference counts it in preferences_used."""
        base = self._base()
        non_req = self._non_required(base)
        lock_code = non_req[0]

        result = self._gen(
            seed=789,
            preferences=[lock_code, "ECE421H1", "ECE444H1"],
            locked_codes=[lock_code],
        )
        self.assertIn(lock_code, result["preferences_used"])

    # ── EXCLUDE integration ───────────────────────────────────────────────────

    def test_exclude_constraint_end_to_end(self):
        """EXCLUDE a course from a generated profile, regenerate, verify it's absent."""
        base = self._base()
        non_req = self._non_required(base)
        self.assertTrue(non_req)
        exclude_code = non_req[0]

        result = self._gen(seed=456, preferences=["ECE421H1", "ECE444H1"], excluded_codes=[exclude_code])
        codes = {c.course_code for c in result["courses"]}
        self.assertNotIn(exclude_code, codes)
        self.assertTrue(ConstraintVerifier(result["semester_plan"], year12_choice="ECE297H1").verify())

    def test_exclude_ece472_raises_infeasible(self):
        """ECE472H1 is required; excluding it should cause infeasibility."""
        with self.assertRaises(SolverInfeasibleError):
            self._gen(seed=1, excluded_codes=["ECE472H1"])

    # ── LIKE integration ──────────────────────────────────────────────────────

    def test_liked_honor_report_end_to_end(self):
        """liked_honored ∪ liked_skipped == liked input (partition)."""
        liked = ["ECE421H1", "ECE454H1", "ECE444H1"]
        result = self._gen(seed=123, preferences=[], liked_codes=liked)
        honored_set = set(result["liked_honored"])
        skipped_set = set(result["liked_skipped"])
        self.assertEqual(honored_set | skipped_set, set(liked))
        self.assertEqual(honored_set & skipped_set, set())

    def test_like_with_preferences_end_to_end(self):
        """Preferences and LIKE can coexist without error."""
        result = self._gen(
            seed=42,
            preferences=["ECE302H1", "ECE345H1"],
            liked_codes=["ECE421H1"],
        )
        self.assertTrue(ConstraintVerifier(result["semester_plan"], year12_choice="ECE297H1").verify())
        self.assertIn("liked_honored", result)
        self.assertIn("liked_skipped", result)

    # ── DISLIKE integration ───────────────────────────────────────────────────

    def test_dislike_soft_penalty_does_not_break_constraints(self):
        """Disliking a course (Option A) must never cause infeasibility."""
        result = self._gen(seed=99, disliked_codes=["ECE302H1", "ECE421H1"])
        self.assertTrue(ConstraintVerifier(result["semester_plan"], year12_choice="ECE297H1").verify())

    def test_dislike_required_course_leaves_it_in_profile(self):
        """Disliking ECE472H1 must not remove it (it's required)."""
        result = self._gen(seed=42, disliked_codes=["ECE472H1"])
        codes = {c.course_code for c in result["courses"]}
        self.assertIn("ECE472H1", codes)

    # ── INFEASIBLE + TIMEOUT ──────────────────────────────────────────────────

    def test_lock_nonexistent_course_raises_infeasible(self):
        with self.assertRaises(SolverInfeasibleError):
            self._gen(seed=1, locked_codes=["XXXXXXXXXXX999"])

    def test_tiny_timeout_raises_timeout_or_infeasible(self):
        with self.assertRaises((SolverTimeoutError, SolverInfeasibleError)):
            self._gen(seed=1, timeout_seconds=0.0001)

    # ── COMBINED LOCK + EXCLUDE ───────────────────────────────────────────────

    def test_lock_and_exclude_different_courses_end_to_end(self):
        base = self._base(seed=77)
        non_req = self._non_required(base)
        self.assertGreaterEqual(len(non_req), 2)
        lock_code = non_req[0]
        exclude_code = next((c for c in non_req[1:] if c != lock_code), None)
        if exclude_code is None:
            self.skipTest("Insufficient non-required courses")

        result = self._gen(
            seed=500,
            preferences=["ECE421H1"],
            locked_codes=[lock_code],
            excluded_codes=[exclude_code],
        )
        codes = {c.course_code for c in result["courses"]}
        self.assertIn(lock_code, codes)
        self.assertNotIn(exclude_code, codes)
        self.assertTrue(ConstraintVerifier(result["semester_plan"], year12_choice="ECE297H1").verify())

    # ── CAPSTONE FEEDBACK ─────────────────────────────────────────────────────

    def test_lock_capstone_selects_that_capstone(self):
        available_caps = [
            code for code in CourseConstants.CAPSTONE_CODES
            if any(c.course_code == code for c in self.profile_courses)
        ]
        if not available_caps:
            self.skipTest("No capstone codes found in pool")
        cap_code = available_caps[0]

        result = self._gen(seed=200, locked_codes=[cap_code])
        cap_codes_in_profile = [
            c.course_code for c in result["courses"]
            if c.course_code in CourseConstants.CAPSTONE_CODES
        ]
        self.assertIn(cap_code, cap_codes_in_profile)
        self.assertEqual(len(cap_codes_in_profile), 1)

    def test_capstone_in_both_semester_slots(self):
        """A locked capstone must appear in both 4F and 4S semester slots."""
        available_caps = [
            code for code in CourseConstants.CAPSTONE_CODES
            if any(c.course_code == code for c in self.profile_courses)
        ]
        if not available_caps:
            self.skipTest("No capstone codes found in pool")
        cap_code = available_caps[0]

        result = self._gen(seed=200, locked_codes=[cap_code])
        semester_plan = result["semester_plan"]
        # Capstone is in semester indices 2 (4F) and 3 (4S)
        sem_4f_codes = [c.course_code for c in semester_plan[2]]
        sem_4s_codes = [c.course_code for c in semester_plan[3]]
        self.assertIn(cap_code, sem_4f_codes, "Locked capstone must appear in 4F slot")
        self.assertIn(cap_code, sem_4s_codes, "Locked capstone must appear in 4S slot")

    # ── DIAGNOSTIC SHAPES ─────────────────────────────────────────────────────

    def test_feedback_result_fields_present(self):
        """Result dict always has all four honor-report keys regardless of feedback."""
        result = self._gen(seed=123)
        self.assertIn("liked_honored", result)
        self.assertIn("liked_skipped", result)
        self.assertIn("disliked_honored", result)
        self.assertIn("disliked_forced", result)

    def test_preferences_and_liked_disjoint_in_honor_report(self):
        """preferences_used tracks rank-based preferences; liked_honored tracks liked."""
        prefs = ["ECE421H1", "ECE444H1"]
        liked = ["ECE454H1"]
        result = self._gen(seed=42, preferences=prefs, liked_codes=liked)
        # preferences_used only contains codes from prefs
        for code in result["preferences_used"]:
            self.assertIn(code, prefs)
        # liked_honored only contains codes from liked
        for code in result["liked_honored"]:
            self.assertIn(code, liked)

    def test_dislike_honor_report_fields_partition_disliked_list(self):
        """disliked_honored ∪ disliked_forced must equal the full disliked input list."""
        disliked = ["ECE302H1", "ECE472H1"]
        result = self._gen(seed=42, disliked_codes=disliked)
        all_reported = set(result["disliked_honored"] + result["disliked_forced"])
        self.assertEqual(all_reported, set(disliked),
                         "disliked_honored ∪ disliked_forced must equal full disliked list")

    def test_dislike_required_course_in_disliked_forced(self):
        """ECE472H1 (required engineering economics) must land in disliked_forced."""
        result = self._gen(seed=42, disliked_codes=["ECE472H1"])
        self.assertIn("ECE472H1", result["disliked_forced"],
                      "Required course must be forced, not honored")
        self.assertNotIn("ECE472H1", result["disliked_honored"])

    def test_no_feedback_produces_empty_dislike_report(self):
        """With no feedback, disliked_honored and disliked_forced must both be empty."""
        result = self._gen(seed=123)
        self.assertEqual(result["disliked_honored"], [])
        self.assertEqual(result["disliked_forced"], [])


if __name__ == "__main__":
    unittest.main()
