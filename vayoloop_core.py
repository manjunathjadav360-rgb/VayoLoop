"""Pure demo-domain logic for VayoLoop. All records are synthetic and session-scoped."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import secrets

INDIA_TZ = ZoneInfo("Asia/Kolkata")


def india_now() -> datetime:
    return datetime.now(INDIA_TZ)


def iso_now(value: datetime | None = None) -> str:
    return (value or india_now()).isoformat(timespec="seconds")


def make_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


def seed_demo_state(now: datetime | None = None) -> dict:
    now = now or india_now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    def at(day_offset: int, hour: int, minute: int = 0) -> str:
        return (today + timedelta(days=day_offset, hours=hour, minutes=minute)).isoformat(timespec="seconds")

    meds = [
        {"id": "med-a", "name": "Medicine A", "strength": "Sample label A", "time": "08:00", "instructions": "Example routine note", "remaining_units": 18, "active": True},
        {"id": "med-b", "name": "Medicine B", "strength": "Sample label B", "time": "13:00", "instructions": "Example routine note", "remaining_units": 7, "active": True},
        {"id": "med-c", "name": "Medicine C", "strength": "Sample label C", "time": "20:00", "instructions": "Example routine note", "remaining_units": 3, "active": True},
    ]
    health = []
    step_values = [2850, 3220, 3610, 3980, 4240, 4610, 4920]
    sleep_values = [7.2, 7.0, 6.9, 7.1, 6.8, 6.7, 6.5]
    for index in range(7):
        observed = today - timedelta(days=6-index) + timedelta(hours=8)
        health.append({"id": make_id("h"), "metric": "Daily steps", "value": step_values[index], "unit": "steps", "observed_at": observed.isoformat(timespec="seconds"), "source": "Demo wearable"})
        health.append({"id": make_id("h"), "metric": "Sleep duration", "value": sleep_values[index], "unit": "hours", "observed_at": (observed + timedelta(minutes=15)).isoformat(timespec="seconds"), "source": "Demo wearable"})
    health.extend([
        {"id": make_id("h"), "metric": "Resting heart rate", "value": 72, "unit": "bpm", "observed_at": at(-1, 8, 30), "source": "Demo wearable"},
        {"id": make_id("h"), "metric": "Resting heart rate", "value": 74, "unit": "bpm", "observed_at": at(0, 8, 30), "source": "Demo wearable"},
    ])
    return {
        "meds": meds,
        "health": health,
        "appointments": [
            {"id": "apt-a", "title": "Routine wellness visit", "provider": "Example family clinic", "when": at(1, 11, 30), "status": "Scheduled", "note": "Fictional demo appointment"},
            {"id": "apt-b", "title": "Follow-up consultation", "provider": "Community clinic demo", "when": at(5, 15), "status": "Scheduled", "note": "Bring the demo care summary"},
        ],
        "devices": [
            {"id": "dev-a", "name": "Asha's demo watch", "kind": "Smartwatch", "provider": "Demo wearable", "status": "Simulated", "last_sync": at(0, 8, 30)},
            {"id": "dev-b", "name": "Hall motion sensor", "kind": "Motion sensor", "provider": "Demo home hub", "status": "Simulated", "last_sync": at(0, 7, 50)},
        ],
        "members": [
            {"id": "mem-a", "name": "Asha Rao", "relationship": "Elder / profile owner", "role": "Elder", "permission": "Own profile"},
            {"id": "mem-b", "name": "Meera Rao", "relationship": "Daughter", "role": "Family", "permission": "Read-only demo access"},
            {"id": "mem-c", "name": "Arjun Patel", "relationship": "Caregiver", "role": "Caregiver", "permission": "Care coordination demo access"},
        ],
        "contacts": [
            {"id": "contact-1", "name": "Meera Rao", "relationship": "Daughter · primary contact", "priority": 1},
            {"id": "contact-2", "name": "Arjun Patel", "relationship": "Son · backup contact", "priority": 2},
            {"id": "contact-3", "name": "Savita Desai", "relationship": "Trusted nearby helper", "priority": 3},
        ],
        "tasks": [
            {"id": "task-1", "title": "Evening check-in call", "assignee": "Meera Rao", "due": at(0, 19), "status": "Planned"},
            {"id": "task-2", "title": "Accompany to clinic", "assignee": "Arjun Patel", "due": at(1, 10, 45), "status": "Planned"},
        ],
        "checkins": [],
        "dose_reports": [],
        "events": [
            {"id": make_id("event"), "title": "Sample morning routine", "detail": "Fictional demo activity · not a verified medicine event", "at": at(0, 8, 5)},
            {"id": make_id("event"), "title": "Demo wearable sync", "detail": "Illustrative steps and sleep sample", "at": at(0, 8, 30)},
        ],
        "emergency_events": [],
        "invitations": [],
        "resources": [],
    }


def create_emergency_event(event_type: str, contacts: list[dict], now: datetime | None = None) -> dict:
    now = now or india_now()
    immediate = event_type == "Manual SOS"
    return {
        "id": make_id("emergency"),
        "event_type": event_type,
        "created_at": iso_now(now),
        "status": "Family alerts simulated" if immediate else "Awaiting person confirmation",
        "severity": "Urgent" if immediate else "Needs verification",
        "contact_updates": [
            {"contact_id": c["id"], "name": c["name"], "relationship": c["relationship"], "priority": c["priority"], "status": "Simulated alert queued" if immediate else "Not notified"}
            for c in sorted(contacts, key=lambda item: item["priority"])
        ],
        "acknowledged_by": None,
        "resolved_at": None,
        "demo_only": True,
    }


def escalate_emergency(event: dict, now: datetime | None = None) -> dict:
    updated = deepcopy(event)
    updated["status"] = "Family alerts simulated"
    updated["severity"] = "Urgent · response required"
    for contact in updated["contact_updates"]:
        contact["status"] = "Simulated alert queued"
    updated["escalated_at"] = iso_now(now)
    return updated


def acknowledge_emergency_contact(event: dict, contact_id: str, now: datetime | None = None) -> dict:
    updated = deepcopy(event)
    for contact in updated["contact_updates"]:
        if contact["contact_id"] == contact_id:
            contact["status"] = "Acknowledged in demo"
            updated["acknowledged_by"] = contact["name"]
            updated["acknowledged_at"] = iso_now(now)
            updated["status"] = "Contact acknowledged"
            break
    return updated


def close_emergency_event(event: dict, now: datetime | None = None, safe: bool = False) -> dict:
    updated = deepcopy(event)
    updated["status"] = "Closed · person confirmed okay" if safe else "Closed · demo resolved"
    updated["resolved_at"] = iso_now(now)
    return updated


def medication_state(medication: dict, reports: list[dict], now: datetime | None = None) -> str:
    now = now or india_now()
    today = now.date().isoformat()
    reported = any(r["medication_id"] == medication["id"] and r["reported_at"][:10] == today for r in reports)
    if reported:
        return "Reported today"
    hour, minute = (int(part) for part in medication["time"].split(":"))
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < scheduled:
        return "Upcoming"
    if now <= scheduled + timedelta(minutes=30):
        return "Due · awaiting report"
    return "Overdue · unconfirmed"


def record_dose(medication_id: str, now: datetime | None = None) -> dict:
    return {
        "id": make_id("dose"),
        "medication_id": medication_id,
        "reported_at": iso_now(now),
        "source": "Self-reported",
    }
