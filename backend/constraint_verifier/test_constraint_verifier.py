# backend/constraint_verifier/test_constraint_verifier.py

import unittest

from backend.course import Course
from backend.ceab_attributes import CEABAttributes
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier


class TestConstraintVerifier(unittest.TestCase):

    def test_fail_case(self):
        # Creates a list that should fail kernel + depth requirement
        courses = [
            Course("ECE101H1", area=1, num_credits=0.5, kernel_course=True),
            Course("ECE102H1", area=1, num_credits=0.5),
            Course("ECE201H1", area=2, num_credits=0.5, kernel_course=True),
            Course("ECE472H1", num_credits=0.5),
            Course("ECE496Y1", num_credits=1.0),
        ]

        verifier = ConstraintVerifier(courses)
        self.assertFalse(verifier.verify())

    def test_pass_case(self):
        # Build a list that satisfies all constraints
        courses = [
            # Area 1 (kernel + 2 additional)
            Course("ECE101H1", area=1, num_credits=1.0, kernel_course=True),
            Course("ECE102H1", area=1, num_credits=1.0),
            Course("ECE103H1", area=1,  num_credits=1.0),

            # Area 2 (kernel + 2 additional)
            Course("ECE201H1", area=2,  num_credits=1.0, kernel_course=True),
            Course("ECE202H1", area=2,  num_credits=1.0),
            Course("ECE203H1", area=2,  num_credits=1.0),

            # Area 3 (kernel)
            Course("ECE104H1", area=3, num_credits=1.0, kernel_course=True),

            # Area 4 (kernel)
            Course("ECE205H1", area=4,  num_credits=1.0, kernel_course=True),

            # Required courses
            Course("ECE472H1", num_credits=1.0),
            Course("ECE496Y1", num_credits=1.0),
        ]

        verifier = ConstraintVerifier(courses)
        self.assertTrue(verifier.verify())


if __name__ == "__main__":
    unittest.main()
