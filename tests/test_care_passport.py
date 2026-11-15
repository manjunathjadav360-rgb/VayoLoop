import json
import unittest
from datetime import datetime

from care_passport import analyse_handoff_completeness, build_care_passport, render_care_passport_html
from vayoloop_core import INDIA_TZ, record_dose, seed_demo_state


class CarePassportTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 15, 10, 30, tzinfo=INDIA_TZ)
        self.workspace = seed_demo_state(self.now)

    def test_snapshot_is_serialisable_and_does_not_mutate_workspace(self):
        original_medicine_count = len(self.workspace["meds"])
        snapshot = build_care_passport(self.workspace, generated_at=self.now)
        encoded = json.dumps(snapshot, ensure_ascii=False)
        self.assertIn("VayoLoop Care Passport", encoded)
        self.assertEqual(snapshot["profile"]["timezone"], "Asia/Kolkata")
        self.assertEqual(len(self.workspace["meds"]), original_medicine_count)
        self.assertEqual(snapshot["counts"]["medicine_records"], original_medicine_count)

    def test_dose_report_is_labelled_as_self_reported(self):
        self.workspace["dose_reports"].append(
            record_dose("med-a", self.now)
        )
        snapshot = build_care_passport(self.workspace, generated_at=self.now)
        self.assertEqual(snapshot["dose_reports"][0]["source"], "Self-reported")
        self.assertIn("not proof of ingestion", snapshot["notice"].lower())

    def test_inactive_medicine_is_not_shown_as_active(self):
        self.workspace["meds"][0]["active"] = False
        snapshot = build_care_passport(self.workspace, generated_at=self.now)
        medicine = next(x for x in snapshot["medicines"] if x["name"] == "Medicine A")
        self.assertFalse(medicine["active"])
        self.assertEqual(medicine["status"], "Inactive record")
        self.assertEqual(snapshot["counts"]["active_medicines"], 2)

    def test_prescription_metadata_is_in_passport_but_file_bytes_are_not(self):
        self.workspace["prescriptions"] = [{
            "id": "rx-1",
            "document_label": "Clinic visit prescription",
            "file_name": "prescription.pdf",
            "file_type": "application/pdf",
            "file_size_bytes": 1024,
            "file_data_b64": "c2FtcGxl",
            "prescribed_on": "2026-11-15",
            "clinic": "Sample clinic",
            "clinician": "Dr Example",
            "condition_as_written": "As written on sample document",
            "notes": "Bring to next visit",
            "uploaded_at": self.now.isoformat(),
        }]
        snapshot = build_care_passport(self.workspace, generated_at=self.now)
        self.assertEqual(snapshot["counts"]["prescription_documents"], 1)
        self.assertEqual(snapshot["prescriptions"][0]["file_name"], "prescription.pdf")
        self.assertNotIn("file_data_b64", json.dumps(snapshot))
        rendered = render_care_passport_html(snapshot)
        self.assertIn("Clinic visit prescription", rendered)
        self.assertIn("Original file available only in the active demo session", rendered)

    def test_medicine_source_prescription_is_carried_into_handoff(self):
        self.workspace["prescriptions"] = [{
            "id": "rx-1",
            "document_label": "November clinic prescription",
            "file_name": "november.pdf",
            "uploaded_at": self.now.isoformat(),
        }]
        self.workspace["meds"][0]["prescription_id"] = "rx-1"
        self.workspace["meds"][1]["prescription_id"] = "rx-missing"

        snapshot = build_care_passport(self.workspace, generated_at=self.now)
        linked = next(item for item in snapshot["medicines"] if item["name"] == "Medicine A")
        missing = next(item for item in snapshot["medicines"] if item["name"] == "Medicine B")

        self.assertEqual(linked["source_prescription"], "November clinic prescription")
        self.assertEqual(missing["source_prescription"], "Source document unavailable")
        rendered = render_care_passport_html(snapshot)
        self.assertIn("Source prescription", rendered)
        self.assertIn("November clinic prescription", rendered)

    def test_handoff_display_does_not_guess_timezone_for_naive_timestamps(self):
        self.workspace["appointments"][0]["when"] = "2026-11-16T11:30:00"
        snapshot = build_care_passport(self.workspace, generated_at=self.now)
        self.assertEqual(
            snapshot["appointments"][0]["when_display"],
            "Time zone missing or invalid · review source",
        )
        checks = {item["area"]: item for item in analyse_handoff_completeness(self.workspace, self.now)}
        self.assertEqual(checks["Appointments"]["status"], "Needs review")

    def test_print_html_escapes_untrusted_values_across_handoff_sections(self):
        payload = '<script>alert("untrusted")</script>'
        self.workspace["contacts"][0]["name"] = payload
        self.workspace["appointments"][0]["provider"] = payload
        self.workspace["tasks"][0]["assignee"] = payload
        self.workspace["devices"][0]["name"] = payload
        self.workspace["health"][0]["source"] = payload
        snapshot = build_care_passport(self.workspace, generated_at=self.now)
        rendered = render_care_passport_html(snapshot)
        self.assertIn("&lt;script&gt;alert(&quot;untrusted&quot;)&lt;/script&gt;", rendered)
        self.assertNotIn(payload, rendered)
        self.assertIn("@media print", rendered)
        self.assertIn("Asia/Kolkata", rendered)


    def test_handoff_review_accepts_complete_synthetic_records_and_marks_empty_sections(self):
        checks = {item["area"]: item for item in analyse_handoff_completeness(self.workspace)}
        self.assertEqual(checks["Medication records"]["status"], "Ready for review")
        self.assertEqual(checks["Health observations"]["status"], "Ready for review")
        self.assertEqual(checks["Appointments"]["status"], "Ready for review")
        self.assertEqual(checks["Trusted contacts"]["status"], "Ready for review")
        self.assertEqual(checks["Family care tasks"]["status"], "Ready for review")
        self.assertEqual(checks["Prescription documents"]["status"], "No records")

    def test_handoff_review_flags_missing_fields_and_broken_source_references(self):
        self.workspace["meds"][0]["strength"] = ""
        self.workspace["meds"][0]["prescription_id"] = "missing-document"
        self.workspace["appointments"][0]["provider"] = ""
        self.workspace["contacts"][0]["relationship"] = ""
        self.workspace["health"][0]["observed_at"] = "2026-11-15T08:30:00"

        checks = {item["area"]: item for item in analyse_handoff_completeness(self.workspace)}
        self.assertEqual(checks["Medication records"]["status"], "Needs review")
        self.assertEqual(checks["Medication records"]["review_items"], 2)
        self.assertIn("1 point to missing documents", checks["Medication records"]["details"])
        self.assertEqual(checks["Appointments"]["status"], "Needs review")
        self.assertEqual(checks["Trusted contacts"]["status"], "Needs review")
        self.assertEqual(checks["Health observations"]["status"], "Needs review")

    def test_handoff_review_is_read_only_and_handles_an_empty_workspace(self):
        import copy

        workspace = {
            "meds": [], "prescriptions": [], "health": [], "appointments": [],
            "contacts": [], "tasks": [],
        }
        before = copy.deepcopy(workspace)
        checks = analyse_handoff_completeness(workspace)
        self.assertTrue(all(item["status"] == "No records" for item in checks))
        self.assertEqual(workspace, before)



    def test_handoff_review_flags_stale_appointments_and_overdue_tasks(self):
        self.workspace["appointments"][0]["when"] = "2026-11-14T11:30:00+05:30"
        self.workspace["tasks"][0]["due"] = "2026-11-14T19:00:00+05:30"
        checks = {
            item["area"]: item
            for item in analyse_handoff_completeness(
                self.workspace,
                now=datetime(2026, 11, 15, 10, 30, tzinfo=INDIA_TZ),
            )
        }
        self.assertEqual(checks["Appointments"]["status"], "Needs review")
        self.assertIn("1 scheduled visit(s) are in the past", checks["Appointments"]["details"])
        self.assertEqual(checks["Family care tasks"]["status"], "Needs review")
        self.assertIn("1 uncompleted task(s) are past due", checks["Family care tasks"]["details"])

    def test_handoff_review_flags_duplicate_contact_priorities_and_invalid_health_values(self):
        self.workspace["contacts"][1]["priority"] = self.workspace["contacts"][0]["priority"]
        self.workspace["health"][0]["value"] = -1
        self.workspace["health"][1]["value"] = True
        checks = {
            item["area"]: item
            for item in analyse_handoff_completeness(
                self.workspace,
                now=datetime(2026, 11, 15, 10, 30, tzinfo=INDIA_TZ),
            )
        }
        self.assertEqual(checks["Trusted contacts"]["status"], "Needs review")
        self.assertIn("1 duplicate priority value(s)", checks["Trusted contacts"]["details"])
        self.assertEqual(checks["Health observations"]["status"], "Needs review")

if __name__ == "__main__":
    unittest.main()
