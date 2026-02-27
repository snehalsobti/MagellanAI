from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from backend.data_pipeline.calendar_scraper import scrape_course_name_and_description


def scrape_missing_descriptions(
    *,
    db_path: str | Path,
    limit: int | None = None,
    include_excluded: bool = False,
    delay_s: float = 0.25,
    only_codes: set[str] | None = None,
) -> tuple[int, int, list[str]]:
    """
    Fill missing course.name/description in the DB by scraping UofT calendars.

    Returns (filled_count, failed_count, failed_codes).
    """
    path = Path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        where = """
            (c.name IS NULL OR TRIM(c.name) = '' OR c.description IS NULL OR TRIM(c.description) = '')
            AND EXISTS (SELECT 1 FROM course_offering o WHERE o.course_code = c.course_code AND o.active = 1)
        """
        if not include_excluded:
            where += """
            AND EXISTS (
                SELECT 1 FROM course_offering o2
                WHERE o2.course_code = c.course_code
                  AND o2.active = 1
                  AND o2.is_excluded = 0
            )
            """

        params: list[object] = []
        if only_codes:
            placeholders = ",".join(["?"] * len(only_codes))
            where += f" AND c.course_code IN ({placeholders})"
            params.extend(sorted(only_codes))

        q = f"""
            SELECT c.course_code
            FROM course c
            WHERE {where}
            ORDER BY c.course_code
        """
        rows = conn.execute(q, params).fetchall()
        codes = [r["course_code"] for r in rows]
        if limit is not None:
            codes = codes[: int(limit)]

        filled = 0
        failed = 0
        failed_codes: list[str] = []

        for code in codes:
            name, desc = scrape_course_name_and_description(code)
            if not desc:
                failed += 1
                failed_codes.append(code)
                continue

            conn.execute(
                """
                UPDATE course
                SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE course_code = ?
                """,
                (name or "", desc, code),
            )
            conn.commit()
            filled += 1
            if delay_s > 0:
                time.sleep(delay_s)

        return filled, failed, failed_codes
    finally:
        conn.close()

