import unittest

from vayoloop_db import (
    DEMO_WORKSPACE_ID,
    detect_prescription_mime,
    map_health_record,
    map_prescription_record,
    sanitise_filename,
)


class VayoLoopDatabaseMappingTests(unittest.TestCase):
    def test_demo_workspace_is_a_fixed_synthetic_workspace(self):
        self.assertEqual(DEMO_WORKSPACE_ID, "00000000-0000-4000-8000-000000000001")

    def test_health_row_is_mapped_for_journal(self):
        mapped = map_health_record({
            "id": "health-1",
            "metric": "Blood pressure — systolic",
            "value": "122.5",
            "unit": "mmHg",
            "observed_at": "2026-11-15T08:30:00+05:30",
            "source": "Entered by family",
            "context": {},
        })
        self.assertEqual(mapped["id"], "health-1")
        self.assertEqual(mapped["value"], 122.5)
        self.assertEqual(mapped["unit"], "mmHg")

    def test_prescription_row_is_shared_demo_record(self):
        mapped = map_prescription_record({
            "id": "rx-1",
            "title": "Clinic visit",
            "original_file_name": "visit.pdf",
            "document_path": f"{DEMO_WORKSPACE_ID}/file.pdf",
            "file_size_bytes": 1200,
            "file_content_type": "application/pdf",
            "created_at": "2026-11-15T08:30:00+05:30",
        })
        self.assertTrue(mapped["is_cloud"])
        self.assertEqual(mapped["file_name"], "visit.pdf")
        self.assertIn("shared demo", mapped["storage_note"])

    def test_filename_is_sanitised(self):
        self.assertEqual(sanitise_filename("../../my rx.pdf"), "my_rx.pdf")

    def test_pdf_signature_is_checked(self):
        self.assertEqual(
            detect_prescription_mime("sample.pdf", "application/pdf", b"%PDF-1.7 sample"),
            "application/pdf",
        )

    def test_extension_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            detect_prescription_mime("sample.png", "image/png", b"%PDF-1.7 sample")

    def test_invalid_file_signature_is_rejected(self):
        with self.assertRaises(ValueError):
            detect_prescription_mime("sample.pdf", "application/pdf", b"not a pdf")


if __name__ == "__main__":
    unittest.main()
