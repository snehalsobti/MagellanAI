# backend/types/constants.py
#
# IMPORTANT: These constants are a CONVENIENCE ALIAS only.
# The Single Source of Truth (SSOT) for all ECE program invariants is:
#   backend/constraint_verifier/constraints.json  →  capstone.codes
#
# If the set of capstone codes ever changes, update constraints.json first.
# This list must stay in sync manually (or via ConstraintPolicy.load_default()
# for runtime use).  Test code and other places that need the list at import
# time (before the DB is available) may continue to reference CAPSTONE_CODES.

class CourseConstants:
    CAPSTONE_CODES = ["ECE496Y1", "APS490Y1", "BME498Y1"]
