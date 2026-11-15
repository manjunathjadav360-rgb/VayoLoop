# VayoLoop
**Care beyond reminders.** An India-first, elder-led family care coordination prototype.

VayoLoop is designed around the way care often works in Indian households: an older adult remains at the centre, while adult children, relatives, caregivers and trusted nearby helpers coordinate routines and respond when support is needed.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit deployment

The Streamlit application entry point is **`app.py`**.

1. Push this repository to GitHub.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Create an app from `manjunathjadav360-rgb/VayoLoop`, branch `main`, file path `app.py`.
4. Deploy. Streamlit installs the dependencies from `requirements.txt`.

No secrets are required for the synthetic-data demo. Do not add real patient information or credentials to this public repository.

## What the demo includes

- **Elder-first home:** short greeting, daily overview, larger-text option and simple navigation.
- **Voice companion:** optional one-time browser audio enablement; attempts a spoken welcome and checks scheduled sample medicine and appointment reminders while the page remains open. Reminder phrases include English, Hindi, Kannada, Gujarati, Marathi, Tamil, Telugu and Bengali.
- **Medication journey:** sample medicine records, scheduled times, self-reported dose events, overdue-unconfirmed state, refill planning and a traceable activity log.
- **Prescription library:** upload PDF or image copies with date, clinic, prescriber and notes; re-download or remove the original during the current session. This prototype does not run OCR or medicine-disease checks.
- **Health record book:** timestamped readings with source labels, personal comparisons and complete CSV / JSON downloads of the current session's health observations.
- **Daily wellbeing check-in:** simple family check-in for meals, water, mood and optional notes; not a clinical assessment.
- **Health journal:** longitudinal user-entered or sample observations with personal comparisons; no diagnosis or universal health score.
- **Appointments:** create and complete appointment records.
- **Family circle:** sample family roles, trusted emergency contacts, shared household tasks and contact priority.
- **Emergency centre:** demonstrate possible-fall confirmation, manual SOS, simulated family escalation, contact acknowledgements and resolution history.
- **Connected living:** sample wearable and home-sensor register, last-sync visibility and simulated device events.
- **Local care directory:** add the family's own clinics, hospitals, pharmacies and home-care contacts. It starts empty rather than inventing local providers.
- **Care Passport:** assemble medication records, self-reported dose history, health observations, appointments, wellbeing check-ins, family tasks, trusted contacts and device status into a print-friendly handoff; export HTML or a structured JSON backup after an explicit sharing acknowledgement.
- **Guided demo:** a five-step path from medication routine through health journal, family coordination and safety simulation to the Care Passport.
- **India-aware emergency information:** 112 is presented as the national emergency number; the demo does not dial it or contact emergency services.

## Important limitations

This is a **synthetic-data hackathon prototype**, not a medical device, care provider or emergency service.

- No real patient data, login, live messaging, SMS, WhatsApp, email or push notifications are connected.
- Family/contact alerts, falls, home-sensor events and device syncs are simulations. The UI labels them as simulated; no person is actually notified.
- A possible fall requires verification. A manual SOS follows the immediate *simulated* family-alert path. The app does not automatically call 112 or dispatch responders.
- Browser speech and reminder tones depend on device/browser support, audio permission and the page staying open. They are not reliable background or life-safety alerts when the browser is closed or the phone is asleep.
- Voice phrases depend on speech voices installed on the device; language coverage varies.
- Streamlit session state is temporary demo storage. It is not a durable patient record or secure multi-user database.
- Care Passport downloads are generated from the current demo session only; they are not saved to a server or sent to a clinician or family member. The export should only be shared with the elder's permission.
- Prescription files, medicine records and health observations live in Streamlit session memory in this prototype. They can be downloaded during the session, but may be lost when the session ends or the app restarts. Do not use this demo to store real private medical records.
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
