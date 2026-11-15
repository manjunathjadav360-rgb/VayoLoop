import json
import unittest
from datetime import datetime

from care_passport import build_care_passport, render_care_passport_html
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

    def test_print_html_escapes_user_content_and_has_print_styles(self):
        self.workspace["contacts"][0]["name"] = "<script>alert(1)</script>"
        snapshot = build_care_passport(self.workspace, generated_at=self.now)
        rendered = render_care_passport_html(snapshot)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("@media print", rendered)
        self.assertIn("Asia/Kolkata", rendered)


if __name__ == "__main__":
    unittest.main()
