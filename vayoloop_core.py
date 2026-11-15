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
        "prescriptions": [],
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



def analyse_health_trends(
    records: list[dict],
    now: datetime | None = None,
    window_size: int = 3,
) -> list[dict]:
    """Summarise numeric history by metric and unit without making clinical judgements.

    A rolling comparison is returned only when there are enough observations for
    two complete windows. Values are never labelled as medically good or bad.
    """
    from math import isfinite

    if window_size < 1:
        raise ValueError("window_size must be at least 1")

    current = now or india_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=INDIA_TZ)
    current = current.astimezone(INDIA_TZ)

    grouped: dict[tuple[str, str], list[dict]] = {}
    for record in records or []:
        metric = str(record.get("metric") or "Observation").strip() or "Observation"
        unit = str(record.get("unit") or "").strip()
        raw_value = record.get("value")
        if isinstance(raw_value, bool):
            continue
        try:
            value = float(raw_value)
            observed = datetime.fromisoformat(
                str(record.get("observed_at") or "").replace("Z", "+00:00")
            )
        except (TypeError, ValueError, OverflowError):
            continue
        if not isfinite(value):
            continue
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=INDIA_TZ)
        observed = observed.astimezone(INDIA_TZ)
        grouped.setdefault((metric, unit), []).append({
            "value": value,
            "observed": observed,
            "source": str(record.get("source") or "Not recorded"),
        })

    summaries = []
    for (metric, unit), readings in sorted(grouped.items()):
        readings.sort(key=lambda item: item["observed"])
        values = [item["value"] for item in readings]
        latest = readings[-1]
        previous = readings[-2] if len(readings) >= 2 else None
        change = latest["value"] - previous["value"] if previous else None

        def direction(value: float | None) -> str:
            if value is None:
                return "Not enough data"
            if value > 0:
                return "Increasing"
            if value < 0:
                return "Decreasing"
            return "Unchanged"

        recent_average = previous_average = window_change = None
        window_direction = "Not enough data"
        required = window_size * 2
        if len(values) >= required:
            previous_window = values[-required:-window_size]
            recent_window = values[-window_size:]
            previous_average = sum(previous_window) / window_size
            recent_average = sum(recent_window) / window_size
            window_change = recent_average - previous_average
            window_direction = direction(window_change)

        age_seconds = (current - latest["observed"]).total_seconds()
        if age_seconds < -300:
            freshness = "Future-dated"
        elif latest["observed"].date() == current.date():
            freshness = "Updated today"
        else:
            age_days = max(0, (current.date() - latest["observed"].date()).days)
            freshness = f"Updated {age_days} day{'s' if age_days != 1 else ''} ago"

        summaries.append({
            "metric": metric,
            "unit": unit,
            "count": len(readings),
            "latest_value": latest["value"],
            "latest_at": latest["observed"].isoformat(timespec="seconds"),
            "previous_value": previous["value"] if previous else None,
            "change_vs_previous": change,
            "direction_vs_previous": direction(change),
            "previous_average": previous_average,
            "recent_average": recent_average,
            "window_change": window_change,
            "window_direction": window_direction,
            "window_size": window_size,
            "freshness": freshness,
            "readings": [
                {
                    "value": item["value"],
                    "observed_at": item["observed"].isoformat(timespec="seconds"),
                    "source": item["source"],
                }
                for item in readings
            ],
        })
    return summaries


def record_dose(medication_id: str, now: datetime | None = None) -> dict:
    return {
        "id": make_id("dose"),
        "medication_id": medication_id,
        "reported_at": iso_now(now),
        "source": "Self-reported",
    }
