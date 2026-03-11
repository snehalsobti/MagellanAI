# integration_test/test_full_flow.py

import unittest
import os
from pathlib import Path

from backend.data_bridge.adapters.sqlite_adapter import SQLiteCatalogAdapter
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.profile_generator.profile_generator import ProfileGenerator
from backend.profile_generator.profile_course_loader import ProfileCourseLoader
from backend.profile_generator.profile_printer import ProfilePrinter
from backend.ranking_engine.rag_model import rag_model

class TestFullFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]  # Project root - parent of integration_test
        cls.db_path = root / "data" / "magellan.db"
        if not cls.db_path.exists():
            raise FileNotFoundError(
                f"{cls.db_path} not found. Build it with: "
                "python3 -m backend.data_pipeline.cli init-db && "
                "python3 -m backend.data_pipeline.cli migrate-from-folders --data-dir data"
            )
        cls.bridge = SQLiteCatalogAdapter(cls.db_path)
        cls.profile_courses = ProfileCourseLoader.load_profile_courses_from_bridge(cls.bridge)
        cls.lookup = cls.bridge.get_course_name_index()

        rag_enabled = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("ALLOW_NETWORK_RAG_TEST") == "1"
        if not rag_enabled:
            print(
                "[integration_test] Network RAG test is skipped. "
                "Set OPENAI_API_KEY and ALLOW_NETWORK_RAG_TEST=1 to enable it."
            )

    def _assert_diagnostics_shape(self, result: dict):
        self.assertIn("generation_engine", result)
        self.assertIn("solver_runtime_ms", result)
        self.assertIn("preference_hit_count", result)
        self.assertIn("preference_weighted_score", result)
        self.assertIn("constraint_diagnostics", result)
        self.assertIsInstance(result["constraint_diagnostics"], dict)
        self.assertIn("ok", result["constraint_diagnostics"])

    def test_profile_generation_cp_sat_with_curated_preferences(self):
        preferred_courses = [
            "ECE421H1",
            "ECE444H1",
            "CSC413H1",
            "ECE454H1",
            "ECE345H1",
            "ECE302H1",
            "ECE320H1",
            "ECE318H1",
            "ECE472H1",
        ]
        gen = ProfileGenerator(self.profile_courses)
        result = gen.generate_profile(seed=123, preferences=preferred_courses, year12_choice="ECE297H1")

        printer = ProfilePrinter(self.lookup)
        printer.print_profile(result)

        self.assertTrue(ConstraintVerifier(result["semester_plan"], year12_choice="ECE297H1").verify())
        self.assertEqual(result.get("generation_engine"), "cp_sat")
        self._assert_diagnostics_shape(result)
        self.assertTrue(result["constraint_diagnostics"]["ok"])

    @unittest.skipUnless(
        os.getenv("OPENAI_API_KEY") and os.getenv("ALLOW_NETWORK_RAG_TEST") == "1",
        "Requires OPENAI_API_KEY and ALLOW_NETWORK_RAG_TEST=1 for networked RAG call",
    )
    def test_rag_to_profile_generation(self):
        """
        Full pipeline:
            RAG -> preferred course codes -> ProfileGenerator -> ProfilePrinter
        """

        # ----------------------------------------
        # 1. Simulated user query
        # ----------------------------------------
        user_prompt = (
            "I want courses related to machine learning, software engineering, "
            "and advanced systems."
        )
        k = 10               # number of semantic chunks to retrieve
        retrieval_k = None   # optional - not used for now

        # ----------------------------------------
        # 2. RAG model → list of course codes
        # ----------------------------------------
        preferred_courses = rag_model(
            user_prompt=user_prompt,
            k=k,
            retrieval_k=retrieval_k,
            bridge=self.bridge,
        )

        print("\n===== RAG Model Output (Preferred Course Codes) =====")
        print(preferred_courses)

        # ----------------------------------------
        # 3. Generate profile with these preferences
        # ----------------------------------------
        gen = ProfileGenerator(self.profile_courses)

        result = gen.generate_profile(
            seed=123,                  # deterministic
            preferences=preferred_courses
        )

        # ----------------------------------------
        # 4. Pretty-print the final schedule
        # ----------------------------------------

        printer = ProfilePrinter(self.lookup)

        printer.print_profile(result)

        self.assertTrue(ConstraintVerifier(result["semester_plan"]).verify())
        self._assert_diagnostics_shape(result)


if __name__ == "__main__":
    unittest.main()
