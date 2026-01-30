# integration_test/test_full_flow.py

import unittest
from pathlib import Path

from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.profile_generator.profile_generator import ProfileGenerator
from backend.profile_generator.technical_course_loader import TechnicalCourseLoader
from backend.profile_generator.profile_printer import ProfilePrinter
from backend.course_query_system.basic_query import load_course_details_index
from backend.ranking_engine.rag_model import rag_model

class TestFullFlow(unittest.TestCase):

    def setUp(self):
        """
        Load course dataset once for all tests.
        """
        root = Path(__file__).resolve().parents[1] # Project root - parent of integration_test
        data_path = root / "data" / "courses_description.ods"

        self.data_path = data_path
        self.technical_courses = TechnicalCourseLoader.load_technical_courses(
            root / "data" / "technical_courses.ods"
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
            data_path=self.data_path,
        )

        print("\n===== RAG Model Output (Preferred Course Codes) =====")
        print(preferred_courses)

        # ----------------------------------------
        # 3. Generate profile with these preferences
        # ----------------------------------------
        gen = ProfileGenerator(self.technical_courses)

        result = gen.generate_profile(
            seed=123,                  # deterministic
            preferences=preferred_courses
        )

        # ----------------------------------------
        # 4. Pretty-print the final schedule
        # ----------------------------------------

        lookup = load_course_details_index(data_path=self.data_path)
        printer = ProfilePrinter(lookup)

        printer.print_profile(result)

        self.assertTrue(ConstraintVerifier(result["semester_plan"]).verify())


if __name__ == "__main__":
    unittest.main()
