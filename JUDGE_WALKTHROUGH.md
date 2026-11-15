# VayoLoop — judge walkthrough

**Suggested time: 90–120 seconds.** Use fictional sample data only.

## The story

VayoLoop is an elder-led care coordination workspace. It connects medication routines, dated health observations, prescription records and a portable care handoff in one place. It is designed to support family coordination without pretending to replace clinicians or emergency services.

## Demo path

1. **Home — start with the elder.** Show the short welcome, today's routine, care timeline and optional voice companion. Voice reminders are browser-based and work only while the page is open and audio is permitted.
2. **Medicines — show the traceable routine.** Add a sample medicine and link it to the source prescription document in the library. Record a self-reported event. Explain that the source link is administrative traceability only; a report is not proof that medicine was swallowed and does not change the prescription.
3. **Health Journal — show longitudinal context.** Add or inspect dated fictional readings. Open Health Trend Analysis to compare the latest reading with the previous one and, when enough history exists, compare two three-reading averages. The direction is numerical only, not a medical judgement.
4. **Prescription Library — show record keeping.** Upload a fictional PDF or image, save its metadata and original file, then prepare a download. This prototype stores the document; it does not perform OCR, verify authenticity or decide whether a medicine is suitable for a condition.
5. **Care Passport — show continuity.** Review the combined handoff and export the print-ready HTML or JSON backup after acknowledging the sharing-permission notice.
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
