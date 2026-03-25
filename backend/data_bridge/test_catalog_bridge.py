import tempfile
import unittest

from backend.data_bridge.adapters.in_memory_adapter import InMemoryCatalogAdapter
from backend.data_bridge.adapters.sqlite_adapter import SQLiteCatalogAdapter
from backend.data_bridge.interfaces import CatalogBridge
from backend.data_bridge.models import CourseOffering
from backend.data_pipeline.schema import init_db


def _sample_offering() -> CourseOffering:
    return CourseOffering(
        course_code="ECE999H1",
        term="F",
        name="Special Topics",
        description="Special topics in ECE and systems.",
        math=0.0,
        ns=0.0,
        cs=0.0,
        es=24.0,
        ed=12.0,
        course_type="technical",
        area=3,
        kernel_course=True,
        technical_elective=True,
        free_elective=True,
    )


class BridgeContractMixin:
    def build_bridge(self) -> CatalogBridge:
        raise NotImplementedError

    def test_upsert_get_search_filter_remove(self):
        bridge = self.build_bridge()

        payload = _sample_offering()
        bridge.upsert_course_offering(payload)

        fetched = bridge.get_course_offering("ECE999H1", "F")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.course_code, "ECE999H1")
        self.assertEqual(fetched.term, "F")

        docs = bridge.get_rag_documents(active_only=True)
        self.assertTrue(any(d.course_code == "ECE999H1" for d in docs))

        search_rows = bridge.search_courses("special", limit=10)
        self.assertTrue(any(r.course_code == "ECE999H1" for r in search_rows))

        filter_rows = bridge.filter_courses(term="F", area=3, kernel_course=True, min_es=20.0, limit=10)
        self.assertTrue(any(r.course_code == "ECE999H1" for r in filter_rows))

        technical = bridge.get_technical_courses()
        self.assertTrue(any(r.course_code == "ECE999H1" for r in technical))

        bridge.soft_remove_course("ECE999H1", "F")
        filtered = bridge.filter_courses(term="F", limit=10)
        self.assertFalse(any(r.course_code == "ECE999H1" for r in filtered))
        filtered_incl = bridge.filter_courses(term="F", include_excluded=True, limit=10)
        self.assertTrue(any(r.course_code == "ECE999H1" for r in filtered_incl))

        bridge.hard_remove_course("ECE999H1", "F")
        self.assertIsNone(bridge.get_course_offering("ECE999H1", "F"))


class TestInMemoryBridgeContract(BridgeContractMixin, unittest.TestCase):
    def build_bridge(self) -> CatalogBridge:
        return InMemoryCatalogAdapter()


class TestSQLiteBridgeContract(BridgeContractMixin, unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = f"{self._tmpdir.name}/bridge_contract.db"
        init_db(self.db_path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def build_bridge(self) -> CatalogBridge:
        return SQLiteCatalogAdapter(self.db_path)


class TestSQLiteMultiAreaCourses(unittest.TestCase):
    """
    A single course offering (course_code + term) may belong to multiple
    technical areas.  The SQLite adapter must preserve all area variants so
    that filter_courses / get_technical_courses return one row per
    (course_code, term, area) — not one row with a single area collapsed.

    This mirrors real catalog data such as ECE302H1, which is simultaneously
    in areas 4, 5, and 7 for both F and S terms.
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = f"{self._tmpdir.name}/multiarea_test.db"
        init_db(self.db_path)
        self.bridge = SQLiteCatalogAdapter(self.db_path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _make_offering(self, area: int) -> CourseOffering:
        return CourseOffering(
            course_code="ECE900H1",
            term="F",
            name="Multi-Area Course",
            description="A course that belongs to several technical areas.",
            math=0.0,
            ns=0.0,
            cs=0.0,
            es=12.0,
            ed=12.0,
            course_type="technical",
            area=area,
            kernel_course=False,
            technical_elective=True,
            free_elective=False,
        )

    def test_multi_area_filter_courses_returns_one_row_per_area(self):
        """filter_courses must return a separate row for each area the course belongs to."""
        for area in (4, 5, 7):
            self.bridge.upsert_course_offering(self._make_offering(area))

        rows = self.bridge.filter_courses(limit=100)
        ece900_rows = [r for r in rows if r.course_code == "ECE900H1"]

        returned_areas = sorted(r.area for r in ece900_rows)
        self.assertEqual(returned_areas, [4, 5, 7],
                         "filter_courses must return one row per area for multi-area courses")

    def test_multi_area_filter_by_area_returns_correct_subset(self):
        """Filtering by a specific area should return only rows with that area."""
        for area in (4, 5, 7):
            self.bridge.upsert_course_offering(self._make_offering(area))

        rows_area5 = self.bridge.filter_courses(area=5, limit=100)
        ece900_in_area5 = [r for r in rows_area5 if r.course_code == "ECE900H1"]

        self.assertEqual(len(ece900_in_area5), 1)
        self.assertEqual(ece900_in_area5[0].area, 5)

    def test_multi_area_get_technical_courses_returns_one_entry_per_area(self):
        """get_technical_courses (used by the solver) must also surface all area variants."""
        for area in (4, 5, 7):
            self.bridge.upsert_course_offering(self._make_offering(area))

        technical = self.bridge.get_technical_courses()
        ece900_entries = [t for t in technical if t.course_code == "ECE900H1"]

        returned_areas = sorted(t.area for t in ece900_entries)
        self.assertEqual(returned_areas, [4, 5, 7],
                         "get_technical_courses must expose all area variants for the solver")

    def test_get_course_offering_returns_single_offering_record(self):
        """
        get_course_offering intentionally returns one record (LIMIT 1) and is
        only used for course-level data (name, description, CEAB).  It must not
        be used to determine the area for multi-area courses.
        """
        for area in (4, 5, 7):
            self.bridge.upsert_course_offering(self._make_offering(area))

        offering = self.bridge.get_course_offering("ECE900H1", "F")
        self.assertIsNotNone(offering)
        # The offering row's area is one of the valid areas; callers that need
        # all areas must use filter_courses / get_technical_courses instead.
        self.assertIn(offering.area, [4, 5, 7])


if __name__ == "__main__":
    unittest.main()

