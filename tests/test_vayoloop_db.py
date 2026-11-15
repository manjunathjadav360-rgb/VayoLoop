import unittest

from vayoloop_db import (
    DEMO_WORKSPACE_ID,
    detect_prescription_mime,
    map_health_record,
    map_prescription_record,
    sanitise_filename,
    is_valid_demo_storage_path,
    save_health_observation,
    delete_prescription_record,
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



    def test_demo_storage_paths_are_restricted_to_one_generated_object(self):
        valid = f"{DEMO_WORKSPACE_ID}/{'a' * 32}_prescription.pdf"
        self.assertTrue(is_valid_demo_storage_path(valid))
        for invalid in [
            "",
            f"{DEMO_WORKSPACE_ID}/../other/file.pdf",
            f"{DEMO_WORKSPACE_ID}/nested/file.pdf",
            "00000000-0000-4000-8000-000000000002/" + "a" * 32 + "_file.pdf",
            f"{DEMO_WORKSPACE_ID}/not-a-generated-key.pdf",
        ]:
            with self.subTest(path=invalid):
                self.assertFalse(is_valid_demo_storage_path(path=invalid))

    def test_delete_rejects_invalid_path_before_touching_database(self):
        class NeverCalledClient:
            def table(self, _name):
                raise AssertionError("Database must not be changed for an invalid path.")

        with self.assertRaises(ValueError):
            delete_prescription_record(
                NeverCalledClient(),
                "record-1",
                f"{DEMO_WORKSPACE_ID}/../outside/file.pdf",
            )

    def test_health_observation_validation_rejects_bad_values_before_database_call(self):
        valid_time = "2026-11-15T10:00:00+05:30"
        bad_inputs = [
            ("", 12, "steps", valid_time, "Entered by family"),
            ("x" * 121, 12, "steps", valid_time, "Entered by family"),
            ("Daily steps", -1, "steps", valid_time, "Entered by family"),
            ("Daily steps", float("nan"), "steps", valid_time, "Entered by family"),
            ("Daily steps", 12, "u" * 33, valid_time, "Entered by family"),
            ("Daily steps", 12, "steps", "not-a-date", "Entered by family"),
            ("Daily steps", 12, "steps", "2026-11-15T10:00:00", "Entered by family"),
        ]
        for metric, value, unit, observed_at, source in bad_inputs:
            with self.subTest(metric=metric, value=value, unit=unit, observed_at=observed_at):
                with self.assertRaises(ValueError):
                    save_health_observation(
                        object(), metric, value, unit, observed_at, source
                    )

    def test_health_observation_saves_normalised_payload(self):
        class Query:
            def insert(self, payload):
                self.payload = payload
                return self
            def execute(self):
                self.executed = True

        class Client:
            def __init__(self):
                self.query = Query()
                self.table_name = None
            def table(self, name):
                self.table_name = name
                return self.query

        client = Client()
        save_health_observation(
            client, " Daily steps ", 12, " steps ",
            "2026-11-15T10:00:00+05:30", " Entered by family "
        )
        self.assertEqual(client.table_name, "vayoloop_demo_health_observations")
        self.assertTrue(client.query.executed)
        self.assertEqual(client.query.payload["workspace_id"], DEMO_WORKSPACE_ID)
        self.assertEqual(client.query.payload["metric"], "Daily steps")
        self.assertEqual(client.query.payload["value"], 12.0)
        self.assertEqual(client.query.payload["unit"], "steps")

if __name__ == "__main__":
    unittest.main()
