# VayoLoop
**Care beyond reminders.** An elder-led, voice-first care coordination experience.

## Public judging demo
The deployed site opens directly into **Asha Rao**, a fictional sample user. It does not ask judges to sign in and does not call Supabase from the public demo frontend.

Demo edits are stored in the current browser only. Use **Reset demo** to restore the original sample workspace.

## Current demo capabilities
- Medication schedule with self-reported dose events, due/missed state and a medication journey view
- Missed-dose alert tone after a 30-minute grace period, while the demo tab is open and voice/audio has been enabled
- Spoken welcome and plain-language summary of the recorded sample health patterns
- Spoken medication and upcoming-appointment reminders while the demo is open
- Optional one-shot voice commands for navigation and reading summaries, where browser speech recognition is supported
- Stop speech and silence an alarm without falsely marking a dose as taken
- Sample health journal and longitudinal trend direction
- Appointment calendar and completion workflow
- Simulated smartwatch and smart-home device events
- Simulated possible-fall safety flow, with no real contact or emergency call
- Care-circle role preview for Elder, Caregiver, Family and Viewer
- Guided five-step product walkthrough
- Larger-text accessibility control

## Voice companion setup
1. Open the public demo.
2. Tap **Enable voice companion** once to permit browser speech and unlock sound.
3. VayoLoop speaks a welcome and a sample care update.
4. Tap **Voice commands** and try phrases such as “read my health summary”, “open medications”, “read appointments” or “stop alarm”.
5. Use **Test missed-dose alarm** to hear the sample alert at any time.

The voice uses the speech voice supplied by the browser/device; its sound and language availability vary by device. The microphone is used only after the user taps Voice commands and depends on browser permission/support. On a later visit, the app attempts a spoken welcome if the voice preference was remembered, but browser autoplay policies may require tapping **Resume voice & sound**.

Voice checks run while the page is open. This prototype does not provide guaranteed background reminders after the tab is closed, when the device is asleep, or when browser audio is blocked.

## Demo data and safety
- Every profile, person, medication, appointment, sensor reading and care event in the public demo is fictional.
- The demo is not connected to a real smartwatch, appliance, health record, location service, email sender or emergency service.
- A dose report is self-reported and is not proof that a medicine was taken.
- A missed reminder is a workflow status, not evidence of harm or a clinical conclusion.
- Health summaries describe the recorded sample values; they do not diagnose, rate health, recommend treatment or infer medication causation.
- A simulated fall alert never contacts anyone and never places a call.
- Do not enter real patient or personal health information in this public demo.
- VayoLoop is not a medical device or emergency service.

## Engineering
- Static HTML, CSS and JavaScript
- Browser localStorage for demo-only persistence
- Web Speech API speech synthesis, optional browser speech recognition, and Web Audio API sample alarm
- GitHub Actions runs JavaScript syntax and smoke checks, then deploys the public static demo to GitHub Pages
- The Supabase schema and secured care-circle backend are separate development foundations; they are not connected to this public demo mode

## Repository and deployment
- Repository: https://github.com/manjunathjadav360-rgb/VayoLoop
- Demo: https://manjunathjadav360-rgb.github.io/VayoLoop/
- GitHub Actions workflow: `.github/workflows/quality-and-deploy.yml`

## Before real-world use
Replace local demo data with an authenticated backend connection, verify all role permissions with separate test accounts, add provider-specific and consent-based wearable/home adapters, implement secure reminder delivery and audit trails, complete accessibility and device testing, and obtain appropriate privacy, clinical-safety and legal reviews. Production voice reminders need dependable background delivery and monitored failure handling; a browser tab alone is not sufficient for critical medication care.
