from __future__ import annotations

from abc import ABC, abstractmethod

from backend.data_bridge.models import CourseOffering, CourseSearchRow, RagDocument, TechnicalCourseInput


class CatalogBridge(ABC):
    @abstractmethod
    def get_technical_courses(self, include_excluded: bool = False) -> list[TechnicalCourseInput]:
        pass

    @abstractmethod
    def get_course_name_index(self) -> dict[str, str]:
        pass

    @abstractmethod
    def get_rag_documents(self, active_only: bool = True) -> list[RagDocument]:
        pass

    @abstractmethod
    def search_courses(self, query: str, limit: int = 20) -> list[CourseSearchRow]:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_course_offering(self, course_code: str, term: str) -> CourseOffering | None:
        pass

    @abstractmethod
    def upsert_course_offering(self, payload: CourseOffering, scrape_if_missing: bool = False) -> None:
        pass

    @abstractmethod
    def soft_remove_course(self, course_code: str, term: str, reason: str | None = None) -> None:
        pass

    @abstractmethod
    def hard_remove_course(self, course_code: str, term: str) -> None:
        pass

    @abstractmethod
    def validate_catalog(self) -> list[str]:
        pass

    @abstractmethod
    def refresh_materialized_views_or_cache(self) -> None:
        pass

    @abstractmethod
    def get_catalog_fingerprint(self) -> str:
        pass

    @abstractmethod
    def get_profile_candidate_courses(
        self,
        *,
        include_excluded: bool = False,
        include_year1_year2: bool = True,
        include_required: bool = True,
    ) -> list[CourseSearchRow]:
        pass

    @abstractmethod
    def get_courses_by_codes(
        self,
        course_codes: list[str],
        *,
        include_excluded: bool = False,
    ) -> list[CourseSearchRow]:
        pass

