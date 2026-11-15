"""Portable, read-only care handoff exports for the VayoLoop demo."""
from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

from vayoloop_core import INDIA_TZ, india_now, medication_state


def _display_time(value: str | None) -> str:
    if not value:
        return "Not recorded"
    try:
        return datetime.fromisoformat(value).astimezone(INDIA_TZ).strftime("%d %b %Y, %I:%M %p IST")
    except (TypeError, ValueError):
        return str(value)


def build_care_passport(
    workspace: dict[str, Any],
    profile_name: str = "Asha Rao",
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a serialisable snapshot without mutating the active demo workspace."""
    stamp = generated_at or india_now()
    medicine_names = {item["id"]: item["name"] for item in workspace.get("meds", [])}

    medicines = []
    for item in sorted(workspace.get("meds", []), key=lambda value: (not value.get("active", True), value.get("time", ""))):
        active = bool(item.get("active", True))
        medicines.append({
            "name": item.get("name", "Unlabelled medicine"),
            "label": item.get("strength", "Not entered"),
            "scheduled_time": item.get("time", "Not set"),
            "routine_note": item.get("instructions", ""),
            "active": active,
            "status": medication_state(item, workspace.get("dose_reports", []), stamp) if active else "Inactive record",
            "approx_supply_units": item.get("remaining_units"),
        })

    dose_reports = []
    for report in sorted(workspace.get("dose_reports", []), key=lambda value: value.get("reported_at", ""), reverse=True)[:12]:
        dose_reports.append({
            "medicine": medicine_names.get(report.get("medication_id"), "Medicine record"),
            "reported_at": report.get("reported_at"),
            "reported_at_display": _display_time(report.get("reported_at")),
            "source": report.get("source", "Self-reported"),
        })

    health_observations = []
    for reading in sorted(workspace.get("health", []), key=lambda value: value.get("observed_at", ""), reverse=True)[:20]:
        health_observations.append({
            "metric": reading.get("metric", "Observation"),
            "value": reading.get("value"),
            "unit": reading.get("unit", ""),
            "observed_at": reading.get("observed_at"),
            "observed_at_display": _display_time(reading.get("observed_at")),
            "source": reading.get("source", "Not recorded"),
        })

    prescriptions = []
    for item in sorted(workspace.get("prescriptions", []), key=lambda value: value.get("uploaded_at", ""), reverse=True):
        prescriptions.append({
            "document_label": item.get("document_label", "Prescription document"),
            "file_name": item.get("file_name", "Document"),
            "prescribed_on": item.get("prescribed_on", "Not recorded"),
            "clinic": item.get("clinic", ""),
            "clinician": item.get("clinician", ""),
            "condition_as_written": item.get("condition_as_written", ""),
            "notes": item.get("notes", ""),
            "file_size_bytes": item.get("file_size_bytes", 0),
            "uploaded_at_display": _display_time(item.get("uploaded_at")),
            "storage_note": "Original file available only in the active demo session",
        })

    appointments = []
    for item in sorted(workspace.get("appointments", []), key=lambda value: value.get("when", "")):
        appointments.append({
            "visit": item.get("title", "Appointment"),
            "provider": item.get("provider", "Not specified"),
            "when": item.get("when"),
            "when_display": _display_time(item.get("when")),
            "status": item.get("status", "Not specified"),
            "note": item.get("note", ""),
        })

    latest_checkin = None
    checkins = workspace.get("checkins", [])
    if checkins:
        item = sorted(checkins, key=lambda value: value.get("at", ""), reverse=True)[0]
        latest_checkin = {
            "recorded_at": item.get("at"),
            "recorded_at_display": _display_time(item.get("at")),
            "meals": item.get("meals", "Not recorded"),
            "hydration": item.get("hydration", "Not recorded"),
            "mood": item.get("mood", "Not recorded"),
            "note": item.get("note", ""),
        }

    care_circle = [
        {
            "name": item.get("name", "Unnamed contact"),
            "relationship": item.get("relationship", "Not specified"),
            "priority": item.get("priority", 99),
        }
        for item in sorted(workspace.get("contacts", []), key=lambda value: value.get("priority", 99))
    ]
    family_tasks = [
        {
            "task": item.get("title", "Care task"),
            "assignee": item.get("assignee", "Unassigned"),
            "due": item.get("due"),
            "due_display": _display_time(item.get("due")),
            "status": item.get("status", "Planned"),
        }
        for item in sorted(workspace.get("tasks", []), key=lambda value: value.get("due", ""))
    ]
    connected_devices = [
        {
            "name": item.get("name", "Device"),
            "kind": item.get("kind", "Device"),
            "provider": item.get("provider", "Not specified"),
            "status": item.get("status", "Unknown"),
            "last_sync": item.get("last_sync"),
            "last_sync_display": _display_time(item.get("last_sync")),
        }
        for item in workspace.get("devices", [])
    ]
    closed_states = {"Closed · person confirmed okay", "Closed · demo resolved"}
    active_safety_events = [
        {
            "event_type": item.get("event_type", "Safety event"),
            "created_at_display": _display_time(item.get("created_at")),
            "status": item.get("status", "Unknown"),
            "demo_only": True,
        }
        for item in workspace.get("emergency_events", [])
        if item.get("status") not in closed_states
    ]

    return {
        "document_title": "VayoLoop Care Passport",
        "profile": {
            "name": profile_name,
            "generated_at": stamp.isoformat(timespec="seconds"),
            "generated_at_display": _display_time(stamp.isoformat()),
            "timezone": "Asia/Kolkata",
        },
        "notice": (
            "Synthetic hackathon demo export. Not a prescription, diagnosis, clinical assessment "
            "or emergency response record. Dose reports are self-reported and are not proof of ingestion."
        ),
        "medicines": medicines,
        "prescriptions": prescriptions,
        "dose_reports": dose_reports,
        "health_observations": health_observations,
        "appointments": appointments,
        "latest_wellbeing_checkin": latest_checkin,
        "care_circle": care_circle,
        "family_tasks": family_tasks,
        "connected_devices": connected_devices,
        "active_safety_events": active_safety_events,
        "counts": {
            "medicine_records": len(medicines),
            "active_medicines": sum(1 for item in medicines if item["active"]),
            "prescription_documents": len(prescriptions),
            "health_observations_included": len(health_observations),
            "appointments": len(appointments),
            "trusted_contacts": len(care_circle),
            "active_demo_safety_events": len(active_safety_events),
        },
    }


def render_care_passport_html(snapshot: dict[str, Any]) -> str:
    """Render an escaped, print-friendly HTML handoff document."""
    def cell(value: Any) -> str:
        if value is None or value == "":
            return "—"
        return escape(str(value))

    def table(headers: list[str], rows: list[list[Any]]) -> str:
        if not rows:
            rows = [["No records"] + [""] * (len(headers) - 1)]
        head = "".join(f"<th>{cell(header)}</th>" for header in headers)
        body = "".join("<tr>" + "".join(f"<td>{cell(value)}</td>" for value in row) + "</tr>" for row in rows)
        return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"

    meds = [
        [x["name"], x["label"], x["scheduled_time"], x["status"], x["approx_supply_units"]]
        for x in snapshot["medicines"]
    ]
    doses = [[x["medicine"], x["reported_at_display"], x["source"]] for x in snapshot["dose_reports"]]
    prescriptions = [[x["document_label"], x["prescribed_on"], x["clinic"], x["clinician"], x["file_name"], x["storage_note"]] for x in snapshot.get("prescriptions", [])]
    health = [[x["metric"], f'{x["value"]} {x["unit"]}', x["observed_at_display"], x["source"]] for x in snapshot["health_observations"]]
    appointments = [[x["visit"], x["provider"], x["when_display"], x["status"], x["note"]] for x in snapshot["appointments"]]
    contacts = [[x["priority"], x["name"], x["relationship"]] for x in snapshot["care_circle"]]
    tasks = [[x["task"], x["assignee"], x["due_display"], x["status"]] for x in snapshot["family_tasks"]]
    devices = [[x["name"], x["kind"], x["provider"], x["status"], x["last_sync_display"]] for x in snapshot["connected_devices"]]
    safety = [[x["event_type"], x["created_at_display"], x["status"], "Demo only"] for x in snapshot["active_safety_events"]]

    checkin = snapshot.get("latest_wellbeing_checkin")
    if checkin:
        wellbeing = table(
            ["Recorded", "Meals", "Water check-in", "How they feel", "Note"],
            [[checkin["recorded_at_display"], checkin["meals"], checkin["hydration"], checkin["mood"], checkin["note"]]],
        )
    else:
        wellbeing = "<p class='empty'>No wellbeing check-in has been recorded in this session.</p>"

    sections = [
        ("Medication plan", table(["Medicine", "Label / strength", "Scheduled", "Current status", "Approx. supply units"], meds)),
        ("Prescription documents", table(["Document", "Prescription date", "Clinic", "Prescriber", "File", "Availability"], prescriptions)),
        ("Recent dose reports", table(["Medicine", "Reported at", "Record source"], doses)),
        ("Recent health observations", table(["Observation", "Recorded value", "Observed at", "Source"], health)),
        ("Appointments", table(["Visit", "Provider", "When", "Status", "Note"], appointments)),
        ("Latest wellbeing check-in", wellbeing),
        ("Trusted care circle", table(["Priority", "Name", "Relationship"], contacts)),
        ("Family care tasks", table(["Task", "Assigned to", "Due", "Status"], tasks)),
        ("Connected device register", table(["Device", "Type", "Provider", "Status", "Last sync"], devices)),
        ("Open safety test events", table(["Event", "Created", "Status", "Scope"], safety)),
    ]
    section_html = "".join(
        f"<section><h2>{cell(title)}</h2>{content}</section>"
        for title, content in sections
    )
    profile = snapshot["profile"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cell(snapshot["document_title"])}</title>
<style>
:root{{color-scheme:light;--ink:#20352e;--muted:#63746a;--line:#e5e8df;--green:#245b49;--paper:#f7f7f1}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:14px/1.5 Arial,sans-serif}}
main{{max-width:1040px;margin:28px auto;padding:0 22px 40px}}
header{{background:#244d3f;color:white;padding:25px 28px;border-radius:14px;margin-bottom:18px}}
header .eyebrow{{font-size:11px;letter-spacing:2px;font-weight:bold;color:#d2e0d3}}
h1{{font-size:28px;margin:7px 0 3px}}header p{{margin:0;color:#e0e9df}}
.meta{{margin:14px 0 0;font-size:12px;color:#e0e9df}}
.notice{{border-left:4px solid #b58a43;background:#f5efdf;padding:12px 14px;border-radius:0 8px 8px 0;color:#695536;margin:0 0 18px}}
section{{background:white;border:1px solid var(--line);border-radius:12px;padding:17px 18px;margin:13px 0;break-inside:avoid}}
h2{{font-size:16px;margin:0 0 11px;color:var(--green)}}
.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;background:#f1f4ee;color:#4f6457;font-size:11px}}
th,td{{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}}
tr:last-child td{{border-bottom:0}}.empty{{color:var(--muted);margin:0}}
footer{{color:var(--muted);font-size:11px;text-align:center;padding:15px}}
@media print{{body{{background:white}}main{{max-width:none;margin:0;padding:0}}header{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}section{{box-shadow:none;break-inside:avoid}}.notice{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}}}
</style>
</head>
<body><main>
<header><div class="eyebrow">VAYOLOOP · CARE BEYOND REMINDERS</div>
<h1>{cell(snapshot["document_title"])}</h1>
<p>An elder-led care handoff summary</p>
<div class="meta">Profile: {cell(profile["name"])} · Generated: {cell(profile["generated_at_display"])} · Time zone: {cell(profile["timezone"])}</div></header>
<div class="notice">{cell(snapshot["notice"])} Share only with the elder's permission and intended care circle.</div>
{section_html}
<footer>VayoLoop · Synthetic demo export · This document does not replace the original prescription or advice from a qualified clinician.</footer>
</main></body></html>"""
