import unittest
from pathlib import Path

from vayoloop_db import (
    DEMO_WORKSPACE_ID,
    detect_prescription_mime,
    map_health_record,
    map_prescription_record,
    sanitise_filename,
    is_valid_demo_storage_path,
    save_health_observation,
    delete_prescription_record,
    download_prescription_file,
    save_prescription_record,
    parse_health_observations_csv,
    save_health_observations,
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


    def test_download_rejects_invalid_object_path_before_storage_access(self):
        class NeverCalledStorage:
            def from_(self, _bucket_name):
                raise AssertionError("Storage must not be accessed for an invalid path.")

        class Client:
            storage = NeverCalledStorage()

        with self.assertRaises(ValueError):
            download_prescription_file(
                Client(), f"{DEMO_WORKSPACE_ID}/../outside/secret.pdf"
            )

    def test_prescription_upload_cleans_orphan_file_when_metadata_insert_fails(self):
        class Bucket:
            def __init__(self):
                self.uploaded_path = None
                self.removed_paths = []
            def upload(self, path, _payload, _options):
                self.uploaded_path = path
            def remove(self, paths):
                self.removed_paths.extend(paths)

        class Storage:
            def __init__(self):
                self.bucket = Bucket()
            def from_(self, _bucket_name):
                return self.bucket

        class Query:
            def insert(self, _payload):
                return self
            def execute(self):
                raise RuntimeError("metadata insert failed")

        class Client:
            def __init__(self):
                self.storage = Storage()
                self.query = Query()
            def table(self, _table_name):
                return self.query

        client = Client()
        with self.assertRaisesRegex(RuntimeError, "metadata insert failed"):
            save_prescription_record(
                client,
                b"%PDF-1.7 synthetic test document",
                "synthetic.pdf",
                "application/pdf",
                "Synthetic test prescription",
                "2026-11-15",
                "Example clinic",
                "Example prescriber",
                "As written on sample document",
                "Fictional test only",
            )
        self.assertIsNotNone(client.storage.bucket.uploaded_path)
        self.assertEqual(
            client.storage.bucket.removed_paths,
            [client.storage.bucket.uploaded_path],
        )

    def test_prescription_upload_cleanup_failure_does_not_hide_database_error(self):
        class Bucket:
            def upload(self, _path, _payload, _options):
                pass
            def remove(self, _paths):
                raise RuntimeError("storage cleanup failed")

        class Storage:
            def from_(self, _bucket_name):
                return Bucket()

        class Query:
            def insert(self, _payload):
                return self
            def execute(self):
                raise RuntimeError("original database failure")

        class Client:
            storage = Storage()
            def table(self, _table_name):
                return Query()

        with self.assertRaisesRegex(RuntimeError, "original database failure"):
            save_prescription_record(
                Client(),
                b"%PDF-1.7 synthetic test document",
                "synthetic.pdf",
                "application/pdf",
                "Synthetic test prescription",
                "2026-11-15",
                "",
                "",
                "",
                "",
            )

    def test_prescription_upload_rejects_oversized_file_before_upload(self):
        class NeverCalledClient:
            class Storage:
                def from_(self, _bucket_name):
                    raise AssertionError("Storage must not be accessed for an oversized file.")
            storage = Storage()

        with self.assertRaises(ValueError):
            save_prescription_record(
                NeverCalledClient(),
                b"%PDF-" + (b"x" * (10 * 1024 * 1024)),
                "oversized.pdf",
                "application/pdf",
                "Oversized test",
                "2026-11-15",
                "",
                "",
                "",
                "",
            )


    def test_wearable_csv_import_parses_required_columns_and_optional_source(self):
        payload = (
            "metric,value,unit,observed_at,source\n"
            "Daily steps,4100,steps,2026-11-15T08:00:00+05:30,Example watch\n"
            "Sleep duration,7.1,hours,2026-11-14T07:30:00+05:30,\n"
        ).encode("utf-8")
        rows, duplicates = parse_health_observations_csv(payload)
        self.assertEqual(duplicates, 0)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["metric"], "Daily steps")
        self.assertEqual(rows[0]["value"], 4100.0)
        self.assertEqual(rows[1]["source"], "Imported wearable CSV")

    def test_wearable_csv_import_skips_duplicates_in_file_and_existing_history(self):
        payload = (
            "metric,value,unit,observed_at\n"
            "Daily steps,4100,steps,2026-11-15T08:00:00+05:30\n"
            "Daily steps,4100,steps,2026-11-15T02:30:00+00:00\n"
            "Sleep duration,7,hours,2026-11-15T07:00:00+05:30\n"
        ).encode("utf-8")
        existing = [{
            "metric": "daily steps",
            "value": 4100,
            "unit": "STEPS",
            "observed_at": "2026-11-15T02:30:00+00:00",
            "source": "Existing device import",
        }]
        rows, duplicates = parse_health_observations_csv(payload, existing_records=existing)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["metric"], "Sleep duration")
        self.assertEqual(duplicates, 2)

    def test_wearable_csv_import_rejects_missing_columns_and_naive_timestamps(self):
        with self.assertRaisesRegex(ValueError, "missing required column"):
            parse_health_observations_csv(
                b"metric,value,observed_at\nDaily steps,4100,2026-11-15T08:00:00+05:30\n"
            )
        with self.assertRaisesRegex(ValueError, "timezone"):
            parse_health_observations_csv(
                b"metric,value,unit,observed_at\nDaily steps,4100,steps,2026-11-15T08:00:00\n"
            )

    def test_wearable_csv_import_rejects_bad_values_and_oversized_payload(self):
        bad_rows = [
            b"Daily steps,-1,steps,2026-11-15T08:00:00+05:30",
            b"Daily steps,NaN,steps,2026-11-15T08:00:00+05:30",
            b"Daily steps,not-a-number,steps,2026-11-15T08:00:00+05:30",
        ]
        for row in bad_rows:
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    parse_health_observations_csv(
                        b"metric,value,unit,observed_at\n" + row + b"\n"
                    )
        with self.assertRaisesRegex(ValueError, "2 MB or smaller"):
            parse_health_observations_csv(b"x" * (2 * 1024 * 1024 + 1))

    def test_wearable_csv_import_enforces_row_limit(self):
        rows = ["metric,value,unit,observed_at"]
        rows.extend(
            f"Daily steps,{index},steps,2026-11-15T08:00:00+05:30"
            for index in range(501)
        )
        with self.assertRaisesRegex(ValueError, "no more than 500"):
            parse_health_observations_csv("\n".join(rows).encode("utf-8"))

    def test_bulk_health_save_validates_entire_batch_before_database_call(self):
        class NeverCalledQuery:
            def insert(self, _payload):
                raise AssertionError("No insert should happen until every row passes validation.")

        class Client:
            def table(self, _name):
                return NeverCalledQuery()

        observations = [
            {
                "metric": "Daily steps",
                "value": 4100,
                "unit": "steps",
                "observed_at": "2026-11-15T08:00:00+05:30",
                "source": "Wearable CSV",
            },
            {
                "metric": "Sleep duration",
                "value": -1,
                "unit": "hours",
                "observed_at": "2026-11-15T08:00:00+05:30",
                "source": "Wearable CSV",
            },
        ]
        with self.assertRaisesRegex(ValueError, "Observation 2"):
            save_health_observations(Client(), observations)

    def test_bulk_health_save_inserts_all_validated_rows_in_one_call(self):
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
        observations = [
            {
                "metric": "Daily steps",
                "value": 4100,
                "unit": "steps",
                "observed_at": "2026-11-15T08:00:00+05:30",
                "source": "Wearable CSV",
            },
            {
                "metric": "Sleep duration",
                "value": 7.1,
                "unit": "hours",
                "observed_at": "2026-11-15T07:30:00+05:30",
                "source": "Wearable CSV",
            },
        ]
        save_health_observations(client, observations)
        self.assertEqual(client.table_name, "vayoloop_demo_health_observations")
        self.assertTrue(client.query.executed)
        self.assertEqual(len(client.query.payload), 2)
        self.assertTrue(
            all(item["workspace_id"] == DEMO_WORKSPACE_ID for item in client.query.payload)
        )


    def test_committed_wearable_sample_csv_is_importable(self):
        sample_path = Path(__file__).resolve().parents[1] / "examples" / "wearable_export_sample.csv"
        rows, duplicates = parse_health_observations_csv(sample_path.read_bytes())
        self.assertEqual(len(rows), 7)
        self.assertEqual(duplicates, 0)
        self.assertTrue(all(row["source"] == "Example smartwatch export" for row in rows))

if __name__ == "__main__":
    unittest.main()
