from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone

from backend.data_bridge.interfaces import CatalogBridge
from backend.data_bridge.models import CourseOffering, CourseSearchRow, RagDocument, TechnicalCourseInput


class InMemoryCatalogAdapter(CatalogBridge):
    def __init__(self) -> None:
        self._rows: "OrderedDict[tuple[str, str], CourseOffering]" = OrderedDict()
        self._touched_at = datetime.now(timezone.utc).isoformat()

    def _touch(self) -> None:
        self._touched_at = datetime.now(timezone.utc).isoformat()

    def get_technical_courses(self, include_excluded: bool = False) -> list[TechnicalCourseInput]:
        out: list[TechnicalCourseInput] = []
        for row in self._rows.values():
            if row.course_type != "technical" or not row.active:
                continue
            if row.is_excluded and not include_excluded:
                continue
            out.append(
                TechnicalCourseInput(
                    course_code=row.course_code,
                    term=row.term,
                    area=row.area if row.area is not None else -1,
                    kernel_course=row.kernel_course,
                    technical_elective=row.technical_elective,
                    free_elective=row.free_elective,
                    math=float(row.math or 0.0),
                    ns=float(row.ns or 0.0),
                    cs=float(row.cs or 0.0),
                    es=float(row.es or 0.0),
                    ed=float(row.ed or 0.0),
                )
            )
        return sorted(out, key=lambda x: (x.course_code, x.term))

    def get_course_name_index(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for row in self._rows.values():
            if row.active and row.name:
                out[row.course_code] = row.name
        return out

    def get_rag_documents(self, active_only: bool = True) -> list[RagDocument]:
        docs: dict[str, RagDocument] = {}
        for row in self._rows.values():
            if active_only and (not row.active or row.is_excluded):
                continue
            docs[row.course_code] = RagDocument(
                course_code=row.course_code,
                title=row.name or "",
                body_text=row.description or "",
                updated_at=self._touched_at,
            )
        return [docs[k] for k in sorted(docs)]

    def _to_search_row(self, row: CourseOffering) -> CourseSearchRow:
        return CourseSearchRow(
            course_code=row.course_code,
            term=row.term,
            name=row.name,
            description=row.description,
            course_type=row.course_type,
            non_technical_type=row.non_technical_type,
            area=row.area,
            kernel_course=row.kernel_course,
            technical_elective=row.technical_elective,
            free_elective=row.free_elective,
            is_excluded=row.is_excluded,
        )

    def search_courses(self, query: str, limit: int = 20) -> list[CourseSearchRow]:
        q = query.lower().strip()
        matches: list[CourseSearchRow] = []
        for row in self._rows.values():
            blob = " ".join([row.course_code, row.name or "", row.description or ""]).lower()
            if q in blob:
                matches.append(self._to_search_row(row))
        return matches[:limit]

    def filter_courses(
        self,
        *,
        term: str | None = None,
        area: int | None = None,
        kernel_course: bool | None = None,
        course_type: str | None = None,
        non_technical_type: str | None = None,
        min_math: float | None = None,
        min_ns: float | None = None,
        min_cs: float | None = None,
        min_es: float | None = None,
        min_ed: float | None = None,
        include_excluded: bool = False,
        limit: int = 200,
    ) -> list[CourseSearchRow]:
        out: list[CourseSearchRow] = []
        for row in self._rows.values():
            if not row.active:
                continue
            if row.is_excluded and not include_excluded:
                continue
            if term and row.term != term.upper():
                continue
            if area is not None and row.area != area:
                continue
            if kernel_course is not None and row.kernel_course != kernel_course:
                continue
            if course_type and row.course_type != course_type:
                continue
            if non_technical_type and row.non_technical_type != non_technical_type:
                continue
            if min_math is not None and (row.math or 0.0) < min_math:
                continue
            if min_ns is not None and (row.ns or 0.0) < min_ns:
                continue
            if min_cs is not None and (row.cs or 0.0) < min_cs:
                continue
            if min_es is not None and (row.es or 0.0) < min_es:
                continue
            if min_ed is not None and (row.ed or 0.0) < min_ed:
                continue
            out.append(self._to_search_row(row))
            if len(out) >= limit:
                break
        return out

    def get_course_offering(self, course_code: str, term: str) -> CourseOffering | None:
        return self._rows.get((course_code, term.upper()))

    def upsert_course_offering(self, payload: CourseOffering, scrape_if_missing: bool = False) -> None:
        del scrape_if_missing
        self._rows[(payload.course_code, payload.term.upper())] = payload
        self._touch()

    def soft_remove_course(self, course_code: str, term: str, reason: str | None = None) -> None:
        del reason
        key = (course_code, term.upper())
        if key in self._rows:
            row = self._rows[key]
            row.is_excluded = True
            self._rows[key] = row
            self._touch()

    def hard_remove_course(self, course_code: str, term: str) -> None:
        self._rows.pop((course_code, term.upper()), None)
        self._touch()

    def validate_catalog(self) -> list[str]:
        issues: list[str] = []
        for row in self._rows.values():
            if row.term not in ("F", "S", "Y"):
                issues.append(f"Invalid term for {row.course_code}: {row.term}")
        return issues

    def refresh_materialized_views_or_cache(self) -> None:
        return None

    def get_catalog_fingerprint(self) -> str:
        return f"{len(self._rows)}:{self._touched_at}"

