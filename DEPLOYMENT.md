# Deployment status

GitHub Pages is configured to use **GitHub Actions**.

The workflow at `.github/workflows/quality-and-deploy.yml` runs on every push to `main`:
1. Runs JavaScript syntax checks and application smoke checks.
2. Uploads the static app.
3. Deploys it to GitHub Pages.

Expected public site URL:
https://manjunathjadav360-rgb.github.io/VayoLoop/

The site is considered deployed only after the GitHub Pages deployment job succeeds and the URL serves the application.

## Current scope
- This is a prototype and must use synthetic data for demonstrations.
- Supabase-backed login and care records need to be tested with separate accounts after deployment.
- Smartwatch, smart-home and email integrations remain future integrations, not live features.
