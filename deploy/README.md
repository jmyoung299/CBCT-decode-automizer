# Deploy guide (click-deploy friendly)

This project can be deployed as:

- Backend API: Google Cloud Run (containerized FastAPI service)
- Frontend UI: Vercel or Firebase Hosting (static React app)

## 1) Deploy backend API to Cloud Run

Prerequisites:

- `gcloud` CLI authenticated
- A GCP project selected
- Billing enabled

From repository root:

```bash
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
gcloud builds submit --config cloudbuild.yaml .
```

This deploys service `cbct-decoder-api` to Cloud Run in region `us-central1`.

Environment variables supported by backend:

- `ALLOW_ORIGINS` (comma-separated origins for CORS)
  - Example:
    - `https://your-vercel-app.vercel.app,https://your-firebase.web.app`

After deploy, get URL:

```bash
gcloud run services describe cbct-decoder-api --region us-central1 --format='value(status.url)'
```

## 2) Deploy frontend to Vercel

The frontend app is in `frontend/`.

In Vercel project settings:

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable:
  - `VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL`

Optional project config is included at `frontend/vercel.json`.

## 3) Deploy frontend to Firebase Hosting

Inside `frontend/`:

```bash
npm install
VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL npm run build
firebase use YOUR_FIREBASE_PROJECT_ID
firebase deploy --only hosting
```

Update `.firebaserc` with your project ID before deploy.

## 4) Verify

- Backend health:
  - `https://YOUR_CLOUD_RUN_URL/health`
- Frontend:
  - open your Vercel/Firebase URL
  - upload `.dcm` or `.dcx` file
  - confirm parsed result appears
