from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from Code_brain import AdvancedCodeProjectBuilder
from Web_scanner_core import IndexedJsonlStore


class AdvancedCodeCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.builder = AdvancedCodeProjectBuilder()

    def test_simple_program_is_not_forced_into_large_architecture(self):
        capabilities = self.builder.detect_capabilities(
            "Build a small Python calculator.",
            {"request_contract": {"requirements": []}},
        )
        self.assertFalse(capabilities["advanced_project"])

    def test_cross_domain_professional_project_is_advanced(self):
        capabilities = self.builder.detect_capabilities(
            (
                "Build a professional multi-file asynchronous API with a database, "
                "authentication, encryption, concurrent workers, and tests."
            ),
            {"request_contract": {"requirements": []}},
        )
        for capability in (
            "multi_file", "api", "database", "authentication",
            "cryptography", "concurrency", "tests", "advanced_project",
        ):
            self.assertTrue(capabilities[capability], capability)

    def test_hardware_science_request_combines_capabilities(self):
        capabilities = self.builder.detect_capabilities(
            "Build professional hardware sensor software for a scientific experiment.",
            {"request_contract": {"requirements": []}},
        )
        self.assertTrue(capabilities["hardware_integration"])
        self.assertTrue(capabilities["scientific_computing"])
        self.assertTrue(capabilities["advanced_project"])


class ScannerStoreTests(unittest.TestCase):
    def test_indexed_store_upsert_search_and_count(self):
        root = PROJECT_ROOT / "Canri_Tests" / "runtime_fixtures"
        database_path = root / "scanner_unit_records.jsonl"
        index_path = root / "scanner_unit_index.sqlite3"
        for path in (database_path, index_path):
            path.unlink(missing_ok=True)
        try:
            store = IndexedJsonlStore(
                "test",
                database_path,
                index_path,
            )
            store.upsert({
                "record_id": "gravity_1",
                "title": "Orbital gravity",
                "summary": "Gravity determines orbital motion.",
                "text": "A satellite follows a curved path around Earth.",
                "source_id": "test_source",
                "trust_score": 90,
            })
            matches = store.search("satellite orbital gravity", limit=3)

            self.assertEqual(store.count(), 1)
            self.assertEqual(matches[0]["record_id"], "gravity_1")
            self.assertEqual(matches[0]["trust_score"], 90)
        finally:
            for path in (
                database_path,
                index_path,
                index_path.with_name(index_path.name + "-shm"),
                index_path.with_name(index_path.name + "-wal"),
            ):
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
