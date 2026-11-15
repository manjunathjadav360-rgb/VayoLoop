# VayoLoop — evaluation evidence

This page maps the prototype's implemented behavior to the evaluation areas. It is an evidence guide, not a claim of a particular score or clinical certification.

## Evaluation evidence

| Area | Implemented evidence | Where to verify |
|---|---|---|
| Code quality | Presentation, domain logic, persistence, output encoding and care handoff logic have separate responsibilities. Shared timestamp parsing keeps app and export behavior consistent. | `app.py`, `vayoloop_core.py`, `vayoloop_db.py`, `vayoloop_security.py`, `care_passport.py` |
| Security and data integrity | Health inputs are validated on write and read. Invalid stored readings remain visible with a review flag but are excluded from numerical trends. Prescription files have size, MIME/signature and generated-path checks. HTML and script-context output use dedicated encoders. | `vayoloop_db.py`, `vayoloop_security.py`, `care_passport.py`, `tests/test_vayoloop_db.py`, `tests/test_security_helpers.py`, `tests/test_care_passport.py` |
| Efficiency | Wearable CSV files are bounded to 2 MB and 500 non-empty rows. The importer validates the complete batch before one bulk insert, skips duplicate fingerprints, and does not make per-row database writes. | `vayoloop_db.py`, Health Journal import in `app.py`, `tests/test_vayoloop_db.py` |
| Testing | Automated checks cover UI wiring, Python lint and compilation, domain logic, persistence validation, CSV edge cases, file cleanup, output encoding and rendering of all ten Streamlit sections. | `.github/workflows/quality-and-deploy.yml`, `tests/`, `scripts/smoke-check.mjs` |
| Accessibility and usability | The interface provides a larger-text option, readable contrast tokens, labelled Streamlit controls, responsive sidebar behavior and concise elder-first navigation. The legacy preview separately tests keyboard tab navigation and reduced-motion preferences. | `app.py`, `.streamlit/config.toml`, `index.html`, `scripts/smoke-check.mjs`, `tests/test_streamlit_app.py` |
| Problem-statement alignment | The working journey covers medication routines and self-reports, prescription record storage, timestamped health history, wearable-export import, family coordination and a portable Care Passport with an administrative handoff review. | `JUDGE_WALKTHROUGH.md`, `app.py`, `care_passport.py` |

## Suggested judge demonstration

1. **Home:** introduce the elder-first workspace and short welcome.
2. **Medicines:** show a sample routine, its optional source-prescription link and a self-reported event. Explain that a self-report is not proof of ingestion.
3. **Health Journal:** import `examples/vayoloop_wearable_demo.csv`; show the preview, duplicate count, confirmation step and numerical history. Show that malformed or timezone-naive data is flagged rather than treated as a reliable measurement.
4. **Prescription Library:** upload a fictional sample PDF or image and show the stored metadata and file handling.
5. **Family Circle / Emergency Centre:** explain care-task coordination and demonstrate only the clearly labelled simulation.
6. **Care Passport:** review missing or inconsistent administrative fields, then export the print-ready handoff after acknowledging the sharing notice.

## Implemented versus simulated

**Implemented in the prototype:** persistent health observations and prescription metadata/files in the shared demo workspace; user-confirmed CSV import; numerical trend summaries; medication self-report tracking; appointments and family-task organization within a session; Care Passport generation and administrative completeness checks.

**Simulated or not connected:** Bluetooth or vendor-cloud wearable sync, smart-home controls, family alert delivery, SMS/WhatsApp/push messaging, emergency dispatch, live background reminders, OCR, prescription authenticity verification, medicine-condition matching, ABDM/ABHA exchange and clinical diagnosis or treatment recommendations.

## Security and privacy boundary

The public demo has no sign-in. Health observations and prescription files are stored in one shared fictional workspace, so visitors can view or change those demo records under the public demo policies. The Supabase publishable key is public by design; no service-role key is embedded. The prescription Storage bucket is non-public, but app-mediated access is still shared with demo visitors. **Use fictional data only. Never upload a real prescription, health record or emergency contact.**

The prototype is not a medical device, clinical record service, emergency service or compliance-certified product. A production system would require verified identity, elder consent, per-person server-enforced authorization, audited access, professionally reviewed clinical safety, validated notification delivery and independent security/privacy review.

## Reproducible quality checks

Run from the repository root:

```bash
npm run check
ruff check --output-format=github .
python -m compileall -q app.py vayoloop_core.py vayoloop_db.py vayoloop_security.py care_passport.py tests
VAYOLOOP_DISABLE_PERSISTENCE=1 python -m unittest discover -s tests -v
```

GitHub Actions runs these checks for pushes to `main` and pull requests targeting `main`. GitHub Pages publishes only the legacy static preview; that deployment does not verify Streamlit Community Cloud.
