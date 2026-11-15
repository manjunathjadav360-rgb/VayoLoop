# VayoLoop — judge walkthrough

**Suggested time: 90–120 seconds.** Use fictional sample data only.

## The story

VayoLoop is an elder-led care coordination workspace. It connects medication routines, dated health observations, prescription records and a portable care handoff in one place. It is designed to support family coordination without pretending to replace clinicians or emergency services.

## Demo path

1. **Home — start with the elder.** Show the short welcome, today's routine, care timeline and optional voice companion. Voice reminders are browser-based and work only while the page is open and audio is permitted.
2. **Medicines — show the traceable routine.** Add a sample medicine and link it to the source prescription document in the library. Record a self-reported event. Explain that the source link is administrative traceability only; a report is not proof that medicine was swallowed and does not change the prescription.
3. **Health Journal — show longitudinal context.** Import the sample wearable CSV or add fictional readings manually. The app validates timestamps and values, previews the batch, skips duplicate readings and saves new records together. Open Health Trend Analysis to compare the latest reading with the previous one and, when enough history exists, compare two three-reading averages. CSV import is not a live device connection and trends are numerical only, not a medical judgement.
4. **Prescription Library — show record keeping.** Upload a fictional PDF or image, save its metadata and original file, then prepare a download. This prototype stores the document; it does not perform OCR, verify authenticity or decide whether a medicine is suitable for a condition.
5. **Care Passport — show continuity and record quality.** Review the pre-export handoff checklist for missing fields, broken source-document links, stale scheduled visits and overdue uncompleted tasks, then export the print-ready HTML or JSON backup after acknowledging the sharing-permission notice. The checklist does not assess medical suitability or clinical accuracy.
6. **Emergency Centre / Connected Living — show boundaries.** The interaction is a simulation only. No fall is detected, no person is notified, no device is contacted and no emergency call is placed.

## Implemented versus simulated

| Capability | Current prototype |
|---|---|
| Prescription file and metadata storage | Implemented for the shared fictional demo workspace |
| Medicine-to-prescription source reference | Implemented in the current session and Care Passport export; not a clinical match |
| Health observation history and numerical trend analysis | Implemented for the shared fictional demo workspace |
| Medicine routine and self-reported dose tracking | Implemented as session-scoped demo data |
| Appointment, family-task and wellbeing organisation | Implemented as session-scoped demo data |
| Wearable and smart-home connections | Simulated only |
| Family messaging and emergency escalation delivery | Simulated only |
| OCR, prescription authenticity and medicine-condition suitability checking | Not implemented |

## Important demo rule

The public app shares its persisted demo workspace with every visitor. Do not upload real prescriptions, enter real health details or add real emergency contacts. This is a hackathon prototype, not a clinical record service or emergency-response service.
