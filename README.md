# VayoLoop
**Care beyond reminders.** An India-first, elder-led family care coordination prototype.

VayoLoop is designed around the way care often works in Indian households: an older adult remains at the centre, while adult children, relatives, caregivers and trusted nearby helpers coordinate routines and respond when support is needed.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Engineering notes

- [Architecture and data boundaries](ARCHITECTURE.md)
- [90–120 second judge walkthrough](JUDGE_WALKTHROUGH.md)
- Quality checks: `npm run check`, `ruff check .`, and `python -m unittest discover -s tests -v`.

## Architecture at a glance

The Streamlit app is the primary product. Responsibilities are deliberately separated:

| Component | Owns | Boundary |
|---|---|---|
| `app.py` | Pages, forms, user confirmation and session orchestration | Presentation only; no diagnosis or treatment decisions |
| `vayoloop_core.py` | Medication-state transitions and numerical health-trend summaries | Pure domain logic; no database or clinical interpretation |
| `vayoloop_db.py` | Supabase mapping, input validation, CSV parsing/batch writes and prescription-file operations | Persistence adapter; fixed shared demo workspace |
| `care_passport.py` | Read-only handoff snapshot, administrative completeness review and HTML export | Does not modify records or assess clinical correctness |
| `vayoloop_security.py` | Context-specific HTML and script-data encoding | Encodes untrusted values before output |
| `tests/` | Domain, database-adapter, security, import and page-render regression tests | Uses synthetic fixtures; no physical wearable or real patient data |

For the complete component diagram, data ownership, trust boundaries and failure handling, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Wearable / health-app CSV import

VayoLoop supports a **user-initiated CSV file import** in **Health Journal**. It is not a Bluetooth connection, live wearable sync or vendor API integration.

**Import sequence**

1. The user selects a CSV export.
2. The parser checks the file-size limit, UTF-8 encoding and required headers.
3. Each non-empty row is validated and normalised; timestamps must include a timezone.
4. Duplicate readings are identified within the uploaded file and against the health history loaded in the demo workspace.
5. The app displays an import preview and duplicate count.
6. Nothing is written until the user confirms.
7. The complete batch is validated again and, when cloud persistence is active, inserted with one Supabase bulk request.
8. The Health Journal reloads the saved readings and updates its numerical summaries.

**CSV format**

| Column | Required | Rule |
|---|---|---|
| `metric` | Yes | Non-empty observation label; maximum 120 characters |
| `value` | Yes | Finite, non-negative number; no clinical threshold is applied |
| `unit` | Yes | Unit label; maximum 32 characters |
| `observed_at` | Yes | ISO-8601 date/time with an explicit timezone offset |
| `source` | No | Defaults to `Imported wearable CSV`; maximum 100 characters |

- Maximum file size: **2 MB**.
- Maximum import size: **500 non-empty data rows**.
- UTF-8 and UTF-8-with-BOM are supported.
- Missing or duplicate headers, rows with extra fields, malformed rows, boolean/non-finite values and timezone-naive timestamps are rejected.
- Duplicate comparison uses metric and unit (case-insensitive), numeric value, and the observation instant normalised to UTC.
- In offline/test mode, validated readings are held in the current Streamlit session; with cloud persistence active, the batch is written to the shared demo table.
- CSV data is user-supplied. The import does not authenticate a device, verify a manufacturer's signature or prove that a reading came from a physical wearable.

**Try it:** use the [fictional sample wearable CSV](examples/vayoloop_wearable_demo.csv). The [judge walkthrough](JUDGE_WALKTHROUGH.md#demo-path) includes the live demonstration sequence.

### CSV import test coverage

The automated suite includes dedicated cases for required and optional columns, valid sample import, duplicates, missing headers, timezone-naive timestamps, invalid values, oversized files, row limits, full-batch validation and one-request batch insertion. Run the suite locally with:

```bash
VAYOLOOP_DISABLE_PERSISTENCE=1 python -m unittest discover -s tests -v
```


## Streamlit deployment

The Streamlit application entry point is **`app.py`**.

1. Push this repository to GitHub.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Create an app from `manjunathjadav360-rgb/VayoLoop`, branch `main`, file path `app.py`.
4. Deploy. Streamlit installs the dependencies from `requirements.txt`.

No secrets are required for the synthetic-data demo. Do not add real patient information or credentials to this public repository.


## Persistent health and prescription records (Supabase)

The VayoLoop Supabase project provides persistent storage for **health observations** and **prescription documents** in one shared public demo workspace. There is deliberately no account, sign-in or sign-up interface at this stage:

- Health readings are stored in `public.vayoloop_demo_health_observations`.
- Prescription details are stored in `public.vayoloop_demo_prescriptions`; original PDFs/images are stored in the private `vayoloop-prescriptions` Storage bucket.
- Anyone visiting the public demo shares the same synthetic workspace.
- Row-level security restricts the public API key to one fixed demo workspace. Prescription files stay in a non-public Storage bucket and are fetched through the app.
- The app uses a **publishable key only**. Never put a Supabase service-role key in this public repository.

### No account setup required

The public project URL and publishable key are configured in the app. Open the deployed app and test the Health Journal and Prescription Library directly — no sign-in or account creation is required.

**Important:** this is a shared public demo. Anyone using it can view or change its saved demo records. Use fictional test data only; never upload real patient information.

Only health observations and prescription records currently persist. Medicines, appointments, family tasks, connected devices, voice reminders and emergency workflows are still synthetic/session-only demo features.

**Privacy limit:** VayoLoop is a hackathon prototype, not a clinically validated or compliance-certified medical-record system. Use fictional data for judging and testing. Do not upload real patient records until professional security, privacy, consent, legal and operational reviews are completed.

## What the demo includes

- **Elder-first home:** short greeting, daily overview, larger-text option and simple navigation.
- **Voice companion:** optional one-time browser audio enablement; attempts a spoken welcome and checks scheduled sample medicine and appointment reminders while the page remains open. Reminder phrases include English, Hindi, Kannada, Gujarati, Marathi, Tamil, Telugu and Bengali.
- **Medication journey:** sample medicine records, scheduled times, self-reported dose events, overdue-unconfirmed state, refill planning, and optional links from medicine entries to the source prescription document. The link is for record traceability only, not clinical suitability checking.
- **Prescription library:** store PDF or image copies, metadata and the original file in the shared demo workspace; download or delete demo files. This prototype does not run OCR or medicine-disease checks.
- **Health record book:** timestamped readings with source labels, personal comparisons and CSV / JSON export. Readings persist in the shared demo workspace. The Health Journal also supports a user-confirmed import of up to 500 validated, timezone-aware readings from a wearable / health-app CSV export, with preview, duplicate detection and a single batch database request. This is file import, not live device integration. See [Wearable / health-app CSV import](#wearable--health-app-csv-import) and [the sample CSV](examples/vayoloop_wearable_demo.csv).
- **Daily wellbeing check-in:** simple family check-in for meals, water, mood and optional notes; not a clinical assessment.
- **Health journal:** timestamped observations, chronological charts, per-metric/unit trend summaries, latest-vs-previous comparisons, and rolling averages (latest three entries vs the preceding three when enough history exists). Trend direction describes recorded numbers only; it is not a diagnosis or a judgement that a value is medically good or bad.
- **Appointments:** create and complete appointment records.
- **Family circle:** sample family roles, trusted emergency contacts, shared household tasks and contact priority.
- **Emergency centre:** demonstrate possible-fall confirmation, manual SOS, simulated family escalation, contact acknowledgements and resolution history.
- **Connected living:** sample wearable and home-sensor register, last-sync visibility and simulated device events. A separate CSV import path in Health Journal accepts exported readings from compatible health apps; live device APIs are not connected.
- **Local care directory:** add the family's own clinics, hospitals, pharmacies and home-care contacts. It starts empty rather than inventing local providers.
- **Care Passport:** assemble medication records, self-reported dose history, health observations, appointments, wellbeing check-ins, family tasks, trusted contacts and device status into a print-friendly handoff; export HTML or a structured JSON backup after an explicit sharing acknowledgement.
- **Care handoff review:** run a pre-export administrative completeness check across medicines, prescription file references, health observations, appointments, trusted contacts and family tasks. It flags missing fields, broken document links, stale appointments, overdue tasks and inconsistent observation records without judging clinical accuracy or medicine suitability.
- **Guided demo:** a five-step path from medication routine through health journal, family coordination and safety simulation to the Care Passport.
- **India-aware emergency information:** 112 is presented as the national emergency number; the demo does not dial it or contact emergency services.

## Important limitations

This is a **synthetic-data hackathon prototype**, not a medical device, care provider or emergency service.

- The current public Streamlit demo has no sign-in or sign-up interface. It uses a Supabase publishable key with row-level security scoped to one fixed shared demo workspace. Only health observations and prescription records are persistently stored; live family messaging, SMS, WhatsApp and push notifications are not connected. All judging/test entries must be fictional.
- Family/contact alerts, falls, home-sensor events and device syncs are simulations. The UI labels them as simulated; no person is actually notified.
- A possible fall requires verification. A manual SOS follows the immediate *simulated* family-alert path. The app does not automatically call 112 or dispatch responders.
- Browser speech and reminder tones depend on device/browser support, audio permission and the page staying open. They are not reliable background or life-safety alerts when the browser is closed or the phone is asleep.
- Voice phrases depend on speech voices installed on the device; language coverage varies.
- Streamlit session state remains temporary for medicines, appointments, family tasks, connected devices, wellbeing check-ins and emergency simulations. The public demo tables and private Storage bucket have row-level security policies scoped to the fixed demo workspace, but those records are visible to anonymous demo visitors and are not private user records. This hackathon prototype is not a production clinical-record service.
- Care Passport downloads are generated from the current demo session only; they are not saved to a server or sent to a clinician or family member. The export should only be shared with the elder's permission.
- Health observations and prescription records persist in one shared public demo workspace. Anyone using the app may view or change them. Medicines and other care workflows remain session-only. Never upload real patient records to this public hackathon prototype.
- A dose report is self-reported and is not proof of ingestion. The app never changes a prescription, recommends a dose or decides treatment.
- Health trends describe entered sample values only. They do not diagnose or infer causes.
- Device compatibility depends on individual provider APIs and permissions; VayoLoop does not connect to every smartwatch or appliance.
- The current demo does not integrate with ABDM / ABHA.

## Before real-world use

A production deployment needs verified identity, durable encrypted storage, consent-based and server-enforced access control, audit trails, provider-specific device adapters, secure notification delivery with receipts and retries, background monitoring, independent emergency workflow validation, location permissions, accessibility testing, clinical-safety review, privacy/legal review and a tested incident-response process. Emergency-service integrations must be separately authorized and validated; a website button or browser notification is not an emergency response system.

## Repository and legacy preview

- Repository: https://github.com/manjunathjadav360-rgb/VayoLoop
- Streamlit entry point: `app.py`
- Legacy static preview: https://manjunathjadav360-rgb.github.io/VayoLoop/
- CI workflow: `.github/workflows/quality-and-deploy.yml`

GitHub Pages remains a legacy HTML preview. **Streamlit Community Cloud is the intended deployment for the new Python application.**
