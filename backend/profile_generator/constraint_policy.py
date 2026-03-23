from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from backend.constraint_verifier.constraint_schema import normalize_constraints
from backend.types.ceab_baseline import load_year12_ceab_baseline


@dataclass(frozen=True)
class ConstraintPolicy:
    """
    Immutable snapshot of all ECE program constraints used by the CP-SAT solver
    and profile generator.  Values are sourced exclusively from constraints.json
    (the SSOT) via :func:`load_default`.  Never construct this class with
    hard-coded literals; always go through :meth:`load_default`.
    """
    # ── Breadth / Depth ─────────────────────────────────────────────────────
    min_breadth_areas: int
    min_kernel_per_breadth_area: int
    min_depth_areas: int
    min_kernel_per_depth_area: int
    min_courses_per_depth_area: int

    # ── Course category minimums ────────────────────────────────────────────
    min_math_sci_courses: int
    min_complementary_courses: int
    min_hss_in_complementary: int
    min_free_elective_courses: int
    min_technical_elective_courses: int

    # ── Year 3 technical requirement ────────────────────────────────────────
    year3_min_technical_courses: int
    year3_min_technical_courses_if_ece472: int

    # ── Credit caps ─────────────────────────────────────────────────────────
    max_csc34_credits: float
    exclude_h3_h5: bool

    # ── Profile shape ────────────────────────────────────────────────────────
    slots_per_term: int
    capstone_semester_indices: list[int]

    # ── Capstone metadata ────────────────────────────────────────────────────
    capstone_codes: list[str]

    # ── CEAB ────────────────────────────────────────────────────────────────
    ceab_attributes_required: bool
    ceab_net_total_au: float
    ceab_net_math: float
    ceab_net_ns: float
    ceab_net_math_ns: float
    ceab_net_es: float
    ceab_net_ed: float
    ceab_net_es_ed: float
    ceab_net_cs: float

    # ── Year 1/2 CEAB baseline ──────────────────────────────────────────────
    include_year12_ceab_baseline: bool
    year12_default_choice: str
    year12_baseline_total_au: float
    year12_baseline_math: float
    year12_baseline_ns: float
    year12_baseline_math_ns: float
    year12_baseline_es: float
    year12_baseline_ed: float
    year12_baseline_es_ed: float
    year12_baseline_cs: float

    @staticmethod
    def load_default(year12_choice: str | None = None) -> "ConstraintPolicy":
        """Load all constraints from the SSOT (constraints.json)."""
        constraints_path = (
            Path(__file__).resolve().parents[1] / "constraint_verifier" / "constraints.json"
        )
        with open(constraints_path, "r", encoding="utf-8") as f:
            raw = normalize_constraints(json.load(f))

        default_choice = str(raw.get("year12_default_choice", "ECE297H1") or "ECE297H1").strip().upper()
        if year12_choice:
            default_choice = str(year12_choice).strip().upper()

        include_baseline = bool(raw.get("include_year12_ceab_baseline", True))
        baseline = (
            load_year12_ceab_baseline(year12_choice=default_choice)
            if include_baseline
            else {
                "total_AU": 0.0,
                "mathematics": 0.0,
                "natural_science": 0.0,
                "math_and_science": 0.0,
                "engineering_science": 0.0,
                "engineering_design": 0.0,
                "eng_sci_and_design": 0.0,
                "complementary_studies": 0.0,
            }
        )

        def net(req_key: str, pre_key: str) -> float:
            return max(0.0, float(raw.get(req_key, 0.0) or 0.0) - float(raw.get(pre_key, 0.0) or 0.0))

        return ConstraintPolicy(
            min_breadth_areas=int(raw.get("min_breadth_areas", 4) or 4),
            min_kernel_per_breadth_area=int(raw.get("min_kernel_per_breadth_area", 1) or 1),
            min_depth_areas=int(raw.get("min_depth_areas", 2) or 2),
            min_kernel_per_depth_area=int(raw.get("min_kernel_per_depth_area", 1) or 1),
            min_courses_per_depth_area=int(raw.get("min_courses_per_depth_area", 3) or 3),
            min_math_sci_courses=int(raw.get("min_math_sci_courses", 1) or 1),
            min_complementary_courses=int(raw.get("min_complementary_courses", 0) or 0),
            min_hss_in_complementary=int(raw.get("min_hss_in_complementary", 0) or 0),
            min_free_elective_courses=int(raw.get("min_free_elective_courses", 0) or 0),
            min_technical_elective_courses=int(raw.get("min_technical_elective_courses", 0) or 0),
            year3_min_technical_courses=int(raw.get("year3_min_technical_courses", 7) or 7),
            year3_min_technical_courses_if_ece472=int(
                raw.get("year3_min_technical_courses_if_ece472", 6) or 6
            ),
            max_csc34_credits=float(raw.get("max_csc34_credits", 1.5) or 1.5),
            exclude_h3_h5=bool(raw.get("exclude_h3_h5", True)),
            slots_per_term=int(raw.get("slots_per_term", 5) or 5),
            capstone_semester_indices=list(raw.get("capstone_semester_indices", [2, 3]) or [2, 3]),
            capstone_codes=list(
                raw.get("capstone_codes", ["ECE496Y1", "APS490Y1", "BME498Y1"])
                or ["ECE496Y1", "APS490Y1", "BME498Y1"]
            ),
            ceab_attributes_required=bool(raw.get("ceab_attributes_required", False)),
            ceab_net_total_au=net("ceab_total_au", "preobtained_total_au"),
            ceab_net_math=net("ceab_math", "preobtained_math"),
            ceab_net_ns=net("ceab_ns", "preobtained_ns"),
            ceab_net_math_ns=net("ceab_math_ns", "preobtained_math_ns"),
            ceab_net_es=net("ceab_es", "preobtained_es"),
            ceab_net_ed=net("ceab_ed", "preobtained_ed"),
            ceab_net_es_ed=net("ceab_es_ed", "preobtained_es_ed"),
            ceab_net_cs=net("ceab_cs", "preobtained_cs"),
            include_year12_ceab_baseline=include_baseline,
            year12_default_choice=default_choice,
            year12_baseline_total_au=float(baseline["total_AU"]),
            year12_baseline_math=float(baseline["mathematics"]),
            year12_baseline_ns=float(baseline["natural_science"]),
            year12_baseline_math_ns=float(baseline["math_and_science"]),
            year12_baseline_es=float(baseline["engineering_science"]),
            year12_baseline_ed=float(baseline["engineering_design"]),
            year12_baseline_es_ed=float(baseline["eng_sci_and_design"]),
            year12_baseline_cs=float(baseline["complementary_studies"]),
        )
