# VayoLoop
**Care beyond reminders.** An elder-led, consent-first care coordination prototype.

## Current build
- Supabase email/password authentication
- Private elder care profile
- Medication records and user-reported dose events
- Appointment tracking
- Personal health journal
- Connected-device registry with explicit consent
- Row Level Security on database tables

## Stack
- Static HTML/CSS/JavaScript
- Supabase Auth + Postgres + Row Level Security
- No service-role key is used in the browser

## Run locally
Serve this folder with any static web server. The app imports Supabase JS from esm.sh, so an internet connection is required.

## Deploy
The repository is compatible with GitHub Pages:
1. Open repository Settings → Pages.
2. Choose Deploy from a branch.
3. Select `main` and `/ (root)`, then Save.
4. Wait for the Pages deployment to complete.

## Important safety and scope notes
- This prototype is not a medical device and does not diagnose, prescribe, or change treatment.
- Medication adherence is self-reported; a button press is not proof a dose was taken.
- Health entries are user-entered records; trends require sufficient real measurements and must not be treated as diagnosis.
- Device registration records consent and intended integration only. It does not yet connect to a smartwatch, home appliance, or emergency service.
- Never enter real patient information in a public demo. Use synthetic demo data clearly labeled as such.
- Emergency events are not monitored. This app is not an emergency service.

## Before real-world use
Complete an independent security review, verify every RLS policy and invitation workflow, add secure notification delivery and provider-specific device adapters, implement audit logging and account recovery, and obtain appropriate privacy/legal review. Do not store service-role credentials in frontend code.
