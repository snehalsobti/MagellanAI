from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from backend.data_bridge.adapters.sqlite_adapter import SQLiteCatalogAdapter
from backend.data_bridge.models import CourseOffering


@dataclass(frozen=True)
class CodeTags:
    is_technical: bool
    non_technical_type: str | None  # 'hss' | 'cs' | 'other' | None
    is_other_bucket: bool


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _clean_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip()


def _load_course_codes(course_codes_dir: Path) -> tuple[set[str], dict[str, set[str]]]:
    all_codes: set[str] = set()
    by_file: dict[str, set[str]] = {}
    for p in sorted(course_codes_dir.glob("*.csv")):
        df = _read_csv(p)
        if "acad_act_cd" not in df.columns:
            raise ValueError(f"Expected 'acad_act_cd' in {p}, got {list(df.columns)}")
        codes = set(_clean_series(df["acad_act_cd"]).tolist())
        codes = {c for c in codes if c and c.lower() != "nan"}
        by_file[p.stem] = codes
        all_codes |= codes
    return all_codes, by_file


def _load_offerings(term_dir: Path) -> set[tuple[str, str]]:
    offerings: set[tuple[str, str]] = set()
    for p in sorted(term_dir.glob("*.csv")):
        df = _read_csv(p)
        if not {"acad_act_cd", "section"} <= set(df.columns):
            raise ValueError(f"Expected acad_act_cd,section in {p}, got {list(df.columns)}")
        codes = _clean_series(df["acad_act_cd"])
        terms = _clean_series(df["section"]).str.upper()
        for code, term in zip(codes.tolist(), terms.tolist()):
            if not code or code.lower() == "nan":
                continue
            if term not in {"F", "S", "Y"}:
                raise ValueError(f"Invalid term {term} for {code} in {p}")
            offerings.add((code, term))
    return offerings


def _load_ceab(ceab_dir: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for p in sorted(ceab_dir.glob("*.csv")):
        df = _read_csv(p)
        if not {"Course Code", "Math", "NS", "CS", "ES", "ED"} <= set(df.columns):
            raise ValueError(f"Expected CEAB columns in {p}, got {list(df.columns)}")
        for _, r in df.iterrows():
            code = str(r["Course Code"]).strip()
            if not code or code.lower() == "nan":
                continue
            vals = {
                "math": float(r["Math"]),
                "ns": float(r["NS"]),
                "cs": float(r["CS"]),
                "es": float(r["ES"]),
                "ed": float(r["ED"]),
            }
            if code in out and out[code] != vals:
                raise ValueError(f"Conflicting CEAB values for {code} between files (including {p})")
            out[code] = vals
    return out


def _load_technical_classification(path: Path) -> dict[str, dict[str, object]]:
    df = _read_csv(path)
    if not {"Course Code", "Area", "Kernel"} <= set(df.columns):
        raise ValueError(f"Expected Course Code,Area,Kernel in {path}, got {list(df.columns)}")
    out: dict[str, dict[str, object]] = {}
    for _, r in df.iterrows():
        code = str(r["Course Code"]).strip()
        if not code or code.lower() == "nan":
            continue
        out[code] = {"area": int(r["Area"]), "kernel": bool(int(r["Kernel"]))}
    return out


def _load_excluded(path: Path) -> set[str]:
    if not path.exists():
        return set()
    df = _read_csv(path)
    col = "Course Code" if "Course Code" in df.columns else df.columns[0]
    codes = set(_clean_series(df[col]).tolist())
    return {c for c in codes if c and c.lower() != "nan"}


def _tags_for_code(code: str, by_file: dict[str, set[str]], technical_classification: dict[str, dict[str, object]]) -> CodeTags:
    is_technical = code in technical_classification or any(code in by_file.get("technical", set()) for _ in [0])
    is_other_bucket = code in by_file.get("others", set())

    if is_technical:
        return CodeTags(is_technical=True, non_technical_type=None, is_other_bucket=is_other_bucket)

    # non-technical typing: use membership in course_codes buckets (filename-based)
    if any(code in by_file.get(stem, set()) for stem in by_file if "hss" in stem):
        nt = "hss"
    elif any(code in by_file.get(stem, set()) for stem in by_file if "cs" in stem):
        nt = "cs"
    elif is_other_bucket:
        nt = "other"
    else:
        nt = "other"

    return CodeTags(is_technical=False, non_technical_type=nt, is_other_bucket=is_other_bucket)


def migrate_from_folders(db_path: str | Path, data_dir: str | Path) -> None:
    base = Path(data_dir)
    adapter = SQLiteCatalogAdapter(db_path=db_path)

    course_codes_dir = base / "course_codes"
    term_dir = base / "term"
    ceab_dir = base / "ceab"
    tech_class_path = base / "technical_classification" / "technical.csv"
    excluded_path = base / "excluded_course_codes.csv"

    all_codes, by_file = _load_course_codes(course_codes_dir)
    offerings = _load_offerings(term_dir)
    ceab = _load_ceab(ceab_dir)
    tech_class = _load_technical_classification(tech_class_path) if tech_class_path.exists() else {}
    excluded = _load_excluded(excluded_path)

    # Ensure term offerings codes exist in course_codes
    missing_codes = sorted({code for (code, _) in offerings} - all_codes)
    if missing_codes:
        raise ValueError(f"Term offerings contain codes not in course_codes: {missing_codes[:10]}")

    for code, term in sorted(offerings):
        tags = _tags_for_code(code, by_file, tech_class)
        tmeta = tech_class.get(code)
        ceab_vals = ceab.get(code, {"math": 0.0, "ns": 0.0, "cs": 0.0, "es": 0.0, "ed": 0.0})

        payload = CourseOffering(
            course_code=code,
            term=term,
            name=None,
            description=None,
            math=ceab_vals["math"],
            ns=ceab_vals["ns"],
            cs=ceab_vals["cs"],
            es=ceab_vals["es"],
            ed=ceab_vals["ed"],
            course_type="technical" if tags.is_technical else "non_technical",
            non_technical_type=None if tags.is_technical else tags.non_technical_type,
            area=int(tmeta["area"]) if tmeta else None,
            kernel_course=bool(tmeta["kernel"]) if tmeta else False,
            technical_elective=tags.is_technical,
            free_elective=True,  # any course may be used as free elective by constraints later
            is_excluded=code in excluded,
            active=True,
        )
        adapter.upsert_course_offering(payload, scrape_if_missing=False)

