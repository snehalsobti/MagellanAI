from __future__ import annotations

from dataclasses import dataclass

from backend.profile_generator.constraint_policy import ConstraintPolicy
from backend.profile_generator.course_pool_builder import CoursePoolBuilder
from backend.types.course import Course

try:
    from ortools.sat.python import cp_model  # type: ignore[reportMissingImports]

    ORTOOLS_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    cp_model = None
    ORTOOLS_AVAILABLE = False


@dataclass(frozen=True)
class ProfileSolveResult:
    semester_plan: list[list[Course]]
    selected_courses: list[Course]


class GlobalCpSatProfileSolver:
    def __init__(self, courses: list[Course], policy: ConstraintPolicy):
        self.courses = courses
        self.policy = policy
        self.pool = CoursePoolBuilder(courses)

    def solve(self, preferred_codes: list[str] | None = None, seed: int | None = None) -> ProfileSolveResult | None:
        if not ORTOOLS_AVAILABLE:
            return None

        preferred_list = preferred_codes or []
        preferred_rank = {code: idx for idx, code in enumerate(preferred_list)}
        capstone_codes = self.pool.capstone_codes()
        if not capstone_codes:
            return None

        noncap_offerings = [
            c for c in self.courses
            if c.term in ("F", "S")
            and not self.pool.is_excluded(c)
            and not self.pool.is_capstone(c)
        ]
        if not noncap_offerings:
            return None

        # Deduplicate by (code, term) in case of duplicates in source list.
        seen = set()
        dedup: list[Course] = []
        for c in noncap_offerings:
            key = (c.course_code, c.term)
            if key in seen:
                continue
            seen.add(key)
            dedup.append(c)
        noncap_offerings = dedup

        code_to_idx: dict[str, list[int]] = {}
        for i, c in enumerate(noncap_offerings):
            code_to_idx.setdefault(c.course_code, []).append(i)

        def _code_any(code: str, pred) -> bool:
            return any(pred(noncap_offerings[i]) for i in code_to_idx.get(code, []))

        def _code_nontech_types(code: str) -> set[str]:
            out: set[str] = set()
            for i in code_to_idx.get(code, []):
                nt = noncap_offerings[i].non_technical_type
                if nt:
                    out.add(str(nt))
            return out

        model = cp_model.CpModel()
        x = [model.NewBoolVar(f"x_{i}") for i in range(len(noncap_offerings))]
        y = {code: model.NewBoolVar(f"y_{code}") for code in code_to_idx}
        for code, idxs in code_to_idx.items():
            model.Add(sum(x[i] for i in idxs) == y[code])
            model.Add(sum(x[i] for i in idxs) <= 1)

        # Capstone variable (choose exactly one code).
        cap_vars = {code: model.NewBoolVar(f"cap_{code}") for code in capstone_codes}
        model.Add(sum(cap_vars.values()) == 1)

        # Semester assignment variables for non-capstone offerings:
        # indices: 0=3F, 1=3S, 2=4F, 3=4S
        slot_targets = {0: 5, 1: 5, 2: 4, 3: 4}
        z: dict[tuple[int, int], cp_model.IntVar] = {}
        for i, c in enumerate(noncap_offerings):
            compatible_terms = [0, 2] if c.term == "F" else [1, 3]
            z_vars = []
            for t in compatible_terms:
                zv = model.NewBoolVar(f"z_{i}_{t}")
                z[(i, t)] = zv
                z_vars.append(zv)
            model.Add(sum(z_vars) == x[i])
        for t, target in slot_targets.items():
            model.Add(sum(z[(i, t)] for i in range(len(noncap_offerings)) if (i, t) in z) == target)

        # Required non-capstone codes must be selected.
        required_noncap = self.pool.required_non_capstone_codes()
        for code in required_noncap:
            if code not in y:
                return None
            model.Add(y[code] == 1)

        # Build representative attributes by code.
        rep_by_code: dict[str, Course] = {}
        for c in noncap_offerings:
            rep_by_code.setdefault(c.course_code, c)

        # Breadth/depth constraints in areas 1..6.
        breadth_bools = []
        depth_bools = []
        for area in (1, 2, 3, 4, 5, 6):
            area_x = [x[i] for i, c in enumerate(noncap_offerings) if c.area == area]
            kernel_x = [x[i] for i, c in enumerate(noncap_offerings) if c.area == area and bool(getattr(c, "kernel_course", False))]
            if not area_x:
                continue
            b = model.NewBoolVar(f"breadth_{area}")
            d = model.NewBoolVar(f"depth_{area}")
            model.Add(sum(kernel_x) >= self.policy.min_kernel_per_breadth_area * b)
            model.Add(sum(kernel_x) >= self.policy.min_kernel_per_depth_area * d)
            model.Add(sum(area_x) >= self.policy.min_courses_per_depth_area * d)
            model.Add(d <= b)
            breadth_bools.append(b)
            depth_bools.append(d)
        if not breadth_bools or not depth_bools:
            return None
        model.Add(sum(breadth_bools) >= self.policy.min_breadth_areas)
        model.Add(sum(depth_bools) >= self.policy.min_depth_areas)

        # Math/sci area 7 minimum.
        area7_x = [x[i] for i, c in enumerate(noncap_offerings) if c.area == 7]
        if self.policy.min_math_sci_courses > 0:
            model.Add(sum(area7_x) >= self.policy.min_math_sci_courses)

        # Complementary + HSS minimum.
        comp_codes = [
            code
            for code in y.keys()
            if ("hss" in _code_nontech_types(code) or "cs" in _code_nontech_types(code))
            and not _code_any(code, lambda c: bool(getattr(c, "is_required", False)))
            and not _code_any(code, lambda c: bool(getattr(c, "is_year1_year2", False)))
        ]
        hss_codes = [code for code in comp_codes if "hss" in _code_nontech_types(code)]
        if self.policy.min_complementary_courses > 0:
            model.Add(sum(y[code] for code in comp_codes) >= self.policy.min_complementary_courses)
        if self.policy.min_hss_in_complementary > 0:
            model.Add(sum(y[code] for code in hss_codes) >= self.policy.min_hss_in_complementary)

        # Free elective minimum.
        free_codes = [
            code
            for code in y.keys()
            if _code_any(code, lambda c: bool(getattr(c, "free_elective", False)))
            and not _code_any(code, lambda c: bool(getattr(c, "is_required", False)))
            and not _code_any(code, lambda c: bool(getattr(c, "is_year1_year2", False)))
        ]
        if self.policy.min_free_elective_courses > 0:
            model.Add(sum(y[code] for code in free_codes) >= self.policy.min_free_elective_courses)

        # Technical elective interpretation:
        # technical electives are additional beyond breadth/depth/math-sci minimum cores.
        tech_codes = [
            code
            for code in y.keys()
            if _code_any(
                code,
                lambda c: bool(getattr(c, "technical_elective", False)) or c.course_type == "technical",
            )
            and not _code_any(code, lambda c: bool(getattr(c, "is_required", False)))
            and not _code_any(code, lambda c: bool(getattr(c, "is_year1_year2", False)))
        ]
        min_consumed = (
            self.policy.min_breadth_areas * self.policy.min_kernel_per_breadth_area
            + self.policy.min_depth_areas * (self.policy.min_courses_per_depth_area - 1)
            + self.policy.min_math_sci_courses
        )
        model.Add(sum(y[code] for code in tech_codes) >= min_consumed + self.policy.min_technical_elective_courses)

        # Year-3 technical rule:
        # technical_y3 >= 7 OR if ECE472 is in year3 then technical_y3 >= 6
        tech_y3 = sum(
            z[(i, t)]
            for i, c in enumerate(noncap_offerings)
            for t in (0, 1)
            if (i, t) in z and ((bool(getattr(c, "technical_elective", False)) or c.course_type == "technical"))
        )
        ece_idx = code_to_idx.get("ECE472H1", [])
        if ece_idx:
            ece_y3 = model.NewBoolVar("ece472_in_year3")
            model.Add(ece_y3 == sum(z[(i, t)] for i in ece_idx for t in (0, 1) if (i, t) in z))
            model.Add(tech_y3 >= 7 - ece_y3)
        else:
            model.Add(tech_y3 >= 7)

        # CSC3*/CSC4* max credits
        csc_codes = [code for code in rep_by_code if code.startswith("CSC3") or code.startswith("CSC4")]
        if csc_codes:
            # credits are half credits for H and full for Y (noncap here are F/S, so typically H)
            def _credit_of(code: str) -> float:
                return 1.0 if code[-2] == "Y" else 0.5

            scale = 10  # integer scaling
            model.Add(
                sum(int(_credit_of(code) * scale) * y[code] for code in csc_codes)
                <= int(self.policy.max_csc34_credits * scale)
            )

        # CEAB hard constraints (when enabled)
        if self.policy.ceab_attributes_required:
            # Keep two decimal places to minimize integer-scaling rounding error.
            ceab_scale = 100

            def ceab_coeff(course: Course, prop: str) -> int:
                raw = float(getattr(course.ceab, prop, 0.0) or 0.0)
                return int(round(raw * ceab_scale))

            cap_rep: dict[str, Course] = {}
            for c in self.courses:
                if self.pool.is_capstone(c):
                    cap_rep.setdefault(c.course_code, c)

            attr_defs = [
                ("total_AU", self.policy.ceab_net_total_au, self.policy.year12_baseline_total_au),
                ("mathematics", self.policy.ceab_net_math, self.policy.year12_baseline_math),
                ("natural_science", self.policy.ceab_net_ns, self.policy.year12_baseline_ns),
                ("math_and_science", self.policy.ceab_net_math_ns, self.policy.year12_baseline_math_ns),
                ("engineering_science", self.policy.ceab_net_es, self.policy.year12_baseline_es),
                ("engineering_design", self.policy.ceab_net_ed, self.policy.year12_baseline_ed),
                ("eng_sci_and_design", self.policy.ceab_net_es_ed, self.policy.year12_baseline_es_ed),
                ("complementary_studies", self.policy.ceab_net_cs, self.policy.year12_baseline_cs),
            ]

            for prop, net_target, baseline in attr_defs:
                rhs = int(round(max(0.0, float(net_target) - float(baseline)) * ceab_scale))
                lhs_noncap = sum(ceab_coeff(rep_by_code[code], prop) * y[code] for code in y.keys())
                lhs_cap = sum(
                    (ceab_coeff(cap_rep[code], prop) if code in cap_rep else 0) * cap_vars[code]
                    for code in cap_vars.keys()
                )
                model.Add(lhs_noncap + lhs_cap >= rhs)

        # Soft objective: maximize preferred picks.
        objective = []
        total_pref = len(preferred_list)
        for code in y.keys():
            if code in preferred_rank:
                objective.append((total_pref - preferred_rank[code]) * y[code])
        for code in cap_vars.keys():
            if code in preferred_rank:
                objective.append((total_pref - preferred_rank[code]) * cap_vars[code])
        if objective:
            model.Maximize(sum(objective))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 8.0
        solver.parameters.num_search_workers = 1
        if seed is not None:
            solver.parameters.random_seed = int(seed)
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None

        cap_code = next(code for code, v in cap_vars.items() if solver.Value(v) == 1)
        capstone = next((c for c in self.courses if c.course_code == cap_code and c.term == "Y"), None)
        if capstone is None:
            return None

        semester_plan: list[list[Course]] = [[], [], [], []]
        # Place capstone in 4F/4S
        semester_plan[2].append(capstone)
        semester_plan[3].append(capstone)
        for i, c in enumerate(noncap_offerings):
            if solver.Value(x[i]) != 1:
                continue
            for t in (0, 1, 2, 3):
                if (i, t) in z and solver.Value(z[(i, t)]) == 1:
                    semester_plan[t].append(c)
                    break

        if not (len(semester_plan[0]) == 5 and len(semester_plan[1]) == 5 and len(semester_plan[2]) == 5 and len(semester_plan[3]) == 5):
            return None

        unique = []
        seen_codes = set()
        for sem in semester_plan:
            for c in sem:
                if c.course_code in seen_codes:
                    continue
                seen_codes.add(c.course_code)
                unique.append(c)
        return ProfileSolveResult(semester_plan=semester_plan, selected_courses=unique)

