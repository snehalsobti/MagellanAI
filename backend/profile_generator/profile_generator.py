# backend/profile_generator/profile_generator.py

import os
import random

from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.profile_generator.profile_printer import ProfilePrinter
from backend.profile_generator.technical_course_loader import TechnicalCourseLoader
from backend.types.constants import CourseConstants
from backend.types.course import Course

class ProfileGenerator:

    def __init__(self, technical_courses: list[Course]):
        # Keep ALL rows (even duplicates); we enforce uniqueness by course_code
        self.courses: list[Course] = technical_courses

    # -----------------------------------------------------
    #  Main API
    # -----------------------------------------------------
    def generate_profile(
        self,
        seed: int | None = None,
        preferences: list[str] | None = None,
    ) -> dict:
        """
        Generate a random but valid course list that satisfies all constraints.
        Soft preferences (ranked list of course codes) may be provided.
        """

        rng = random.Random(seed)

        # ---------------------------------------------
        # Normalize preferences — preserve order, dedupe by code
        # ---------------------------------------------
        preferences = preferences or []
        preferred_set = set()
        preferences_clean: list[str] = []
        for code in preferences:
            if code not in preferred_set:
                preferred_set.add(code)
                preferences_clean.append(code)

        # Validate preferred codes
        available_codes = {c.course_code for c in self.courses}
        preferences_invalid = [c for c in preferences_clean if c not in available_codes]

        # Remove invalid prefs from the working preference list
        if preferences_invalid:
            preferences_clean = [c for c in preferences_clean if c in available_codes]

        # Main generation loop (may restart if we get stuck)
        while True:
            plan: list[Course] = []
            chosen_codes: set[str] = set()
            credits = 0.0
            preferences_used: list[str] = []

            # =====================================================
            # 1. Required — ECE472H1
            # =====================================================
            ece472 = self._find_course("ECE472H1")
            if ece472 is None:
                raise ValueError("ECE472H1 missing from dataset!")

            plan.append(ece472)
            chosen_codes.add(ece472.course_code)
            credits += ece472.num_credits
            if ece472.course_code in preferences_clean:
                preferences_used.append(ece472.course_code)

            # =====================================================
            # 2. Required — EXACTLY 1 capstone
            #    Prefer the first preferred capstone if given.
            # =====================================================
            capstones_available = [
                code for code in CourseConstants.CAPSTONE_CODES if self._exists(code)
            ]
            if not capstones_available:
                raise ValueError("No capstone available in dataset!")

            preferred_capstones = [
                code for code in preferences_clean if code in capstones_available
            ]
            if preferred_capstones:
                chosen_cap_code = preferred_capstones[0]
            else:
                chosen_cap_code = rng.choice(capstones_available)

            capstone = self._find_course(chosen_cap_code)
            plan.append(capstone)
            chosen_codes.add(capstone.course_code)
            credits += capstone.num_credits
            if capstone.course_code in preferences_clean:
                preferences_used.append(capstone.course_code)

            # =====================================================
            # 3. Select 4 kernel areas (areas 1–6), unique by course code
            #    Prefer preferred kernels.
            # =====================================================
            kernel_by_area = self._group_kernel_courses_by_area()
            all_kernel_areas = list(kernel_by_area.keys())
            if len(all_kernel_areas) < 4:
                raise ValueError("Not enough kernel areas available (need ≥4).")

            kernel_areas = rng.sample(all_kernel_areas, 4)
            restart = False

            for area in kernel_areas:
                kernels = kernel_by_area[area]

                # Only consider kernels whose course_code isn't already chosen
                unused_kernels = [
                    c for c in kernels if c.course_code not in chosen_codes
                ]
                if not unused_kernels:
                    restart = True
                    break

                preferred_kernels = [
                    c for c in unused_kernels
                    if c.course_code in preferences_clean
                ]

                if preferred_kernels:
                    kc = preferred_kernels[0]
                else:
                    kc = rng.choice(unused_kernels)

                plan.append(kc)
                chosen_codes.add(kc.course_code)
                credits += kc.num_credits

                if kc.course_code in preferences_clean:
                    preferences_used.append(kc.course_code)

            if restart:
                continue  # restart whole loop

            # =====================================================
            # 4. Pick 2 depth areas and select 2 non-kernel courses in each
            #    Prefer preferred courses when possible.
            #    Ensure uniqueness by course_code.
            # =====================================================
            depth_areas = rng.sample(kernel_areas, 2)
            depth_extra: list[Course] = []

            for area in depth_areas:
                # All non-kernel courses in this area whose codes not yet chosen
                pool = [
                    c for c in self.courses
                    if c.area == area
                    and not c.kernel_course
                    and c.course_code not in chosen_codes
                ]

                if len(pool) < 2:
                    restart = True
                    break

                # Track codes chosen within this depth area to avoid duplicates
                local_codes: set[str] = set()
                chosen_list: list[Course] = []

                # Preferred pool
                preferred_pool = [
                    c for c in pool if c.course_code in preferences_clean
                ]

                # Try to fill from preferred_pool
                while len(chosen_list) < 2 and preferred_pool:
                    c = rng.choice(preferred_pool)
                    preferred_pool.remove(c)
                    if c.course_code not in local_codes:
                        chosen_list.append(c)
                        local_codes.add(c.course_code)

                # Fill remainder from general pool
                if len(chosen_list) < 2:
                    needed = 2 - len(chosen_list)
                    fallback = [
                        c for c in pool
                        if c.course_code not in local_codes
                    ]
                    if len(fallback) < needed:
                        restart = True
                        break
                    extra_choices = rng.sample(fallback, needed)
                    for c in extra_choices:
                        if c.course_code not in local_codes:
                            chosen_list.append(c)
                            local_codes.add(c.course_code)

                if len(chosen_list) < 2:
                    restart = True
                    break

                # Add them to the global plan
                for c in chosen_list:
                    plan.append(c)
                    chosen_codes.add(c.course_code)
                    credits += c.num_credits
                    depth_extra.append(c)
                    if c.course_code in preferences_clean:
                        preferences_used.append(c.course_code)

            if restart or len(depth_extra) < 4:
                continue  # restart everything

            # =====================================================
            # 5. Fill courses until exactly 10.0 credits
            #    Prefer remaining preferred courses.
            #    No repetition, no extra capstones.
            # =====================================================
            stuck = 0

            while credits < 10.0:
                available = [
                    c for c in self.courses
                    if c.course_code not in chosen_codes
                    and c.course_code not in CourseConstants.CAPSTONE_CODES
                ]

                if not available:
                    break  # restart

                preferred_available = [
                    c for c in available if c.course_code in preferences_clean
                ]

                candidate_pool = preferred_available if preferred_available else available
                candidate = rng.choice(candidate_pool)

                new_total = credits + candidate.num_credits
                if new_total > 10.0:
                    stuck += 1
                    if stuck > 50:
                        break  # restart
                    continue

                # Accept
                plan.append(candidate)
                chosen_codes.add(candidate.course_code)
                credits = new_total

                if candidate.course_code in preferences_clean:
                    preferences_used.append(candidate.course_code)

            if credits != 10.0:
                continue  # restart

            # =====================================================
            # SUCCESS
            # =====================================================

            preferences_skipped = [c for c in preferences_clean if c not in preferences_used]
            preferences_skipped = preferences_skipped + preferences_invalid

            kernel_areas.sort()
            depth_areas.sort()

            result = {
                "courses": plan,
                "total_credits": credits,
                "kernel_areas_selected": kernel_areas,
                "depth_areas_selected": depth_areas,
                "preferences_requested": preferences,
                "preferences_used": preferences_used,
                "preferences_skipped": preferences_skipped,
                "seed_used": seed,
            }

            verifier = ConstraintVerifier(plan)
            assert verifier.verify(), "Generated profile violates constraints!"

            return result

    # -----------------------------------------------------
    # Helper utilities
    # -----------------------------------------------------
    def _find_course(self, code: str) -> Course | None:
        for c in self.courses:
            if c.course_code == code:
                return c
        return None

    def _exists(self, code: str) -> bool:
        return any(c.course_code == code for c in self.courses)

    def _group_kernel_courses_by_area(self) -> dict[int, list[Course]]:
        out: dict[int, list[Course]] = {}
        for c in self.courses:
            if c.kernel_course and 1 <= c.area <= 6:
                out.setdefault(c.area, []).append(c)
        return out
