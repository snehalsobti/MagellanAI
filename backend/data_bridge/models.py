from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Term = Literal["F", "S", "Y"]
CourseType = Literal["technical", "non_technical"]
NonTechnicalType = Literal["hss", "cs", "other"]


@dataclass
class CourseOffering:
    course_code: str
    term: Term
    name: str | None = None
    description: str | None = None
    math: float | None = None
    ns: float | None = None
    cs: float | None = None
    es: float | None = None
    ed: float | None = None
    course_type: CourseType = "technical"
    non_technical_type: NonTechnicalType | None = None
    area: int | None = None
    kernel_course: bool = False
    technical_elective: bool = False
    free_elective: bool = False
    is_excluded: bool = False
    active: bool = True


@dataclass
class TechnicalCourseInput:
    course_code: str
    term: Term
    area: int
    kernel_course: bool
    technical_elective: bool
    free_elective: bool
    math: float = 0.0
    ns: float = 0.0
    cs: float = 0.0
    es: float = 0.0
    ed: float = 0.0


@dataclass
class CourseSearchRow:
    course_code: str
    term: Term
    name: str | None
    description: str | None
    course_type: CourseType
    non_technical_type: NonTechnicalType | None
    area: int | None
    kernel_course: bool
    technical_elective: bool
    free_elective: bool
    is_excluded: bool


@dataclass
class RagDocument:
    course_code: str
    title: str
    body_text: str
    updated_at: str

