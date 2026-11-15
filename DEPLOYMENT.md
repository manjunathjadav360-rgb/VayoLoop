# Deployment guide

## Streamlit Community Cloud — intended hackathon application

The India-first Python app starts at **`app.py`**.

1. Open [Streamlit Community Cloud](https://share.streamlit.io/).
2. Sign in using the GitHub account that can access this public repository.
3. Select **Create app**.
4. Choose repository `manjunathjadav360-rgb/VayoLoop`, branch `main`, and main file path `app.py`.
5. Deploy. Streamlit reads `requirements.txt` and installs the runtime dependency.
6. Open the generated Streamlit URL and test the full demo from a fresh session.

No secrets are needed for the synthetic demo. Do not add service-role keys, personal health data, or real emergency contacts to this public repository.

## Automated repository checks

The GitHub Actions workflow runs:
1. JavaScript syntax and static-preview smoke checks.
2. Python syntax compilation.
3. Unit tests for medicine status and emergency event transitions.
4. GitHub Pages deployment of the legacy static preview after the quality checks pass.

A successful GitHub Pages job does **not** mean the Streamlit app has been deployed. The Streamlit Community Cloud URL is only valid after the app has been created there and its deployment succeeds.

## Legacy static preview

https://manjunathjadav360-rgb.github.io/VayoLoop/

This is the older HTML/JavaScript preview, not the new Streamlit app.

## Current safety scope

- Use fictional records for all hackathon testing. After Secrets are configured, authenticated health observations and prescription records persist in Supabase; other demo workflows remain session-scoped.
- Emergency detections, family notifications, contact acknowledgements and device events are simulations only.
- No automated 112 call, dispatch, SMS, WhatsApp, email or push delivery is implemented.
- Browser voice alerts depend on browser permissions and the page being open.
- No real patient or emergency data should be entered.


## Configure private record persistence

The database project and schema are provisioned separately from the Streamlit app. To connect the deployed app:

1. Open the Streamlit Community Cloud dashboard and select the VayoLoop app.
2. Open **App settings → Secrets**.
3. Add the following TOML, replacing the placeholder with the VayoLoop project's **publishable** API key:

```toml
SUPABASE_URL = "https://vhugnytmbjktbhlspgyx.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
```

4. Save and reboot the app.
5. In the app sidebar, create an account or sign in. If email confirmation is enabled, confirm the email before signing in.
6. Add a fictional health observation and a fictional prescription file, refresh the page, sign in again if needed, and confirm both records remain.

The app uses the publishable key with user authentication. Never place a service-role or secret key in Streamlit secrets. Database tables have row-level security; prescription files are in a private Storage bucket with care-circle role policies.

Only the Health Journal and Prescription Library are persistent at this stage. Other sections remain synthetic demo workflows. Do not upload real patient records to this public hackathon prototype.

