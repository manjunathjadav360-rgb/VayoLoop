"""Shared synthetic demo persistence for VayoLoop.

There is intentionally no sign-in or account UI. The public hackathon demo uses
one shared workspace and therefore must contain fictional data only. Database
policies scope all access to one fixed demo workspace; no service-role key is
used or embedded in the application.
"""
from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime, timezone
from math import isfinite
from typing import Any

DEMO_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"
BUCKET_NAME = "vayoloop-prescriptions"
MAX_PRESCRIPTION_BYTES = 10 * 1024 * 1024
MAX_HEALTH_IMPORT_BYTES = 2 * 1024 * 1024
MAX_HEALTH_IMPORT_ROWS = 500
_DEMO_STORAGE_PATH_RE = re.compile(
    rf"^{re.escape(DEMO_WORKSPACE_ID)}/[0-9a-f]{{32}}_[A-Za-z0-9._-]{{1,120}}$"
)


def is_valid_demo_storage_path(path: str) -> bool:
    """Accept only object keys created for this fixed demo workspace."""
    return isinstance(path, str) and bool(_DEMO_STORAGE_PATH_RE.fullmatch(path))

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


def normalise_health_observation(
    metric: str,
    value: float,
    unit: str,
    observed_at: str,
    source: str,
) -> dict[str, Any]:
    """Validate and normalise one timestamped observation without clinical interpretation."""
    metric_value = str(metric or "").strip()
    unit_value = str(unit or "").strip()
    source_value = str(source or "Entered by user").strip() or "Entered by user"

    if not metric_value or len(metric_value) > 120:
        raise ValueError("Observation name must contain 1 to 120 characters.")
    if len(unit_value) > 32:
        raise ValueError("Unit must be 32 characters or fewer.")
    if len(source_value) > 100:
        raise ValueError("Source must be 100 characters or fewer.")

    try:
        numeric_value = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Observation value must be numeric.") from exc
    if not isfinite(numeric_value) or numeric_value < 0:
        raise ValueError("Observation value must be a finite, non-negative number.")

    try:
        timestamp = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Observation time must be a valid ISO timestamp.") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Observation time must include a timezone.")

    return {
        "metric": metric_value,
        "value": numeric_value,
        "unit": unit_value,
        "observed_at": timestamp.isoformat(timespec="seconds"),
        "source": source_value,
    }


def _health_observation_fingerprint(record: dict[str, Any]) -> tuple[str, float, str, str]:
    """Return a stable key so repeated imports do not duplicate the same reading."""
    normalised = normalise_health_observation(
        record.get("metric"),
        record.get("value"),
        record.get("unit", ""),
        record.get("observed_at"),
        record.get("source", "Not recorded"),
    )
    observed = datetime.fromisoformat(normalised["observed_at"]).astimezone(timezone.utc)
    return (
        normalised["metric"].casefold(),
        normalised["value"],
        normalised["unit"].casefold(),
        observed.isoformat(timespec="seconds"),
    )


def parse_health_observations_csv(
    payload: bytes,
    existing_records: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Parse a bounded wearable export with explicit fields and duplicate suppression.

    Required columns: metric,value,unit,observed_at. Optional column: source.
    Timestamps must be ISO-8601 values with a timezone. No clinical ranges are applied.
    """
    if not isinstance(payload, bytes) or not payload:
        raise ValueError("Choose a non-empty CSV file.")
    if len(payload) > MAX_HEALTH_IMPORT_BYTES:
        raise ValueError("The CSV file must be 2 MB or smaller.")

    try:
        decoded = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The CSV must use UTF-8 text encoding.") from exc

    try:
        reader = csv.DictReader(io.StringIO(decoded))
        headers = {
            str(header or "").strip().casefold(): header
            for header in (reader.fieldnames or [])
            if str(header or "").strip()
        }
        required = {"metric", "value", "unit", "observed_at"}
        missing = sorted(required - set(headers))
        if missing:
            raise ValueError("CSV is missing required column(s): " + ", ".join(missing))

        seen: set[tuple[str, float, str, str]] = set()
        for record in existing_records or []:
            try:
                seen.add(_health_observation_fingerprint(record))
            except (TypeError, ValueError, OverflowError):
                continue

        def field(row: dict[str | None, str | None], name: str, default: str = "") -> str:
            original_header = headers.get(name)
            value = row.get(original_header) if original_header else None
            return str(value if value is not None else default).strip()

        observations: list[dict[str, Any]] = []
        duplicates = 0
        row_count = 0
        for line_number, raw in enumerate(reader, start=2):
            if not raw or not any(str(value or "").strip() for value in raw.values()):
                continue
            row_count += 1
            if row_count > MAX_HEALTH_IMPORT_ROWS:
                raise ValueError(f"The CSV may contain no more than {MAX_HEALTH_IMPORT_ROWS} data rows.")

            try:
                observation = normalise_health_observation(
                    field(raw, "metric"),
                    field(raw, "value"),
                    field(raw, "unit"),
                    field(raw, "observed_at"),
                    field(raw, "source", "Imported wearable CSV") or "Imported wearable CSV",
                )
                fingerprint = _health_observation_fingerprint(observation)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"CSV row {line_number}: {exc}") from exc

            if fingerprint in seen:
                duplicates += 1
                continue
            seen.add(fingerprint)
            observations.append(observation)

    except csv.Error as exc:
        raise ValueError("The CSV file could not be read. Check its delimiter and quoting.") from exc

    if row_count == 0:
        raise ValueError("The CSV contains no observation rows.")
    return observations, duplicates


def save_health_observation(
    client: Any,
    metric: str,
    value: float,
    unit: str,
    observed_at: str,
    source: str,
) -> None:
    """Validate and save one non-negative, timestamped observation."""
    observation = normalise_health_observation(metric, value, unit, observed_at, source)
    client.table("vayoloop_demo_health_observations").insert({
        "workspace_id": DEMO_WORKSPACE_ID,
        **observation,
        "context": {},
    }).execute()


def save_health_observations(
    client: Any,
    observations: list[dict[str, Any]],
) -> None:
    """Validate every row before inserting a batch of observations in one database call."""
    if not observations:
        raise ValueError("There are no new observations to import.")
    if len(observations) > MAX_HEALTH_IMPORT_ROWS:
        raise ValueError(f"An import may contain no more than {MAX_HEALTH_IMPORT_ROWS} observations.")

    payloads = []
    for index, item in enumerate(observations, start=1):
        try:
            payload = normalise_health_observation(
                item.get("metric"),
                item.get("value"),
                item.get("unit"),
                item.get("observed_at"),
                item.get("source", "Imported wearable CSV"),
            )
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Observation {index}: {exc}") from exc
        payloads.append({
            "workspace_id": DEMO_WORKSPACE_ID,
            **payload,
            "context": {},
        })

    # Supabase/PostgREST inserts the validated batch as one transaction.
    client.table("vayoloop_demo_health_observations").insert(payloads).execute()


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
            "clinician_name": str(clinician_name or "").strip()[:120] or None,
            "prescribed_on": date.fromisoformat(prescribed_on).isoformat() if prescribed_on else None,
            "document_path": path,
            "review_status": "pending_review",
            "clinic_name": str(clinic_name or "").strip()[:160] or None,
            "condition_as_written": str(condition_as_written or "").strip()[:240] or None,
            "notes": str(notes or "").strip()[:2000] or None,
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
    if not is_valid_demo_storage_path(path):
        raise ValueError("The requested file path is not a valid VayoLoop demo object.")
    result = client.storage.from_(BUCKET_NAME).download(path)
    if isinstance(result, bytes):
        return result
    if isinstance(result, bytearray):
        return bytes(result)
    raise RuntimeError("The stored document could not be downloaded.")


def delete_prescription_record(client: Any, record_id: str, path: str) -> None:
    # Validate every destructive target before issuing either delete operation.
    if not record_id:
        raise ValueError("A prescription record ID is required.")
    if not is_valid_demo_storage_path(path):
        raise ValueError("The requested file path is not a valid VayoLoop demo object.")

    client.table("vayoloop_demo_prescriptions").delete().eq(
        "id", record_id
    ).eq("workspace_id", DEMO_WORKSPACE_ID).execute()
    client.storage.from_(BUCKET_NAME).remove([path])
