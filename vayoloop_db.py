"""Authenticated, row-scoped persistence for VayoLoop health and prescription records.

This module uses only a Supabase publishable key. RLS and private Storage
policies enforce the actual access boundaries; never add a service-role key.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

BUCKET_NAME = "vayoloop-prescriptions"
MAX_PRESCRIPTION_BYTES = 10 * 1024 * 1024

_ALLOWED_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def create_supabase_client(project_url: str, publishable_key: str) -> Any:
    """Create a per-Streamlit-session client; never share an authenticated client globally."""
    from supabase import create_client

    return create_client(project_url, publishable_key)


def get_current_user(client: Any) -> dict[str, str]:
    response = client.auth.get_user()
    user = getattr(response, "user", None)
    if user is None:
        data = getattr(response, "data", None)
        user = getattr(data, "user", None)
    if user is None or not getattr(user, "id", None):
        raise RuntimeError("The account session has expired. Please sign in again.")
    return {"id": str(user.id), "email": str(getattr(user, "email", "") or "")}


def ensure_elder_profile(client: Any, user_id: str) -> dict[str, Any]:
    """Return this account's own care profile, creating it once on first sign-in."""
    result = (
        client.table("elder_profiles")
        .select("id,display_name,preferred_language,timezone")
        .eq("created_by", user_id)
        .order("created_at")
        .limit(1)
        .execute()
    )
    rows = getattr(result, "data", None) or []
    if rows:
        return rows[0]

    created = (
        client.table("elder_profiles")
        .insert({
            "created_by": user_id,
            "display_name": "My care profile",
            "preferred_language": "en",
            "timezone": "Asia/Kolkata",
        })
        .execute()
    )
    created_rows = getattr(created, "data", None) or []
    if created_rows:
        return created_rows[0]

    # Some PostgREST configurations return no representation after INSERT.
    verify = (
        client.table("elder_profiles")
        .select("id,display_name,preferred_language,timezone")
        .eq("created_by", user_id)
        .order("created_at")
        .limit(1)
        .execute()
    )
    verify_rows = getattr(verify, "data", None) or []
    if not verify_rows:
        raise RuntimeError("Your care profile could not be created. Please try again.")
    return verify_rows[0]


def map_health_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "metric": str(row.get("metric", "Observation")),
        "value": float(row.get("value", 0)),
        "unit": str(row.get("unit", "")),
        "observed_at": str(row.get("observed_at", "")),
        "source": str(row.get("source", "Not recorded")),
        "context": row.get("context") or {},
    }


def map_prescription_record(row: dict[str, Any]) -> dict[str, Any]:
    file_name = str(row.get("original_file_name") or row.get("title") or "Prescription")
    return {
        "id": str(row.get("id", "")),
        "document_label": str(row.get("title") or file_name),
        "file_name": file_name,
        "file_type": str(row.get("file_content_type") or "application/pdf"),
        "file_size_bytes": int(row.get("file_size_bytes") or 0),
        "prescribed_on": str(row.get("prescribed_on") or ""),
        "clinic": str(row.get("clinic_name") or ""),
        "clinician": str(row.get("clinician_name") or ""),
        "condition_as_written": str(row.get("condition_as_written") or ""),
        "notes": str(row.get("notes") or ""),
        "uploaded_at": str(row.get("created_at") or ""),
        "document_path": str(row.get("document_path") or ""),
        "review_status": str(row.get("review_status") or "pending_review"),
        "is_cloud": True,
        "storage_note": "Original file is stored privately in VayoLoop Storage; access follows care-circle permissions.",
    }


def list_health_observations(client: Any, elder_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("health_observations")
        .select("id,metric,value,unit,observed_at,source,context")
        .eq("elder_id", elder_id)
        .order("observed_at", desc=True)
        .limit(1000)
        .execute()
    )
    return [map_health_record(row) for row in (getattr(result, "data", None) or [])]


def save_health_observation(
    client: Any,
    elder_id: str,
    user_id: str,
    metric: str,
    value: float,
    unit: str,
    observed_at: str,
    source: str,
) -> None:
    client.table("health_observations").insert({
        "elder_id": elder_id,
        "metric": metric,
        "value": value,
        "unit": unit,
        "observed_at": observed_at,
        "source": source,
        "context": {},
        "recorded_by": user_id,
    }).execute()


def list_prescription_records(client: Any, elder_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("prescription_records")
        .select(
            "id,title,clinician_name,prescribed_on,document_path,review_status,"
            "created_at,clinic_name,condition_as_written,notes,original_file_name,"
            "file_content_type,file_size_bytes"
        )
        .eq("elder_id", elder_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return [map_prescription_record(row) for row in (getattr(result, "data", None) or [])]


def sanitise_filename(filename: str) -> str:
    base = str(filename or "prescription").replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return (cleaned or "prescription")[:120]


def detect_prescription_mime(filename: str, declared_type: str, payload: bytes) -> str:
    """Allow only supported document signatures; the uploader's MIME label alone is not trusted."""
    extension = "." + str(filename).rsplit(".", 1)[-1].lower() if "." in str(filename) else ""
    expected = _ALLOWED_MIME.get(extension)
    if expected is None:
        raise ValueError("Upload a PDF, JPG, PNG or WebP prescription.")
    if len(payload) > MAX_PRESCRIPTION_BYTES:
        raise ValueError("This file is larger than 10 MB. Choose a smaller copy.")

    if payload.startswith(b"%PDF-"):
        actual = "application/pdf"
    elif payload.startswith(b"\x89PNG\r\n\x1a\n"):
        actual = "image/png"
    elif payload.startswith(b"\xff\xd8\xff"):
        actual = "image/jpeg"
    elif len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        actual = "image/webp"
    else:
        raise ValueError("The file contents do not look like a supported PDF or image.")

    if actual != expected:
        raise ValueError("The file extension and file contents do not match.")
    if declared_type and declared_type not in {actual, "application/octet-stream"}:
        raise ValueError("The file type reported by the browser does not match its contents.")
    return actual


def save_prescription_record(
    client: Any,
    elder_id: str,
    user_id: str,
    payload: bytes,
    filename: str,
    declared_type: str,
    title: str,
    prescribed_on: str,
    clinic_name: str,
    clinician_name: str,
    condition_as_written: str,
    notes: str,
) -> dict[str, Any]:
    mime_type = detect_prescription_mime(filename, declared_type, payload)
    safe_name = sanitise_filename(filename)
    path = f"{elder_id}/{uuid.uuid4().hex}_{safe_name}"

    client.storage.from_(BUCKET_NAME).upload(
        path,
        payload,
        {"content-type": mime_type, "upsert": "false"},
    )

    try:
        response = client.table("prescription_records").insert({
            "elder_id": elder_id,
            "title": (title or safe_name).strip()[:180],
            "clinician_name": clinician_name.strip() or None,
            "prescribed_on": prescribed_on,
            "document_path": path,
            "review_status": "pending_review",
            "created_by": user_id,
            "clinic_name": clinic_name.strip() or None,
            "condition_as_written": condition_as_written.strip() or None,
            "notes": notes.strip() or None,
            "original_file_name": safe_name,
            "file_content_type": mime_type,
            "file_size_bytes": len(payload),
        }).execute()
        rows = getattr(response, "data", None) or []
        if rows:
            return map_prescription_record(rows[0])
        loaded = list_prescription_records(client, elder_id)
        if loaded and loaded[0].get("document_path") == path:
            return loaded[0]
        raise RuntimeError("The file uploaded, but its record could not be confirmed.")
    except Exception:
        try:
            client.storage.from_(BUCKET_NAME).remove([path])
        except Exception:
            pass
        raise


def download_prescription_file(client: Any, path: str) -> bytes:
    result = client.storage.from_(BUCKET_NAME).download(path)
    if isinstance(result, bytes):
        return result
    if isinstance(result, bytearray):
        return bytes(result)
    raise RuntimeError("The stored document could not be downloaded.")


def delete_prescription_record(client: Any, elder_id: str, record_id: str, path: str) -> None:
    if path:
        client.storage.from_(BUCKET_NAME).remove([path])
    client.table("prescription_records").delete().eq("id", record_id).eq("elder_id", elder_id).execute()
