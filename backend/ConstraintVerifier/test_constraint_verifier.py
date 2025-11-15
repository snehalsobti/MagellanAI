# ConstraintVerifier/test_constraint_verifier.py

import unittest

from courses import Course
from CEAB_Attributes import CEABAttributes
from ConstraintVerifier.constraint_verifier import ConstraintVerifier


class TestConstraintVerifier(unittest.TestCase):

    def test_fail_case(self):
        # Creates a list that should fail kernel + depth requirement
        courses = [
            Course("ECE101", area=1, num_credits=1, kernel_course=True),
            Course("ECE102", area=1, num_credits=1),
            Course("ECE201", area=2, num_credits=1, kernel_course=True),
            Course("ECE472", num_credits=1)
        ]

        verifier = ConstraintVerifier(courses)
        self.assertFalse(verifier.verify())

    def test_pass_case(self):
        # Build a list that satisfies all constraints
        courses = [
            # Area 1 (kernel + 2 additional)
            Course("ECE101", area=1, num_credits=2, kernel_course=True),
            Course("ECE102", area=1, num_credits=2),
            Course("ECE103", area=1,  num_credits=2),

            # Area 2 (kernel + 2 additional)
            Course("ECE201", area=2,  num_credits=2, kernel_course=True),
            Course("ECE202", area=2,  num_credits=2),
            Course("ECE203", area=2,  num_credits=2),

            # Area 3 (kernel)
            Course("ECE101", area=3, num_credits=2, kernel_course=True),

            # Area 4 (kernel)
            Course("ECE201", area=4,  num_credits=2, kernel_course=True),

            # Required course
            Course("ECE472", num_credits=4),
        ]

        verifier = ConstraintVerifier(courses)
        self.assertTrue(verifier.verify())


if __name__ == "__main__":
    unittest.main()
