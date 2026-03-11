from __future__ import annotations

from typing import Any


def _get(d: dict[str, Any], path: list[str], default: Any = None) -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def normalize_constraints(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize the structured constraints.json schema into the flat dict
    consumed by verifier and policy components.
    """
    if not isinstance(raw.get("hard_requirements"), dict):
        raise ValueError("Invalid constraints schema: missing 'hard_requirements' object")
    if not isinstance(raw.get("ceab_requirements"), dict):
        raise ValueError("Invalid constraints schema: missing 'ceab_requirements' object")
    if not isinstance(raw.get("profile_shape"), dict):
        raise ValueError("Invalid constraints schema: missing 'profile_shape' object")

    out: dict[str, Any] = {}
    out["total_num_credits"] = float(_get(raw, ["hard_requirements", "total_num_credits"], 10.0))
    out["ece472_required"] = bool(_get(raw, ["hard_requirements", "ece472_required"], True))
    out["capstone_required"] = bool(_get(raw, ["hard_requirements", "capstone_required"], True))
    out["min_required_non_capstone_courses"] = int(
        _get(raw, ["hard_requirements", "min_required_non_capstone_courses"], 1)
    )
    out["allow_non_capstone_y"] = bool(_get(raw, ["profile_shape", "allow_non_capstone_y"], False))

    out["min_breadth_areas"] = int(_get(raw, ["hard_requirements", "breadth", "min_breadth_areas"], 4))
    out["min_kernel_per_breadth_area"] = int(
        _get(raw, ["hard_requirements", "breadth", "min_kernel_per_breadth_area"], 1)
    )
    out["breadth_depth_area_domain"] = list(
        _get(raw, ["hard_requirements", "breadth", "breadth_depth_area_domain"], [1, 2, 3, 4, 5, 6])
    )

    out["min_depth_areas"] = int(_get(raw, ["hard_requirements", "depth", "min_depth_areas"], 2))
    out["min_kernel_per_depth_area"] = int(
        _get(raw, ["hard_requirements", "depth", "min_kernel_per_depth_area"], 1)
    )
    out["min_courses_per_depth_area"] = int(
        _get(raw, ["hard_requirements", "depth", "min_courses_per_depth_area"], 3)
    )

    out["min_math_sci_courses"] = int(_get(raw, ["hard_requirements", "math_sci", "min_math_sci_courses"], 1))
    out["exclude_h3_h5"] = bool(_get(raw, ["hard_requirements", "exclude_h3_h5"], True))
    out["max_csc34_credits"] = float(_get(raw, ["hard_requirements", "max_csc34_credits"], 1.5))

    out["min_complementary_courses"] = int(
        _get(raw, ["hard_requirements", "complementary", "min_complementary_courses"], 4)
    )
    out["min_hss_in_complementary"] = int(
        _get(raw, ["hard_requirements", "complementary", "min_hss_in_complementary"], 2)
    )
    out["min_free_elective_courses"] = int(
        _get(raw, ["hard_requirements", "free_elective", "min_free_elective_courses"], 1)
    )
    out["min_technical_elective_courses"] = int(
        _get(raw, ["hard_requirements", "technical_electives", "min_technical_elective_courses"], 3)
    )
    out["year3_min_technical_courses"] = int(
        _get(raw, ["hard_requirements", "year3_technical", "min_technical_courses"], 7)
    )
    out["year3_min_technical_courses_if_ece472"] = int(
        _get(raw, ["hard_requirements", "year3_technical", "min_technical_courses_if_ece472"], 6)
    )

    out["include_year12_ceab_baseline"] = bool(_get(raw, ["assumptions", "include_year12_ceab_baseline"], True))
    out["year12_default_choice"] = str(_get(raw, ["assumptions", "year12_default_choice"], "ECE297H1"))

    out["ceab_attributes_required"] = bool(_get(raw, ["ceab_requirements", "enabled"], True))

    targets = _get(raw, ["ceab_requirements", "targets"], {})
    pre = _get(raw, ["ceab_requirements", "preobtained"], {})
    out["ceab_total_au"] = float(targets.get("total_au", 1870.0))
    out["ceab_math"] = float(targets.get("math", 214.5))
    out["ceab_ns"] = float(targets.get("ns", 200.0))
    out["ceab_math_ns"] = float(targets.get("math_ns", 462.0))
    out["ceab_es"] = float(targets.get("es", 247.5))
    out["ceab_ed"] = float(targets.get("ed", 247.5))
    out["ceab_es_ed"] = float(targets.get("es_ed", 990.0))
    out["ceab_cs"] = float(targets.get("cs", 240.0))

    out["preobtained_total_au"] = float(pre.get("total_au", 0.0))
    out["preobtained_math"] = float(pre.get("math", 0.0))
    out["preobtained_ns"] = float(pre.get("ns", 0.0))
    out["preobtained_math_ns"] = float(pre.get("math_ns", 0.0))
    out["preobtained_es"] = float(pre.get("es", 0.0))
    out["preobtained_ed"] = float(pre.get("ed", 0.0))
    out["preobtained_es_ed"] = float(pre.get("es_ed", 0.0))
    out["preobtained_cs"] = float(pre.get("cs", 0.0))
    return out

