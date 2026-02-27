from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.data_bridge.interfaces import CatalogBridge
from backend.data_bridge.models import CourseOffering, CourseSearchRow, RagDocument, TechnicalCourseInput
from backend.data_pipeline.calendar_scraper import scrape_course_name_and_description
from backend.data_pipeline.schema import init_db


class SQLiteCatalogAdapter(CatalogBridge):
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @staticmethod
    def _search_row_from_record(row: sqlite3.Row) -> CourseSearchRow:
        return CourseSearchRow(
            course_code=row["course_code"],
            term=row["term"],
            name=row["name"],
            description=row["description"],
            course_type=row["course_type"],
            non_technical_type=row["non_technical_type"],
            area=row["area"],
            kernel_course=bool(row["kernel_course"]),
            technical_elective=bool(row["technical_elective"]),
            free_elective=bool(row["free_elective"]),
            is_excluded=bool(row["is_excluded"]),
        )

    def get_technical_courses(self, include_excluded: bool = False) -> list[TechnicalCourseInput]:
        rows: list[sqlite3.Row]
        with self._conn() as conn:
            query = """
                SELECT
                    o.course_code, o.term, cls.area,
                    cls.kernel_course, cls.technical_elective, cls.free_elective,
                    COALESCE(ceab.math, 0.0) AS math,
                    COALESCE(ceab.ns, 0.0) AS ns,
                    COALESCE(ceab.cs, 0.0) AS cs,
                    COALESCE(ceab.es, 0.0) AS es,
                    COALESCE(ceab.ed, 0.0) AS ed,
                    o.is_excluded, o.active
                FROM course_offering o
                JOIN course_classification cls
                  ON cls.course_code = o.course_code AND cls.term = o.term
                LEFT JOIN course_ceab ceab
                  ON ceab.course_code = o.course_code
                WHERE cls.course_type = 'technical'
                  AND o.active = 1
            """
            params: list[object] = []
            if not include_excluded:
                query += " AND o.is_excluded = 0"
            query += " ORDER BY o.course_code, o.term"
            rows = list(conn.execute(query, params))

        return [
            TechnicalCourseInput(
                course_code=row["course_code"],
                term=row["term"],
                area=int(row["area"]) if row["area"] is not None else -1,
                kernel_course=bool(row["kernel_course"]),
                technical_elective=bool(row["technical_elective"]),
                free_elective=bool(row["free_elective"]),
                math=float(row["math"] or 0.0),
                ns=float(row["ns"] or 0.0),
                cs=float(row["cs"] or 0.0),
                es=float(row["es"] or 0.0),
                ed=float(row["ed"] or 0.0),
            )
            for row in rows
        ]

    def get_course_name_index(self) -> dict[str, str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT course_code, name FROM course WHERE active = 1 ORDER BY course_code"
            ).fetchall()
        return {r["course_code"]: (r["name"] or "") for r in rows}

    def get_rag_documents(self, active_only: bool = True) -> list[RagDocument]:
        query = """
            SELECT
                c.course_code,
                COALESCE(c.name, '') AS title,
                COALESCE(c.description, '') AS body_text,
                COALESCE(
                    (
                        SELECT MAX(o2.updated_at)
                        FROM course_offering o2
                        WHERE o2.course_code = c.course_code
                    ),
                    c.updated_at
                ) AS updated_at
            FROM course c
            WHERE EXISTS (
                SELECT 1 FROM course_offering o
                WHERE o.course_code = c.course_code
            )
        """
        if active_only:
            query += """
                AND c.active = 1
                AND EXISTS (
                    SELECT 1 FROM course_offering o
                    WHERE o.course_code = c.course_code
                      AND o.active = 1
                      AND o.is_excluded = 0
                )
            """
        query += " ORDER BY c.course_code"

        with self._conn() as conn:
            rows = conn.execute(query).fetchall()
        return [
            RagDocument(
                course_code=r["course_code"],
                title=r["title"],
                body_text=r["body_text"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def search_courses(self, query: str, limit: int = 20) -> list[CourseSearchRow]:
        needle = f"%{query.strip().lower()}%"
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    o.course_code, o.term, c.name, c.description,
                    cls.course_type, cls.non_technical_type, cls.area,
                    cls.kernel_course, cls.technical_elective, cls.free_elective,
                    o.is_excluded
                FROM course_offering o
                JOIN course c ON c.course_code = o.course_code
                JOIN course_classification cls
                  ON cls.course_code = o.course_code AND cls.term = o.term
                WHERE LOWER(o.course_code) LIKE ?
                   OR LOWER(COALESCE(c.name, '')) LIKE ?
                   OR LOWER(COALESCE(c.description, '')) LIKE ?
                ORDER BY o.is_excluded ASC, o.course_code ASC
                LIMIT ?
                """,
                (needle, needle, needle, limit),
            ).fetchall()
        return [self._search_row_from_record(r) for r in rows]

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
        query = """
            SELECT
                o.course_code, o.term, c.name, c.description,
                cls.course_type, cls.non_technical_type, cls.area,
                cls.kernel_course, cls.technical_elective, cls.free_elective,
                o.is_excluded,
                COALESCE(ceab.math, 0.0) AS math,
                COALESCE(ceab.ns, 0.0) AS ns,
                COALESCE(ceab.cs, 0.0) AS cs,
                COALESCE(ceab.es, 0.0) AS es,
                COALESCE(ceab.ed, 0.0) AS ed
            FROM course_offering o
            JOIN course c ON c.course_code = o.course_code
            JOIN course_classification cls
              ON cls.course_code = o.course_code AND cls.term = o.term
            LEFT JOIN course_ceab ceab
              ON ceab.course_code = o.course_code
            WHERE o.active = 1
        """
        params: list[object] = []

        if not include_excluded:
            query += " AND o.is_excluded = 0"
        if term:
            query += " AND o.term = ?"
            params.append(term.upper())
        if area is not None:
            query += " AND cls.area = ?"
            params.append(area)
        if kernel_course is not None:
            query += " AND cls.kernel_course = ?"
            params.append(int(kernel_course))
        if course_type:
            query += " AND cls.course_type = ?"
            params.append(course_type)
        if non_technical_type:
            query += " AND cls.non_technical_type = ?"
            params.append(non_technical_type)
        if min_math is not None:
            query += " AND COALESCE(ceab.math, 0.0) >= ?"
            params.append(min_math)
        if min_ns is not None:
            query += " AND COALESCE(ceab.ns, 0.0) >= ?"
            params.append(min_ns)
        if min_cs is not None:
            query += " AND COALESCE(ceab.cs, 0.0) >= ?"
            params.append(min_cs)
        if min_es is not None:
            query += " AND COALESCE(ceab.es, 0.0) >= ?"
            params.append(min_es)
        if min_ed is not None:
            query += " AND COALESCE(ceab.ed, 0.0) >= ?"
            params.append(min_ed)

        query += " ORDER BY o.course_code, o.term LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._search_row_from_record(r) for r in rows]

    def get_course_offering(self, course_code: str, term: str) -> CourseOffering | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    o.course_code, o.term, o.is_excluded, o.active,
                    c.name, c.description,
                    cls.course_type, cls.non_technical_type, cls.area,
                    cls.kernel_course, cls.technical_elective, cls.free_elective,
                    ceab.math, ceab.ns, ceab.cs, ceab.es, ceab.ed
                FROM course_offering o
                JOIN course c ON c.course_code = o.course_code
                JOIN course_classification cls
                  ON cls.course_code = o.course_code AND cls.term = o.term
                LEFT JOIN course_ceab ceab
                  ON ceab.course_code = o.course_code
                WHERE o.course_code = ? AND o.term = ?
                """,
                (course_code, term.upper()),
            ).fetchone()
        if row is None:
            return None
        return CourseOffering(
            course_code=row["course_code"],
            term=row["term"],
            name=row["name"],
            description=row["description"],
            math=row["math"],
            ns=row["ns"],
            cs=row["cs"],
            es=row["es"],
            ed=row["ed"],
            course_type=row["course_type"],
            non_technical_type=row["non_technical_type"],
            area=row["area"],
            kernel_course=bool(row["kernel_course"]),
            technical_elective=bool(row["technical_elective"]),
            free_elective=bool(row["free_elective"]),
            is_excluded=bool(row["is_excluded"]),
            active=bool(row["active"]),
        )

    def upsert_course_offering(self, payload: CourseOffering, scrape_if_missing: bool = False) -> None:
        name = payload.name
        description = payload.description
        if scrape_if_missing and (not name or not description):
            scraped_name, scraped_description = scrape_course_name_and_description(payload.course_code)
            if not name and scraped_name:
                name = scraped_name
            if not description and scraped_description:
                description = scraped_description

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO course (course_code, name, description, active, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(course_code) DO UPDATE SET
                    name = COALESCE(NULLIF(excluded.name, ''), name),
                    description = COALESCE(NULLIF(excluded.description, ''), description),
                    active = excluded.active,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    payload.course_code,
                    name,
                    description,
                    int(payload.active),
                ),
            )
            conn.execute(
                """
                INSERT INTO course_offering
                    (course_code, term, is_excluded, active, updated_at, removal_reason)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, NULL)
                ON CONFLICT(course_code, term) DO UPDATE SET
                    is_excluded = excluded.is_excluded,
                    active = excluded.active,
                    removal_reason = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    payload.course_code,
                    payload.term.upper(),
                    int(payload.is_excluded),
                    int(payload.active),
                ),
            )
            conn.execute(
                """
                INSERT INTO course_classification
                    (course_code, term, course_type, non_technical_type, area, kernel_course,
                     technical_elective, free_elective, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(course_code, term) DO UPDATE SET
                    course_type = excluded.course_type,
                    non_technical_type = excluded.non_technical_type,
                    area = excluded.area,
                    kernel_course = excluded.kernel_course,
                    technical_elective = excluded.technical_elective,
                    free_elective = excluded.free_elective,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    payload.course_code,
                    payload.term.upper(),
                    payload.course_type,
                    payload.non_technical_type,
                    payload.area,
                    int(payload.kernel_course),
                    int(payload.technical_elective),
                    int(payload.free_elective),
                ),
            )
            conn.execute(
                """
                INSERT INTO course_ceab
                    (course_code, math, ns, cs, es, ed, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(course_code) DO UPDATE SET
                    math = excluded.math,
                    ns = excluded.ns,
                    cs = excluded.cs,
                    es = excluded.es,
                    ed = excluded.ed,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    payload.course_code,
                    payload.math,
                    payload.ns,
                    payload.cs,
                    payload.es,
                    payload.ed,
                ),
            )
            conn.commit()

    def soft_remove_course(self, course_code: str, term: str, reason: str | None = None) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE course_offering
                SET is_excluded = 1, removal_reason = ?, updated_at = CURRENT_TIMESTAMP
                WHERE course_code = ? AND term = ?
                """,
                (reason, course_code, term.upper()),
            )
            conn.commit()

    def hard_remove_course(self, course_code: str, term: str) -> None:
        up_term = term.upper()
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM course_classification WHERE course_code = ? AND term = ?",
                (course_code, up_term),
            )
            conn.execute("DELETE FROM course_offering WHERE course_code = ? AND term = ?", (course_code, up_term))
            leftover = conn.execute(
                "SELECT 1 FROM course_offering WHERE course_code = ? LIMIT 1", (course_code,)
            ).fetchone()
            if leftover is None:
                conn.execute("DELETE FROM course WHERE course_code = ?", (course_code,))
            conn.commit()

    def validate_catalog(self) -> list[str]:
        issues: list[str] = []
        with self._conn() as conn:
            bad_terms = conn.execute(
                "SELECT course_code, term FROM course_offering WHERE term NOT IN ('F', 'S', 'Y')"
            ).fetchall()
            for row in bad_terms:
                issues.append(f"Invalid term for {row['course_code']}: {row['term']}")

            missing_classification = conn.execute(
                """
                SELECT o.course_code, o.term
                FROM course_offering o
                LEFT JOIN course_classification c
                  ON c.course_code = o.course_code AND c.term = o.term
                WHERE c.course_code IS NULL
                """
            ).fetchall()
            for row in missing_classification:
                issues.append(f"Missing classification for {row['course_code']} {row['term']}")

        return issues

    def refresh_materialized_views_or_cache(self) -> None:
        return None

    def get_catalog_fingerprint(self) -> str:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM course_offering) AS n_offerings,
                    (SELECT COUNT(*) FROM course WHERE active = 1) AS n_courses,
                    (
                      SELECT MAX(ts) FROM (
                        SELECT MAX(updated_at) AS ts FROM course
                        UNION ALL SELECT MAX(updated_at) AS ts FROM course_offering
                        UNION ALL SELECT MAX(updated_at) AS ts FROM course_classification
                        UNION ALL SELECT MAX(updated_at) AS ts FROM course_ceab
                      )
                    ) AS last_updated
                """
            ).fetchone()
        return f"{row['n_courses']}:{row['n_offerings']}:{row['last_updated'] or 'none'}"

