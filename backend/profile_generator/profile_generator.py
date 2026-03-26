# backend/profile_generator/profile_generator.py

from __future__ import annotations

import time

from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.profile_generator.constraint_policy import ConstraintPolicy
from backend.profile_generator.solver_cp_sat import GlobalCpSatProfileSolver
from backend.types.course import Course


class SolverTimeoutError(Exception):
    """Raised when the CP-SAT solver times out without finding a feasible solution."""


class SolverInfeasibleError(Exception):
    """Raised when the CP-SAT solver cannot find a feasible solution.

    This typically means the feedback constraints (LOCK / EXCLUDE combinations)
    are too restrictive, or a locked course is not available in the course pool.
    """


class ProfileGenerator:
    """
    CP-SAT profile generation orchestrator.
    """

    def __init__(self, profile_courses: list[Course]):
        self.courses: list[Course] = profile_courses

    def generate_profile(
        self,
        seed: int | None = None,
        preferences: list[str] | None = None,
        year12_choice: str | None = None,
        locked_codes: list[str] | None = None,
        excluded_codes: list[str] | None = None,
        liked_codes: list[str] | None = None,
        disliked_codes: list[str] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict:
        """Generate a course profile.

        All feedback parameters are optional and default to empty / no feedback,
        preserving backward compatibility with callers that do not use feedback.

        Args:
            seed: Random seed for the CP-SAT solver (deterministic runs).
            preferences: Ordered list of preferred course codes (soft objective).
            year12_choice: "ECE295H1" or "ECE297H1" (CEAB baseline selection).
            locked_codes: Courses that MUST appear in the output (hard constraint).
            excluded_codes: Courses that MUST NOT appear in the output (hard constraint).
            liked_codes: Courses to boost in the objective (soft, always safe).
            disliked_codes: Courses to penalise in the objective (soft, Option A –
                never causes infeasibility; course is still placed if constraints require it).
            timeout_seconds: CP-SAT wall-clock limit. Defaults to 30 s for both
                initial generation and regeneration calls.

        Raises:
            SolverTimeoutError: Solver ran out of time without finding a solution.
            SolverInfeasibleError: No feasible solution exists (usually conflicting
                locked / excluded feedback).
            ValueError: Generated profile unexpectedly violates a constraint
                (should never happen in normal operation).
        """
        started = time.perf_counter()
        policy = ConstraintPolicy.load_default(year12_choice=year12_choice)
        solver = GlobalCpSatProfileSolver(self.courses, policy)

        preferences_clean = self._normalize_code_list(preferences or [])
        locked_clean = self._normalize_code_list(locked_codes or [])
        excluded_clean = self._normalize_code_list(excluded_codes or [])
        liked_clean = self._normalize_code_list(liked_codes or [])
        disliked_clean = self._normalize_code_list(disliked_codes or [])
        effective_timeout = timeout_seconds if timeout_seconds is not None else 30.0

        solved, solve_status = solver.solve(
            preferred_codes=preferences_clean,
            seed=seed,
            locked_codes=locked_clean,
            excluded_codes=excluded_clean,
            liked_codes=liked_clean,
            disliked_codes=disliked_clean,
            timeout_seconds=effective_timeout,
        )

        if solved is None:
            if solve_status == 'timeout':
                raise SolverTimeoutError(
                    "Profile generation timed out. Please try again or reduce feedback constraints."
                )
            raise SolverInfeasibleError(
                "No feasible profile found. The feedback constraints may be too restrictive "
                "(e.g. a locked course is unavailable, or locked and excluded courses conflict)."
            )

        semester_plan = solved.semester_plan
        unique_courses = solved.selected_courses
        selected_codes = {c.course_code for c in unique_courses}

        preferences_used = [code for code in preferences_clean if code in selected_codes]
        preferences_skipped = [code for code in preferences_clean if code not in selected_codes]

        liked_honored = [code for code in liked_clean if code in selected_codes]
        liked_skipped = [code for code in liked_clean if code not in selected_codes]

        # For DISLIKE (soft penalty, Option A): "honored" means the course was successfully
        # kept out of the profile; "forced" means it still appeared (constraints required it).
        disliked_honored = [code for code in disliked_clean if code not in selected_codes]
        disliked_forced = [code for code in disliked_clean if code in selected_codes]

        total_credits = sum(c.num_credits for c in unique_courses)
        kernel_areas = sorted({c.area for c in unique_courses if c.kernel_course and c.area in (1, 2, 3, 4, 5, 6)})
        area_counts: dict[int, int] = {}
        for c in unique_courses:
            if c.area in (1, 2, 3, 4, 5, 6):
                area_counts[c.area] = area_counts.get(c.area, 0) + 1
        depth_areas = sorted([a for a, n in area_counts.items() if n >= policy.min_courses_per_depth_area])[:2]

        verifier = ConstraintVerifier(semester_plan, year12_choice=year12_choice)
        diagnostics = verifier.evaluate()
        if not diagnostics["ok"]:
            raise ValueError(f"Generated profile violates constraints: {diagnostics}")

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        weighted = sum((len(preferences_clean) - idx) for idx, code in enumerate(preferences_clean) if code in selected_codes)

        return {
            "semester_plan": semester_plan,
            "courses": unique_courses,
            "total_credits": total_credits,
            "kernel_areas_selected": kernel_areas,
            "depth_areas_selected": depth_areas,
            "preferences_requested": preferences or [],
            "preferences_used": preferences_used,
            "preferences_skipped": preferences_skipped,
            "liked_honored": liked_honored,
            "liked_skipped": liked_skipped,
            "disliked_honored": disliked_honored,
            "disliked_forced": disliked_forced,
            "seed_used": seed,
            "generation_engine": "cp_sat",
            "solver_runtime_ms": elapsed_ms,
            "preference_hit_count": len(set(preferences_used)),
            "preference_weighted_score": weighted,
            "constraint_diagnostics": diagnostics,
        }

    @staticmethod
    def _normalize_code_list(codes: list[str]) -> list[str]:
        """Deduplicate, strip, and uppercase a list of course codes."""
        seen: set[str] = set()
        out: list[str] = []
        for code in codes:
            code_clean = str(code).strip().upper()
            if not code_clean or code_clean in seen:
                continue
            seen.add(code_clean)
            out.append(code_clean)
        return out

    @staticmethod
    def _normalize_preferences(preferences: list[str]) -> list[str]:
        """Backward-compatible alias for _normalize_code_list."""
        return ProfileGenerator._normalize_code_list(preferences)
