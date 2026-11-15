import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from vayoloop_core import (
    INDIA_TZ,
    analyse_health_trends,
    acknowledge_emergency_contact,
    close_emergency_event,
    create_emergency_event,
    escalate_emergency,
    medication_state,
    record_dose,
    seed_demo_state,
)


class VayoLoopCoreTests(unittest.TestCase):
    def setUp(self):
        self.contacts = [
            {"id": "c1", "name": "Meera", "relationship": "Daughter", "priority": 1},
            {"id": "c2", "name": "Arjun", "relationship": "Son", "priority": 2},
        ]

    def test_possible_fall_waits_for_confirmation(self):
        event = create_emergency_event("Possible fall signal", self.contacts)
        self.assertEqual(event["status"], "Awaiting person confirmation")
        self.assertTrue(all(x["status"] == "Not notified" for x in event["contact_updates"]))

    def test_manual_sos_queues_immediate_demo_alerts(self):
        event = create_emergency_event("Manual SOS", self.contacts)
        self.assertEqual(event["status"], "Family alerts simulated")
        self.assertTrue(all(x["status"] == "Simulated alert queued" for x in event["contact_updates"]))

    def test_escalation_and_acknowledgement_are_auditable(self):
        event = create_emergency_event("Possible fall signal", self.contacts)
        event = escalate_emergency(event)
        self.assertEqual(event["status"], "Family alerts simulated")
        event = acknowledge_emergency_contact(event, "c2")
        self.assertEqual(event["status"], "Contact acknowledged")
        self.assertEqual(event["acknowledged_by"], "Arjun")
        self.assertEqual(event["contact_updates"][1]["status"], "Acknowledged in demo")

    def test_close_event_does_not_mutate_original(self):
        event = create_emergency_event("Possible fall signal", self.contacts)
        closed = close_emergency_event(event, safe=True)
        self.assertEqual(closed["status"], "Closed · person confirmed okay")
        self.assertIsNone(event["resolved_at"])

    def test_medication_state_uses_self_report_only(self):
        now = datetime(2026, 11, 15, 9, 0, tzinfo=INDIA_TZ)
        med = {"id": "m1", "time": "08:00"}
        self.assertEqual(medication_state(med, [], now), "Overdue · unconfirmed")
        report = {"medication_id": "m1", "reported_at": "2026-11-15T09:00:00+05:30"}
        self.assertEqual(medication_state(med, [report], now), "Reported today")

    def test_medicine_due_is_not_overdue_before_schedule(self):
        now = datetime(2026, 11, 15, 7, 59, tzinfo=INDIA_TZ)
        med = {"id": "m1", "time": "08:00"}
        self.assertEqual(medication_state(med, [], now), "Upcoming")

    def test_seed_state_is_synthetic_and_has_india_timezone_dates(self):
        state = seed_demo_state(datetime(2026, 11, 15, 10, 0, tzinfo=INDIA_TZ))
        self.assertEqual(len(state["meds"]), 3)
        self.assertEqual(len(state["contacts"]), 3)
        self.assertEqual(state["meds"][0]["name"], "Medicine A")
        self.assertTrue(state["appointments"][0]["when"].endswith("+05:30"))

    def test_health_trend_compares_two_rolling_windows(self):
        now = datetime(2026, 11, 15, 10, 0, tzinfo=INDIA_TZ)
        records = [
            {
                "metric": "Daily steps",
                "unit": "steps",
                "value": value,
                "observed_at": (now.replace(hour=8) - timedelta(days=5-index)).isoformat(),
                "source": "Demo wearable",
            }
            for index, value in enumerate([100, 200, 300, 400, 500, 600])
        ]
        result = analyse_health_trends(records, now=now)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["latest_value"], 600)
        self.assertEqual(result[0]["change_vs_previous"], 100)
        self.assertEqual(result[0]["previous_average"], 200)
        self.assertEqual(result[0]["recent_average"], 500)
        self.assertEqual(result[0]["window_direction"], "Increasing")
        self.assertEqual(result[0]["freshness"], "Updated today")

    def test_health_trend_separates_units_and_requires_enough_history(self):
        now = datetime(2026, 11, 15, 10, 0, tzinfo=INDIA_TZ)
        records = [
            {"metric": "Weight", "unit": unit, "value": value,
             "observed_at": (now.replace(hour=8) - timedelta(days=index)).isoformat()}
            for unit, values in [("kg", [60, 61]), ("lb", [132, 134])]
            for index, value in enumerate(values)
        ]
        result = analyse_health_trends(records, now=now)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(item["window_change"] is None for item in result))
        self.assertTrue(all(item["count"] == 2 for item in result))

    def test_health_trend_skips_invalid_and_non_finite_records(self):
        now = datetime(2026, 11, 15, 10, 0, tzinfo=INDIA_TZ)
        records = [
            {"metric": "Sleep", "unit": "hours", "value": 7,
             "observed_at": now.isoformat()},
            {"metric": "Sleep", "unit": "hours", "value": "NaN",
             "observed_at": now.isoformat()},
            {"metric": "Sleep", "unit": "hours", "value": "bad",
             "observed_at": now.isoformat()},
            {"metric": "Sleep", "unit": "hours", "value": 6.5,
             "observed_at": "not-a-date"},
        ]
        result = analyse_health_trends(records, now=now)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["count"], 1)
        self.assertEqual(result[0]["direction_vs_previous"], "Not enough data")

    def test_record_dose_is_marked_self_reported(self):
        report = record_dose("m1", datetime(2026, 11, 15, 10, 0, tzinfo=INDIA_TZ))
        self.assertEqual(report["source"], "Self-reported")
        self.assertEqual(report["medication_id"], "m1")


if __name__ == "__main__":
    unittest.main()
