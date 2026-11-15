# VayoLoop
**Care beyond reminders.** An elder-led, consent-first care coordination prototype.

## Current working prototype
- Supabase email/password authentication
- Private elder care profile
- Medication records and user-reported dose events
- Appointment tracking
- Personal health journal
- Care-circle invitations with 256-bit random one-time codes
- SHA-256 invitation hashes stored in the database; codes expire after 1–7 days
- Invitations accepted only by a signed-in account with the matching verified email
- Elder, caregiver, family, and viewer roles
- Revoke pending invitations and remove member access
- Connected-device registry with explicit consent
- Row Level Security and least-privilege table grants

## Stack
- Static HTML/CSS/JavaScript
- Supabase Auth + Postgres + Row Level Security
- Supabase publishable key in the browser; no service-role or secret key in frontend code
- GitHub Actions for syntax/smoke checks and static deployment

## Deploy
1. Open repository **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.
3. The workflow validates the app and deploys the repository on pushes to `main`.
4. Open the deployment URL shown in the **github-pages** environment.

## Run locally
Serve this folder with a static web server. The app imports Supabase JS from esm.sh, so an internet connection is required.

## Care-circle permissions
- **Owner:** creates and administers the care profile; cannot remove their own owner access.
- **Elder:** primary elder account, with the ability to invite and manage the care circle.
- **Caregiver:** can help manage medication records, appointments, health entries, and supported device records.
- **Family:** read-only access to core care records.
- **Viewer:** limited read access.

Invitation codes are displayed once and must be shared privately with the named recipient. Email delivery of invitations is not yet configured.

## Safety and scope
- This prototype is not a medical device and does not diagnose, prescribe, or change treatment.
- Medication adherence is self-reported; a button press is not proof a dose was taken.
- Health entries are user-entered records. Trends require sufficient genuine measurements and are not clinical conclusions.
- Device registration records consent and intended integration only. It does not yet connect to a smartwatch, home appliance, or emergency service.
- No live fall detection, location tracking, ambulance dispatch, or email reminder delivery is implemented.
- Never enter real patient information in a public demo. Use synthetic demo data clearly labelled as such.
- This app is not an emergency service.

## Database migrations
The live Supabase project currently has the initial care schema, owner-trigger hardening, and connected-living foundation applied. The care-circle access-control migration is included under `supabase/migrations`. Earlier bootstrap migrations still need to be backfilled into this repository before one-command database recreation is possible.

## Before real-world use
Complete an independent security review, verify invitation and RLS behavior with separate test accounts, add secure notification delivery and provider-specific device adapters, implement audit logging and account recovery, and obtain appropriate privacy/legal review. Keep all Supabase secret keys out of frontend code.
