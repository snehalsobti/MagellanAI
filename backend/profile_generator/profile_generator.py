# backend/profile_generator/profile_generator.py

import random

from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
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
        Generate a random but valid semester-aware profile.

        Simplified term model (for now):
          - Capstone is the ONLY allowed Y course
          - Choose exactly: 9 F courses + 9 S courses + 1 Y capstone
          - Schedule template:
              3F: 5 F
              3S: 5 S
              4F: 4 F + capstone (Y)
              4S: 4 S + capstone (Y)

        Preferences are soft: used only to bias selections when possible.
        """

        rng = random.Random(seed)

        # ---------------------------------------------
        # Normalize preferences - preserve order, dedupe by code
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
        if preferences_invalid:
            preferences_clean = [c for c in preferences_clean if c in available_codes]

        # ---------------------------------------------
        # Pools (exclude ALL non-capstone Y courses)
        # ---------------------------------------------
        # Capstone list must exist in dataset
        capstones_available = [
            code for code in CourseConstants.CAPSTONE_CODES if self._exists(code)
        ]
        if not capstones_available:
            raise ValueError("No capstone available in dataset!")

        # Main generation loop (restart if we get stuck)
        while True:
            # Semester grid: [3F, 3S, 4F, 4S]
            semester_plan: list[list[Course]] = [[], [], [], []]

            # Track chosen unique courses by code
            chosen_codes: set[str] = set()
            unique_courses: list[Course] = []

            # Credit tracking uses UNIQUE courses only
            credits = 0.0

            # Preference tracking
            preferences_used: list[str] = []

            # Slot targets (excluding the capstone duplication rule)
            # After we place capstone in (4F,4S), we must fill:
            #   F courses: 9 total (5 in 3F, 4 in 4F)
            #   S courses: 9 total (5 in 3S, 4 in 4S)
            remaining_F = 9
            remaining_S = 9

            # -----------------------------------------------------
            # Step 1) Choose capstone (Y) and place into 4F + 4S
            # -----------------------------------------------------
            preferred_capstones = [c for c in preferences_clean if c in capstones_available]
            chosen_cap_code = preferred_capstones[0] if preferred_capstones else rng.choice(capstones_available)

            capstone = self._find_course(chosen_cap_code)  # should exist
            if capstone is None:
                raise ValueError(f"Capstone {chosen_cap_code} missing from dataset unexpectedly.")

            # Must be Y-term capstone (your dataset should have it as Y)
            # Even if term isn't "Y" due to data issues, we still treat it as the year-long course.
            if not self._add_course(
                course=capstone,
                semester_plan=semester_plan,
                unique_courses=unique_courses,
                chosen_codes=chosen_codes,
                preferences_clean=preferences_clean,
                preferences_used=preferences_used,
                credits_ref=lambda v=None: credits if v is None else None,
                add_credit=True,
                force_capstone_year4=True,
            ):
                # If somehow cannot place, restart
                continue

            credits += capstone.num_credits
            # Capstone takes one slot in 4F and 4S (already placed), leaving:
            # 4F needs 4 more F courses, 4S needs 4 more S courses

            # -----------------------------------------------------
            # Build filtered course pools for this run
            #   - exclude capstone codes (we already placed one)
            #   - exclude all non-capstone Y courses
            # -----------------------------------------------------
            def is_allowed_noncap(course: Course) -> bool:
                if course.course_code in CourseConstants.CAPSTONE_CODES:
                    return False
                # only allow F or S (no other Y courses for now)
                return course.term in ("F", "S")

            F_pool = [c for c in self.courses if is_allowed_noncap(c) and c.term == "F"]
            S_pool = [c for c in self.courses if is_allowed_noncap(c) and c.term == "S"]

            # -----------------------------------------------------
            # Step 2) Required — ECE472H1 (choose F or S offering)
            # -----------------------------------------------------
            ece472_offerings = [c for c in self.courses if c.course_code == "ECE472H1" and c.term in ("F", "S")]
            if not ece472_offerings:
                raise ValueError("ECE472H1 missing from dataset!")

            # Prefer an offering that fits remaining slots (and preferences later)
            # Default: if we still need more F than S, choose F offering; else S.
            desired_term = "F" if remaining_F >= remaining_S else "S"
            ece472 = self._pick_offering_by_term_preference(
                offerings=ece472_offerings,
                desired_term=desired_term,
                rng=rng,
            )

            if ece472.term == "F":
                if remaining_F <= 0:
                    # try the S offering instead
                    alt = self._pick_offering_by_term_preference(ece472_offerings, "S", rng)
                    if alt.term == "S" and remaining_S > 0:
                        ece472 = alt
                    else:
                        continue
                remaining_F -= 1
            else:
                if remaining_S <= 0:
                    alt = self._pick_offering_by_term_preference(ece472_offerings, "F", rng)
                    if alt.term == "F" and remaining_F > 0:
                        ece472 = alt
                    else:
                        continue
                remaining_S -= 1

            if not self._place_fs_course(ece472, semester_plan, chosen_codes, unique_courses, preferences_clean, preferences_used):
                continue
            credits += ece472.num_credits

            # -----------------------------------------------------
            # Step 3) Breadth — select 4 kernel areas (1–6), pick 1 kernel course in each
            # Must respect remaining_F / remaining_S.
            # -----------------------------------------------------
            kernel_by_area = self._group_kernel_courses_by_area(allowed_terms=("F", "S"))
            all_kernel_areas = list(kernel_by_area.keys())
            if len(all_kernel_areas) < 4:
                raise ValueError("Not enough kernel areas available (need ≥4).")

            kernel_areas = rng.sample(all_kernel_areas, 4)
            restart = False

            for area in kernel_areas:
                kernels = [
                    c for c in kernel_by_area[area]
                    if c.course_code not in chosen_codes
                ]
                # Must also respect remaining slots by term
                kernels = [
                    c for c in kernels
                    if (c.term == "F" and remaining_F > 0) or (c.term == "S" and remaining_S > 0)
                ]
                if not kernels:
                    restart = True
                    break

                # Prefer preferred kernels if possible
                preferred_kernels = [c for c in kernels if c.course_code in preferences_clean]
                kc = preferred_kernels[0] if preferred_kernels else rng.choice(kernels)

                if kc.term == "F":
                    remaining_F -= 1
                else:
                    remaining_S -= 1

                if not self._place_fs_course(kc, semester_plan, chosen_codes, unique_courses, preferences_clean, preferences_used):
                    restart = True
                    break
                credits += kc.num_credits

            if restart:
                continue

            # -----------------------------------------------------
            # Step 4) Depth — choose 2 of those areas, add 2 more courses in each area
            # IMPORTANT: depth extras may be kernel OR non-kernel.
            # Must respect remaining_F / remaining_S.
            # -----------------------------------------------------
            depth_areas = rng.sample(kernel_areas, 2)
            depth_extra_count = 0

            for area in depth_areas:
                pool = [
                    c for c in self.courses
                    if c.area == area
                    and c.term in ("F", "S")
                    and c.course_code not in chosen_codes
                    and c.course_code not in CourseConstants.CAPSTONE_CODES
                ]
                # respect remaining slots
                pool = [
                    c for c in pool
                    if (c.term == "F" and remaining_F > 0) or (c.term == "S" and remaining_S > 0)
                ]

                if len(pool) < 2:
                    restart = True
                    break

                chosen_list: list[Course] = []

                preferred_pool = [c for c in pool if c.course_code in preferences_clean]
                rng.shuffle(preferred_pool)

                # Fill from preferred first
                for c in preferred_pool:
                    if len(chosen_list) == 2:
                        break
                    chosen_list.append(c)

                # Fill remainder from general pool
                if len(chosen_list) < 2:
                    remaining_needed = 2 - len(chosen_list)
                    fallback = [c for c in pool if c.course_code not in {x.course_code for x in chosen_list}]
                    if len(fallback) < remaining_needed:
                        restart = True
                        break
                    chosen_list.extend(rng.sample(fallback, remaining_needed))

                if len(chosen_list) < 2:
                    restart = True
                    break

                # Add selected depth courses
                for c in chosen_list:
                    if c.term == "F":
                        if remaining_F <= 0:
                            restart = True
                            break
                        remaining_F -= 1
                    else:
                        if remaining_S <= 0:
                            restart = True
                            break
                        remaining_S -= 1

                    if not self._place_fs_course(c, semester_plan, chosen_codes, unique_courses, preferences_clean, preferences_used):
                        restart = True
                        break
                    credits += c.num_credits
                    depth_extra_count += 1

                if restart:
                    break

            if restart or depth_extra_count != 4:
                continue

            # -----------------------------------------------------
            # Step 5) Fill remaining F slots first, then remaining S slots
            # Must end at exactly 10.0 credits and 5 courses in each semester.
            # -----------------------------------------------------
            # Sanity: credits should now be 1.0 + (some number)*0.5
            # Remaining slots correspond to remaining_F and remaining_S
            if remaining_F < 0 or remaining_S < 0:
                continue

            # Fill Fall slots
            if not self._fill_term_slots(
                term="F",
                count=remaining_F,
                pool=F_pool,
                rng=rng,
                semester_plan=semester_plan,
                chosen_codes=chosen_codes,
                unique_courses=unique_courses,
                preferences_clean=preferences_clean,
                preferences_used=preferences_used,
            ):
                continue

            credits += 0.5 * remaining_F
            remaining_F = 0

            # Fill Spring slots
            if not self._fill_term_slots(
                term="S",
                count=remaining_S,
                pool=S_pool,
                rng=rng,
                semester_plan=semester_plan,
                chosen_codes=chosen_codes,
                unique_courses=unique_courses,
                preferences_clean=preferences_clean,
                preferences_used=preferences_used,
            ):
                continue

            credits += 0.5 * remaining_S
            remaining_S = 0

            # -----------------------------------------------------
            # Final structural sanity checks
            # -----------------------------------------------------
            # Exact semester sizes
            if not (len(semester_plan[0]) == 5 and len(semester_plan[1]) == 5 and len(semester_plan[2]) == 5 and len(semester_plan[3]) == 5):
                continue

            # Exact credits = 10.0 (unique courses only)
            if abs(credits - 10.0) > 1e-6:
                continue

            # Preferences skipped
            preferences_skipped = [c for c in preferences_clean if c not in preferences_used]
            preferences_skipped = preferences_skipped + preferences_invalid

            kernel_areas.sort()
            depth_areas.sort()

            result = {
                "semester_plan": semester_plan,          # 4x5 grid (capstone duplicated across 4F/4S)
                "courses": unique_courses,               # unique courses (no duplicates)
                "total_credits": credits,
                "kernel_areas_selected": kernel_areas,
                "depth_areas_selected": depth_areas,
                "preferences_requested": preferences,
                "preferences_used": preferences_used,
                "preferences_skipped": preferences_skipped,
                "seed_used": seed,
            }

            # Verifier: your updated verifier expects semester_courses (2D list)
            verifier = ConstraintVerifier(semester_plan)
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

    def _group_kernel_courses_by_area(self, allowed_terms=("F", "S")) -> dict[int, list[Course]]:
        out: dict[int, list[Course]] = {}
        for c in self.courses:
            if c.kernel_course and 1 <= (c.area or -999) <= 6 and c.term in allowed_terms:
                out.setdefault(c.area, []).append(c)
        return out

    def _pick_offering_by_term_preference(self, offerings: list[Course], desired_term: str, rng: random.Random) -> Course:
        desired = [c for c in offerings if c.term == desired_term]
        if desired:
            return rng.choice(desired)
        return rng.choice(offerings)

    def _place_fs_course(
        self,
        course: Course,
        semester_plan: list[list[Course]],
        chosen_codes: set[str],
        unique_courses: list[Course],
        preferences_clean: list[str],
        preferences_used: list[str],
    ) -> bool:
        """
        Place an F or S course into the earliest semester with space:
          F -> 3F first, then 4F
          S -> 3S first, then 4S
        """
        if course.course_code in chosen_codes:
            return False
        if course.term not in ("F", "S"):
            return False

        # Determine target semesters based on term
        if course.term == "F":
            targets = [0, 2]  # 3F, 4F
        else:
            targets = [1, 3]  # 3S, 4S

        placed = False
        for idx in targets:
            if len(semester_plan[idx]) < 5:
                semester_plan[idx].append(course)
                placed = True
                break

        if not placed:
            return False

        chosen_codes.add(course.course_code)
        unique_courses.append(course)

        if course.course_code in preferences_clean and course.course_code not in preferences_used:
            preferences_used.append(course.course_code)

        return True

    def _fill_term_slots(
        self,
        term: str,
        count: int,
        pool: list[Course],
        rng: random.Random,
        semester_plan: list[list[Course]],
        chosen_codes: set[str],
        unique_courses: list[Course],
        preferences_clean: list[str],
        preferences_used: list[str],
    ) -> bool:
        """
        Fill exactly `count` slots of the given term using the provided pool.
        Preferences are used as a soft bias.
        """
        if count == 0:
            return True

        # Build candidate list excluding chosen codes
        available = [c for c in pool if c.course_code not in chosen_codes]

        if len(available) < count:
            return False

        preferred_available = [c for c in available if c.course_code in preferences_clean]
        # Try preferred first, then fallback
        picks: list[Course] = []

        # Pick preferred without duplicates
        rng.shuffle(preferred_available)
        for c in preferred_available:
            if len(picks) == count:
                break
            if c.course_code not in {x.course_code for x in picks}:
                picks.append(c)

        if len(picks) < count:
            remaining_needed = count - len(picks)
            fallback = [c for c in available if c.course_code not in {x.course_code for x in picks}]
            if len(fallback) < remaining_needed:
                return False
            picks.extend(rng.sample(fallback, remaining_needed))

        # Place them
        for c in picks:
            if not self._place_fs_course(
                c, semester_plan, chosen_codes, unique_courses, preferences_clean, preferences_used
            ):
                return False

        return True

    def _add_course(
        self,
        course: Course,
        semester_plan: list[list[Course]],
        unique_courses: list[Course],
        chosen_codes: set[str],
        preferences_clean: list[str],
        preferences_used: list[str],
        credits_ref,
        add_credit: bool,
        force_capstone_year4: bool,
    ) -> bool:
        """
        Internal helper currently only used for capstone placement.
        Places capstone in Year 4 (4F + 4S) by construction.
        """
        if course.course_code in chosen_codes:
            return False

        # Capstone placement: force Year 4
        if force_capstone_year4:
            # add to both 4F and 4S if space
            if len(semester_plan[2]) >= 5 or len(semester_plan[3]) >= 5:
                return False
            semester_plan[2].append(course)
            semester_plan[3].append(course)
        else:
            return False  # not used for now

        chosen_codes.add(course.course_code)
        unique_courses.append(course)

        if course.course_code in preferences_clean and course.course_code not in preferences_used:
            preferences_used.append(course.course_code)

        return True
