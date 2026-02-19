from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.data_bridge.adapters.sqlite_adapter import SQLiteCatalogAdapter
from backend.data_bridge.models import CourseOffering


def _term_normalize(raw: object) -> str:
    term = str(raw).strip().upper()
    if term not in {"F", "S", "Y"}:
        raise ValueError(f"Invalid term value: {raw}")
    return term


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    txt = str(value).strip()
    if txt == "" or txt.lower() == "nan":
        return None
    return txt


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    txt = str(value).strip()
    if txt == "" or txt.lower() == "nan":
        return None
    return float(txt)


def migrate_from_legacy(db_path: str | Path, data_dir: str | Path) -> None:
    base = Path(data_dir)
    adapter = SQLiteCatalogAdapter(db_path=db_path)

    ceab_df = pd.read_excel(base / "courses_ceab.ods", engine="odf")
    desc_df = pd.read_excel(base / "courses_description.ods", engine="odf")
    tech_df = pd.read_excel(base / "technical_courses.ods", engine="odf")
    excluded_df = pd.read_csv(base / "excluded_course_codes.csv")

    desc_index: dict[str, dict[str, str | None]] = {}
    for _, row in desc_df.iterrows():
        code = _clean_text(row.get("Course Code"))
        if not code:
            continue
        desc_index[code] = {
            "name": _clean_text(row.get("Course Name")),
            "description": _clean_text(row.get("Description")),
        }

    tech_index: dict[tuple[str, str], dict[str, object]] = {}
    for _, row in tech_df.iterrows():
        code = _clean_text(row.get("Course Code"))
        term_raw = row.get("Term")
        if not code or term_raw is None:
            continue
        term = _term_normalize(term_raw)
        area_raw = row.get("Area")
        area = int(area_raw) if str(area_raw).strip() not in {"", "nan", "None"} else -1
        kernel = bool(int(row.get("Kernel", 0)))
        tech_index[(code, term)] = {"area": area, "kernel_course": kernel}

    excluded_codes = {str(x).strip() for x in excluded_df["Course Code"].dropna().tolist()}

    seen: set[tuple[str, str]] = set()
    for _, row in ceab_df.iterrows():
        code = _clean_text(row.get("Course Code"))
        term_raw = row.get("Term")
        if not code or term_raw is None:
            continue
        term = _term_normalize(term_raw)
        key = (code, term)
        if key in seen:
            continue
        seen.add(key)

        ceab_name = _clean_text(row.get("Course Name"))
        desc = desc_index.get(code, {})
        name = desc.get("name") or ceab_name
        description = desc.get("description")

        tech_meta = tech_index.get(key)
        is_technical = tech_meta is not None
        area = int(tech_meta["area"]) if tech_meta else None
        kernel = bool(tech_meta["kernel_course"]) if tech_meta else False

        payload = CourseOffering(
            course_code=code,
            term=term,
            name=name,
            description=description,
            math=_to_float(row.get("Math")),
            ns=_to_float(row.get("NS")),
            cs=_to_float(row.get("CS")),
            es=_to_float(row.get("ES")),
            ed=_to_float(row.get("ED")),
            course_type="technical" if is_technical else "non_technical",
            non_technical_type=None,
            area=area,
            kernel_course=kernel,
            technical_elective=is_technical,
            free_elective=True,
            is_excluded=code in excluded_codes,
            active=True,
        )
        adapter.upsert_course_offering(payload)

    # Also include technical rows that may be absent in CEAB data.
    for (code, term), tech_meta in tech_index.items():
        if (code, term) in seen:
            continue
        desc = desc_index.get(code, {})
        payload = CourseOffering(
            course_code=code,
            term=term,
            name=desc.get("name"),
            description=desc.get("description"),
            math=0.0,
            ns=0.0,
            cs=0.0,
            es=0.0,
            ed=0.0,
            course_type="technical",
            area=int(tech_meta["area"]),
            kernel_course=bool(tech_meta["kernel_course"]),
            technical_elective=True,
            free_elective=True,
            is_excluded=code in excluded_codes,
            active=True,
        )
        adapter.upsert_course_offering(payload)

