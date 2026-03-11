# backend/profile_generator/profile_generator.py

from __future__ import annotations

import time

from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.profile_generator.constraint_policy import ConstraintPolicy
from backend.profile_generator.solver_cp_sat import GlobalCpSatProfileSolver
from backend.types.course import Course


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
    ) -> dict:
        started = time.perf_counter()
        policy = ConstraintPolicy.load_default(year12_choice=year12_choice)
        solver = GlobalCpSatProfileSolver(self.courses, policy)

        preferences_clean = self._normalize_preferences(preferences or [])
        solved = solver.solve(preferences_clean, seed=seed)
        if solved is None:
            raise ValueError("Profile generation failed: no feasible solution found.")

        semester_plan = solved.semester_plan
        unique_courses = solved.selected_courses
        selected_codes = {c.course_code for c in unique_courses}
        preferences_used = [code for code in preferences_clean if code in selected_codes]
        preferences_skipped = [code for code in preferences_clean if code not in selected_codes]

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
            "seed_used": seed,
            "generation_engine": "cp_sat",
            "solver_runtime_ms": elapsed_ms,
            "preference_hit_count": len(set(preferences_used)),
            "preference_weighted_score": weighted,
            "constraint_diagnostics": diagnostics,
        }

    @staticmethod
    def _normalize_preferences(preferences: list[str]) -> list[str]:
        seen = set()
        out: list[str] = []
        for code in preferences:
            code_clean = str(code).strip().upper()
            if not code_clean or code_clean in seen:
                continue
            seen.add(code_clean)
            out.append(code_clean)
        return out
