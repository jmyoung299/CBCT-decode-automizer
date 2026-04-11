# DICOM Decoder Frontend

Standalone frontend dashboard for uploading DICOM/DCX files to the Python API.

## Local development

```bash
npm install
cp .env.example .env.local
npm run dev
```

By default, the app expects the API at:

```text
http://127.0.0.1:8000
```

If your API runs elsewhere, set:

```bash
VITE_API_BASE_URL=https://your-api.example.com
```

## Build

```bash
npm run build
npm run preview
```

## Deploy to Vercel

1. Import the `frontend/` directory as a Vercel project.
2. Set build command to `npm run build`.
3. Set output directory to `dist`.
4. Add environment variable:
   - `VITE_API_BASE_URL=https://<your-python-api-host>`

## Deploy to Firebase Hosting

```bash
npm run build
firebase deploy --only hosting
```

Before deploying, edit `.firebaserc` and replace `your-firebase-project-id`.

Set the API URL before build:

```bash
VITE_API_BASE_URL=https://<your-python-api-host> npm run build
```
