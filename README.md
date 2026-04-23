# Local Event Discovery & Itinerary Planner

An AI-powered full-stack web application that transforms natural language descriptions into optimized, map-based itineraries — exported directly to Google Calendar.

Built with **FastAPI**, **React**, and the **Google Cloud Platform** API suite as a graduate course project.

---

## Features

- **Natural language input** — describe your interests, location, and availability in plain English
- **AI intent parsing** — Gemini 2.5 Flash extracts structured data (interests, location, date, time) from freeform text
- **Venue discovery** — Google Places API (New) fetches and ranks nearby venues by popularity and rating
- **Geographic clustering** — k-means clustering with greedy nearest-neighbor ordering groups stops into efficient routes
- **Real road routing** — Google Directions API renders actual road, transit, cycling, or walking paths on the map
- **Travel-aware scheduling** — Distance Matrix API calculates real travel times between stops; calendar events are spaced accordingly
- **Interactive itinerary editing** — swap stops for alternatives, remove stops, include/exclude with one click
- **Rich place details** — photo carousels, opening hours, ratings, website, phone pulled live from Places API
- **Google Calendar export** — OAuth 2.0 flow exports the finalized itinerary as time-blocked calendar events
- **Transportation mode selector** — walk, drive, transit, or cycle between stops

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| AI / NLP | Google Gemini 2.5 Flash (`google-genai`) |
| Places & Maps | Google Places API (New), Directions API, Distance Matrix API, Geocoding API |
| Calendar | Google Calendar API (OAuth 2.0) |
| Frontend | React, Vite, `@react-google-maps/api`, Axios |
| Deployment | Google Cloud Run |

---

## Project Structure

```
event-planner/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── .env                     # API keys (never committed)
│   ├── .env.example             # Template for required env vars
│   ├── client_secret.json       # OAuth credentials (never committed)
│   ├── requirements.txt
│   ├── routers/
│   │   ├── plan.py              # /api/plan, /api/recalculate, /api/export, /api/place
│   │   └── auth.py              # /auth/login, /auth/callback
│   └── services/
│       ├── gemini.py            # Natural language → structured JSON
│       ├── places.py            # Venue search, geocoding, place details, travel times
│       ├── clustering.py        # k-means clustering + nearest-neighbor ordering
│       └── calendar.py         # Google Calendar event creation
└── frontend/
    └── src/
        ├── App.jsx              # All React components and app logic
        └── index.css            # Global styles
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- A [Google Cloud project](https://console.cloud.google.com) with billing enabled
- A [Google AI Studio](https://aistudio.google.com) account for the Gemini API key

### Google Cloud APIs to Enable

In **APIs & Services → Library**, enable all of the following:

- Geocoding API
- Places API (New)
- Directions API
- Distance Matrix API
- Maps JavaScript API
- Google Calendar API

### 1. Clone the repository

```bash
git clone https://github.com/AryanDevikar/event-planner.git
cd event-planner
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy the environment template and fill in your keys:

```bash
cp .env.example .env
```

```bash
# backend/.env
GOOGLE_API_KEY=your_maps_places_directions_key
GEMINI_API_KEY=your_gemini_api_key
```

Place your OAuth credentials file at `backend/client_secret.json` (downloaded from Google Cloud Console → Credentials → OAuth 2.0 Client ID).

### 3. Frontend setup

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```bash
VITE_GOOGLE_MAPS_API_KEY=your_maps_javascript_api_key
VITE_API_BASE_URL=http://localhost:8000
```

### 4. Run locally

In two separate terminals:

```bash
# Terminal 1 — Backend
cd event-planner
set OAUTHLIB_INSECURE_TRANSPORT=1   # Windows
# export OAUTHLIB_INSECURE_TRANSPORT=1  # Mac/Linux
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd event-planner/frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

### 5. Connect Google Calendar (optional)

Visit `http://localhost:8000/auth/login` to authorize Calendar access before using the export feature.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/plan` | Parse message, fetch venues, build itinerary |
| `POST` | `/api/recalculate` | Recalculate route + travel times after stop changes |
| `GET` | `/api/place/{place_id}` | Fetch rich details + photos for a place |
| `POST` | `/api/export` | Export itinerary to Google Calendar |
| `GET` | `/auth/login` | Start Google OAuth flow |
| `GET` | `/auth/callback` | OAuth callback handler |
| `GET` | `/health` | Check API connectivity |

### Example request — `/api/plan`

```json
{
  "message": "I want to visit coffee shops and bookstores in New Brunswick this Saturday afternoon",
  "max_stops": 4,
  "radius_meters": 5000,
  "mode": "walking"
}
```

### Example response

```json
{
  "intent": {
    "interests": ["coffee shops", "bookstores"],
    "location": "New Brunswick, NJ",
    "date": "2026-04-12",
    "time_start": "13:00",
    "time_end": "17:00",
    "max_stops": 4
  },
  "itinerary": [...],
  "alternatives": {...},
  "travel_times": [...],
  "directions_path": [...],
  "total_venues_found": 9,
  "mode": "walking"
}
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | API key for Maps Platform (Geocoding, Places, Directions, Distance Matrix) |
| `GEMINI_API_KEY` | API key from Google AI Studio for Gemini 2.5 Flash |

### Frontend (`frontend/.env`)

| Variable | Description |
|---|---|
| `VITE_GOOGLE_MAPS_API_KEY` | Maps JavaScript API key for the frontend map |
| `VITE_API_BASE_URL` | Backend URL (default: `http://localhost:8000`) |

---

## Deployment

The backend is designed for **Google Cloud Run** — stateless, containerized, and scales to zero.

```bash
# Build and deploy
gcloud run deploy event-planner \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=...,GEMINI_API_KEY=...
```

Update `frontend/.env` with the Cloud Run URL before building the frontend for production:

```bash
VITE_API_BASE_URL=https://your-cloud-run-url.run.app
npm run build
```

---
