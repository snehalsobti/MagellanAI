from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS course (
    course_code TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS course_offering (
    course_code TEXT NOT NULL,
    term TEXT NOT NULL CHECK (term IN ('F', 'S', 'Y')),
    is_excluded INTEGER NOT NULL DEFAULT 0,
    source_status TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    removal_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (course_code, term),
    FOREIGN KEY (course_code) REFERENCES course(course_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS course_classification (
    classification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL,
    term TEXT NOT NULL,
    course_type TEXT NOT NULL CHECK (course_type IN ('technical', 'non_technical')),
    non_technical_type TEXT CHECK (non_technical_type IN ('hss', 'cs', 'other') OR non_technical_type IS NULL),
    area INTEGER NOT NULL DEFAULT -1,
    kernel_course INTEGER NOT NULL DEFAULT 0,
    technical_elective INTEGER NOT NULL DEFAULT 0,
    free_elective INTEGER NOT NULL DEFAULT 0,
    is_year1_year2 INTEGER NOT NULL DEFAULT 0,
    is_required INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (course_code, term, area),
    FOREIGN KEY (course_code, term) REFERENCES course_offering(course_code, term) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS course_ceab (
    course_code TEXT NOT NULL,
    math REAL,
    ns REAL,
    cs REAL,
    es REAL,
    ed REAL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (course_code),
    FOREIGN KEY (course_code) REFERENCES course(course_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS course_source_snapshot (
    course_code TEXT NOT NULL,
    term TEXT NOT NULL,
    ceab_name TEXT,
    calendar_name TEXT,
    raw_description TEXT,
    source_notes TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (course_code, term),
    FOREIGN KEY (course_code, term) REFERENCES course_offering(course_code, term) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_course_name ON course(name);
CREATE INDEX IF NOT EXISTS idx_offering_excluded ON course_offering(is_excluded);
CREATE INDEX IF NOT EXISTS idx_classification_filters ON course_classification(course_type, area, kernel_course);
"""


def init_db(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA_SQL)
        # Lightweight migration: if an old term-keyed course_ceab exists, collapse to course-level.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(course_ceab)").fetchall()]
        if "term" in cols:
            conn.executescript(
                """
                PRAGMA foreign_keys = OFF;
                ALTER TABLE course_ceab RENAME TO course_ceab_old;
                CREATE TABLE course_ceab (
                    course_code TEXT NOT NULL PRIMARY KEY,
                    math REAL,
                    ns REAL,
                    cs REAL,
                    es REAL,
                    ed REAL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (course_code) REFERENCES course(course_code) ON DELETE CASCADE
                );
                INSERT INTO course_ceab(course_code, math, ns, cs, es, ed, updated_at)
                SELECT
                    course_code,
                    MAX(math) AS math,
                    MAX(ns) AS ns,
                    MAX(cs) AS cs,
                    MAX(es) AS es,
                    MAX(ed) AS ed,
                    MAX(updated_at) AS updated_at
                FROM course_ceab_old
                GROUP BY course_code;
                DROP TABLE course_ceab_old;
                PRAGMA foreign_keys = ON;
                """
            )

        cls_cols = {r[1] for r in conn.execute("PRAGMA table_info(course_classification)").fetchall()}
        # Migration: preserve multi-area rows in course_classification.
        if "classification_id" not in cls_cols:
            conn.executescript(
                """
                PRAGMA foreign_keys = OFF;
                ALTER TABLE course_classification RENAME TO course_classification_old;
                CREATE TABLE course_classification (
                    classification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_code TEXT NOT NULL,
                    term TEXT NOT NULL,
                    course_type TEXT NOT NULL CHECK (course_type IN ('technical', 'non_technical')),
                    non_technical_type TEXT CHECK (non_technical_type IN ('hss', 'cs', 'other') OR non_technical_type IS NULL),
                    area INTEGER NOT NULL DEFAULT -1,
                    kernel_course INTEGER NOT NULL DEFAULT 0,
                    technical_elective INTEGER NOT NULL DEFAULT 0,
                    free_elective INTEGER NOT NULL DEFAULT 0,
                    is_year1_year2 INTEGER NOT NULL DEFAULT 0,
                    is_required INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (course_code, term, area),
                    FOREIGN KEY (course_code, term) REFERENCES course_offering(course_code, term) ON DELETE CASCADE
                );
                INSERT OR IGNORE INTO course_classification(
                    course_code, term, course_type, non_technical_type, area,
                    kernel_course, technical_elective, free_elective, is_year1_year2, is_required, updated_at
                )
                SELECT
                    course_code,
                    term,
                    course_type,
                    non_technical_type,
                    COALESCE(area, -1) AS area,
                    kernel_course,
                    technical_elective,
                    free_elective,
                    COALESCE(is_year1_year2, 0),
                    COALESCE(is_required, 0),
                    updated_at
                FROM course_classification_old;
                DROP TABLE course_classification_old;
                PRAGMA foreign_keys = ON;
                """
            )
            cls_cols = {r[1] for r in conn.execute("PRAGMA table_info(course_classification)").fetchall()}
        if "is_year1_year2" not in cls_cols:
            conn.execute(
                "ALTER TABLE course_classification ADD COLUMN is_year1_year2 INTEGER NOT NULL DEFAULT 0"
            )
        if "is_required" not in cls_cols:
            conn.execute(
                "ALTER TABLE course_classification ADD COLUMN is_required INTEGER NOT NULL DEFAULT 0"
            )
        conn.commit()
    finally:
        conn.close()

