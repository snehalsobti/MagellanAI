import unittest
from pathlib import Path


class TestDataAccessGuardrails(unittest.TestCase):
    def test_sqlite_import_limited_to_allowed_packages(self):
        root = Path(__file__).resolve().parent
        allowed = {
            root / "data_bridge" / "adapters",
            root / "data_pipeline",
        }

        violations: list[str] = []
        for py_file in root.rglob("*.py"):
            if "test_data_access_guardrails.py" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8")
            if "import sqlite3" not in content:
                continue
            if not any(str(py_file).startswith(str(path)) for path in allowed):
                violations.append(str(py_file))

        self.assertEqual(
            violations,
            [],
            msg="sqlite3 import must stay in data adapters/pipeline only",
        )


if __name__ == "__main__":
    unittest.main()

