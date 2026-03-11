from __future__ import annotations

from backend.data_bridge.factory import get_catalog_bridge
from backend.data_bridge.interfaces import CatalogBridge


def _empty_baseline() -> dict[str, float]:
    return {
        "total_AU": 0.0,
        "mathematics": 0.0,
        "natural_science": 0.0,
        "math_and_science": 0.0,
        "engineering_science": 0.0,
        "engineering_design": 0.0,
        "eng_sci_and_design": 0.0,
        "complementary_studies": 0.0,
    }


def load_year12_ceab_baseline(
    *,
    year12_choice: str = "ECE297H1",
    bridge: CatalogBridge | None = None,
) -> dict[str, float]:
    """
    Compute Year 1/2 CEAB baseline through the CatalogBridge (DB-backed by default).

    Notes:
      - Exactly one of ECE295H1 / ECE297H1 is counted.
      - Baseline is deduped by course_code.
    """

    catalog = bridge or get_catalog_bridge()
    rows = catalog.get_profile_candidate_courses(
        include_excluded=True,
        include_year1_year2=True,
        include_required=True,
    )
    year12_rows = [r for r in rows if bool(getattr(r, "is_year1_year2", False))]
    if not year12_rows:
        return _empty_baseline()

    chosen = year12_choice.strip().upper() if year12_choice else "ECE297H1"
    choice_codes = {"ECE295H1", "ECE297H1"}
    if chosen not in choice_codes:
        chosen = "ECE297H1"

    accum = _empty_baseline()
    seen_codes: set[str] = set()
    for row in sorted(year12_rows, key=lambda r: (r.course_code, r.term)):
        code = row.course_code.strip().upper()
        if not code or code in seen_codes:
            continue
        if code in choice_codes and code != chosen:
            continue

        offering = catalog.get_course_offering(code, row.term)
        if offering is None:
            continue
        math = float(offering.math or 0.0)
        ns = float(offering.ns or 0.0)
        cs = float(offering.cs or 0.0)
        es = float(offering.es or 0.0)
        ed = float(offering.ed or 0.0)

        accum["mathematics"] += math
        accum["natural_science"] += ns
        accum["math_and_science"] += math + ns
        accum["engineering_science"] += es
        accum["engineering_design"] += ed
        accum["eng_sci_and_design"] += es + ed
        accum["complementary_studies"] += cs
        accum["total_AU"] += math + ns + cs + es + ed
        seen_codes.add(code)

    return accum

