"""Shared synthetic demo persistence for VayoLoop.

There is intentionally no sign-in or account UI. The public hackathon demo uses
one shared workspace and therefore must contain fictional data only. Database
policies scope all access to one fixed demo workspace; no service-role key is
used or embedded in the application.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

DEMO_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"
BUCKET_NAME = "vayoloop-prescriptions"
MAX_PRESCRIPTION_BYTES = 10 * 1024 * 1024

# A Supabase publishable key is intended for public clients. RLS policies limit
# this app to a single fictional demo workspace. A secret/service-role key is
# never used here.
DEFAULT_SUPABASE_URL = "https://vhugnytmbjktbhlspgyx.supabase.co"
DEFAULT_SUPABASE_PUBLISHABLE_KEY = "sb_publishable_2SxGxrtA5oPY1h6oDaBUMw_DLrVbRdU"

_ALLOWED_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def create_supabase_client(project_url: str = DEFAULT_SUPABASE_URL,
                           publishable_key: str = DEFAULT_SUPABASE_PUBLISHABLE_KEY) -> Any:
    """Create an unauthenticated client using the public publishable key."""
    if not project_url or not publishable_key:
        raise ValueError("VayoLoop demo storage is not configured.")
    from supabase import create_client
    return create_client(project_url, publishable_key)


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
        "storage_note": "Original file is in the shared demo workspace; use fictional documents only.",
    }


def list_health_observations(client: Any) -> list[dict[str, Any]]:
    result = (
        client.table("vayoloop_demo_health_observations")
        .select("id,metric,value,unit,observed_at,source,context")
        .eq("workspace_id", DEMO_WORKSPACE_ID)
        .order("observed_at", desc=True)
        .limit(1000)
        .execute()
    )
    return [map_health_record(row) for row in (getattr(result, "data", None) or [])]


def save_health_observation(
    client: Any,
    metric: str,
    value: float,
    unit: str,
    observed_at: str,
    source: str,
) -> None:
    client.table("vayoloop_demo_health_observations").insert({
        "workspace_id": DEMO_WORKSPACE_ID,
        "metric": metric,
        "value": value,
        "unit": unit,
        "observed_at": observed_at,
        "source": source,
        "context": {},
    }).execute()


def list_prescription_records(client: Any) -> list[dict[str, Any]]:
    result = (
        client.table("vayoloop_demo_prescriptions")
        .select(
            "id,title,clinician_name,prescribed_on,document_path,review_status,"
            "created_at,clinic_name,condition_as_written,notes,original_file_name,"
            "file_content_type,file_size_bytes"
        )
        .eq("workspace_id", DEMO_WORKSPACE_ID)
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
    """Allow only supported document signatures; do not trust the browser MIME label alone."""
    extension = "." + str(filename).rsplit(".", 1)[-1].lower() if "." in str(filename) else ""
    expected = _ALLOWED_MIME.get(extension)
    if expected is None:
        raise ValueError("Upload a PDF, JPG, PNG or WebP prescription.")
    if not payload or len(payload) > MAX_PRESCRIPTION_BYTES:
        raise ValueError("The file is empty or larger than 10 MB.")

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
    path = f"{DEMO_WORKSPACE_ID}/{uuid.uuid4().hex}_{safe_name}"

    client.storage.from_(BUCKET_NAME).upload(
        path,
        payload,
        {"content-type": mime_type, "upsert": "false"},
    )

    try:
        response = client.table("vayoloop_demo_prescriptions").insert({
            "workspace_id": DEMO_WORKSPACE_ID,
            "title": (title or safe_name).strip()[:180],
            "clinician_name": clinician_name.strip() or None,
            "prescribed_on": prescribed_on,
            "document_path": path,
            "review_status": "pending_review",
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
        loaded = list_prescription_records(client)
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
    if not path.startswith(f"{DEMO_WORKSPACE_ID}/"):
        raise ValueError("The requested file is outside the VayoLoop demo workspace.")
    result = client.storage.from_(BUCKET_NAME).download(path)
    if isinstance(result, bytes):
        return result
    if isinstance(result, bytearray):
        return bytes(result)
    raise RuntimeError("The stored document could not be downloaded.")


def delete_prescription_record(client: Any, record_id: str, path: str) -> None:
    client.table("vayoloop_demo_prescriptions").delete().eq(
        "id", record_id
    ).eq("workspace_id", DEMO_WORKSPACE_ID).execute()
    if path:
        if not path.startswith(f"{DEMO_WORKSPACE_ID}/"):
            raise ValueError("The requested file is outside the VayoLoop demo workspace.")
        client.storage.from_(BUCKET_NAME).remove([path])
