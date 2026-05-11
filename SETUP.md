# RouteIQ — Setup & Run Instructions

This document provides complete, step-by-step instructions to launch and test RouteIQ end-to-end on a fresh machine. No additional development work is required beyond what is described below.

---

## Prerequisites

Before you begin, ensure the following are installed and available on your system:

| Requirement | Minimum Version | Check with |
|---|---|---|
| Python | 3.12 | `python --version` |
| Node.js | 18 | `node --version` |
| npm | 9 | `npm --version` |
| git | any | `git --version` |

You also need:

- A **Google Cloud project** with billing enabled ([console.cloud.google.com](https://console.cloud.google.com))
- A **Google AI Studio** account for the Gemini API key ([aistudio.google.com](https://aistudio.google.com))

---

## Step 1 — Enable Google Cloud APIs

In your Google Cloud project, go to **APIs & Services → Library** and enable **all** of the following:

| API | Purpose |
|---|---|
| Geocoding API | Convert addresses to lat/lng |
| Places API (New) | Venue search and place details |
| Directions API | Real road polyline rendering |
| Distance Matrix API | Travel time and distance between stops |
| Maps JavaScript API | Interactive map in the browser |
| Google Calendar API | Export itinerary to Google Calendar |

> **Important:** The system uses the **new** Places API. Do not enable the legacy "Places API" — it will cause `REQUEST_DENIED` errors for new project keys.

---

## Step 2 — Get API Keys

### Maps Platform API Key

1. Go to **APIs & Services → Credentials** in your Cloud Console.
2. Click **Create Credentials → API Key**.
3. Restrict the key to the APIs listed in Step 1 (recommended).
4. Copy the key — this is your `GOOGLE_API_KEY`.

### Gemini API Key

1. Visit [aistudio.google.com](https://aistudio.google.com) and sign in.
2. Click **Get API Key → Create API key**.
3. Copy the key — this is your `GEMINI_API_KEY`.

### OAuth 2.0 Client (for Calendar export)

1. In **APIs & Services → Credentials**, click **Create Credentials → OAuth 2.0 Client ID**.
2. Set **Application type** to **Web application**.
3. Add `http://localhost:8000/auth/callback` to **Authorised redirect URIs**.
4. Download the JSON file and save it as `backend/client_secret.json` in the project directory.

---

## Step 3 — Clone the Repository

```bash
git clone https://github.com/AryanDevikar/Itinerary-Planner.git
cd Itinerary-Planner
```

---

## Step 4 — Backend Setup

### 4a. Create a virtual environment and install dependencies

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
- **Windows (CMD):** `venv\Scripts\activate.bat`
- **Mac/Linux:** `source venv/bin/activate`

Install dependencies:

```bash
pip install -r requirements.txt
```

### 4b. Configure environment variables

Create the file `backend/.env` with the following content (replace the placeholder values with your actual keys):

```env
GOOGLE_API_KEY=your_maps_places_directions_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4c. Place the OAuth credentials file

Copy the `client_secret.json` you downloaded in Step 2 into the `backend/` directory:

```
backend/
├── client_secret.json   ← place it here
├── .env
├── main.py
└── ...
```

---

## Step 5 — Frontend Setup

Open a **new terminal** (keep the backend one open) and navigate to the frontend directory:

```bash
cd frontend
npm install
```

Create the file `frontend/.env` with the following content:

```env
VITE_GOOGLE_MAPS_API_KEY=your_maps_javascript_api_key_here
VITE_API_BASE_URL=http://localhost:8000
```

> The Maps JavaScript API key can be the same key as `GOOGLE_API_KEY`, or a separate browser-restricted key.

---

## Step 6 — Run the Application

You need **two terminals open at the same time** — one for the backend, one for the frontend.

### Terminal 1 — Start the backend

Navigate to the **project root** (the `Itinerary-Planner/` folder, not `backend/`):

```bash
# Windows (PowerShell)
$env:OAUTHLIB_INSECURE_TRANSPORT = "1"
uvicorn backend.main:app --reload --port 8000

# Mac/Linux
export OAUTHLIB_INSECURE_TRANSPORT=1
uvicorn backend.main:app --reload --port 8000
```

> `OAUTHLIB_INSECURE_TRANSPORT=1` allows OAuth callbacks over plain HTTP on localhost. Do **not** use this flag in production.

You should see output similar to:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

### Terminal 2 — Start the frontend

```bash
cd frontend
npm run dev
```

You should see:

```
  VITE v5.x.x  ready in 300ms

  ➜  Local:   http://localhost:5173/
```

---

## Step 7 — Open the Application

Open your browser and go to:

```
http://localhost:5173
```

You should see the RouteIQ input screen with the "Where do you want to go today?" prompt.

---

## Step 8 — Connect Google Calendar (optional)

To enable the **Export to Google Calendar** feature, you must complete the OAuth flow once:

1. In your browser, navigate to:
   ```
   http://localhost:8000/auth/login
   ```
2. Sign in with your Google account and grant the requested Calendar permissions.
3. You will be redirected back to the backend — you should see `{"status":"authenticated"}`.
4. Return to the app (`http://localhost:5173`) and use the export button normally.

> You only need to do this once per server session. OAuth tokens reset when the backend restarts.

---

## Step 9 — Test the Application End-to-End

Use the following sample queries to verify the system is working correctly:

| Test scenario | Sample query | What to verify |
|---|---|---|
| Basic search | "Coffee shops in New Brunswick, NJ" | Stops appear on map with travel times |
| Multi-interest | "Coffee shops and bookstores in Manhattan" | Both interest types appear in results |
| With origin | Query above + starting address "Penn Station, New York" | Gold pin appears at origin; route starts there |
| Transport mode | Select "Drive" or "Transit" before submitting | Road polyline matches selected mode |
| Stop editing | Click numbered badge on a stop | Stop fades in/out; route recalculates |
| Swap stop | Click "Details", then "Swap in" on an alternative | Stop replaced; route updates |
| Place details | Click "Details" on any stop | Side panel shows photos, hours, website |
| Calendar export | Click "Export to Google Calendar" | Select date/time, confirm; check Google Calendar |
| Recent history | Run two searches, return to home | Previous query appears as clickable button |
| Recently visited | Run two searches, return to home | Recently seen venues listed below history |

---

## Project Structure Reference

```
Itinerary-Planner/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── .env                     # API keys (you create this)
│   ├── client_secret.json       # OAuth credentials (you download this)
│   ├── requirements.txt
│   ├── routers/
│   │   ├── plan.py              # /api/plan, /api/recalculate, /api/export,
│   │   │                        # /api/place, /api/recent-places, /debug/history
│   │   └── auth.py              # /auth/login, /auth/callback
│   └── services/
│       ├── gemini.py            # Natural language → structured JSON via Gemini
│       ├── places.py            # Venue search, geocoding, place details
│       ├── clustering.py        # k-means clustering + nearest-neighbor ordering
│       └── calendar.py          # Google Calendar event creation
├── frontend/
│   ├── .env                     # Frontend env vars (you create this)
│   └── src/
│       ├── App.jsx              # All React components and app logic
│       └── index.css            # Global styles
├── Dockerfile                   # For Cloud Run deployment
└── SETUP.md                     # This file
```

---

## Environment Variables Summary

### `backend/.env`

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | API key for Maps Platform (Geocoding, Places New, Directions, Distance Matrix) |
| `GEMINI_API_KEY` | API key from Google AI Studio for Gemini 2.5 Flash |

### `frontend/.env`

| Variable | Description |
|---|---|
| `VITE_GOOGLE_MAPS_API_KEY` | Maps JavaScript API key for the in-browser map |
| `VITE_API_BASE_URL` | Backend base URL — use `http://localhost:8000` for local development |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `REQUEST_DENIED` from Places API | Legacy Places API used, or key not enabled for Places (New) | Enable "Places API (New)" in Cloud Console; do not use legacy Places API |
| `Could not parse intent` (422) | Gemini API key missing or invalid | Check `GEMINI_API_KEY` in `backend/.env` |
| `No venues found` (404) | Location not recognised, or Places API not returning results | Try a more specific location; check API key restrictions |
| `ZERO_RESULTS` on Directions | Transit mode with no route between stops | Switch to Walking or Driving mode; the system falls back to straight lines |
| Calendar export fails | Not authenticated, or OAuth scope denied | Visit `http://localhost:8000/auth/login` and complete the OAuth flow |
| `Missing code verifier` (OAuth error) | OAuth `Flow` object not shared between login and callback | Restart the backend; this is a known issue fixed in the current implementation |
| `OAUTHLIB_INSECURE_TRANSPORT` error | Environment variable not set before starting uvicorn | Set `$env:OAUTHLIB_INSECURE_TRANSPORT = "1"` (PowerShell) before running uvicorn |
| Frontend shows blank map | Maps JavaScript API key missing or not enabled | Check `VITE_GOOGLE_MAPS_API_KEY` in `frontend/.env`; enable Maps JavaScript API |
| `ModuleNotFoundError: backend` | Uvicorn run from wrong directory | Run uvicorn from the project root (`Itinerary-Planner/`), not from `backend/` |

---

## Optional: Docker Deployment

A `Dockerfile` is included for containerised deployment. To build and run locally with Docker:

```bash
docker build -t routeiq .
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your_key \
  -e GEMINI_API_KEY=your_key \
  routeiq
```

To deploy to Google Cloud Run:

```bash
gcloud run deploy routeiq \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=...,GEMINI_API_KEY=...
```

Update `VITE_API_BASE_URL` in `frontend/.env` to the Cloud Run URL, then rebuild the frontend:

```bash
npm run build
```
