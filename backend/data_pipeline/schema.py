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
    course_code TEXT NOT NULL,
    term TEXT NOT NULL,
    course_type TEXT NOT NULL CHECK (course_type IN ('technical', 'non_technical')),
    non_technical_type TEXT CHECK (non_technical_type IN ('hss', 'cs', 'other') OR non_technical_type IS NULL),
    area INTEGER,
    kernel_course INTEGER NOT NULL DEFAULT 0,
    technical_elective INTEGER NOT NULL DEFAULT 0,
    free_elective INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (course_code, term),
    FOREIGN KEY (course_code, term) REFERENCES course_offering(course_code, term) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS course_ceab (
    course_code TEXT NOT NULL,
    term TEXT NOT NULL,
    math REAL,
    ns REAL,
    cs REAL,
    es REAL,
    ed REAL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (course_code, term),
    FOREIGN KEY (course_code, term) REFERENCES course_offering(course_code, term) ON DELETE CASCADE
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
        conn.commit()
    finally:
        conn.close()

