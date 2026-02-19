from __future__ import annotations

import os
from pathlib import Path

from backend.data_bridge.adapters.in_memory_adapter import InMemoryCatalogAdapter
from backend.data_bridge.adapters.sqlite_adapter import SQLiteCatalogAdapter
from backend.data_bridge.interfaces import CatalogBridge


def get_catalog_bridge() -> CatalogBridge:
    backend = os.getenv("DATA_BACKEND", "sqlite").strip().lower()
    if backend == "memory":
        return InMemoryCatalogAdapter()
    if backend == "sqlite":
        db_path = os.getenv("MAGELLAN_DB_PATH")
        if not db_path:
            db_path = str(Path(__file__).resolve().parents[2] / "data" / "magellan.db")
        return SQLiteCatalogAdapter(db_path=db_path)
    raise ValueError(f"Unsupported DATA_BACKEND: {backend}")

