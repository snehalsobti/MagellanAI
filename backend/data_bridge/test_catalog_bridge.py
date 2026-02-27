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


if __name__ == "__main__":
    unittest.main()

