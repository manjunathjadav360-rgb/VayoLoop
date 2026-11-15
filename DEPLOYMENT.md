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

- All records are fictional and session-scoped.
- Emergency detections, family notifications, contact acknowledgements and device events are simulations only.
- No automated 112 call, dispatch, SMS, WhatsApp, email or push delivery is implemented.
- Browser voice alerts depend on browser permissions and the page being open.
- No real patient or emergency data should be entered.
