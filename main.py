from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
from backend.routers import plan, auth
import os, traceback
from google import genai

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

app = FastAPI()  # ← must come first

app.add_middleware(  # ← then middleware
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plan.router)  # ← then routers
app.include_router(auth.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "traceback": traceback.format_exc()}
    )

@app.get("/health")
def health():
    import requests
    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": "New York, NY", "key": os.getenv("GOOGLE_API_KEY")}
        )
        maps_ok = resp.json().get("status") == "OK"
    except Exception as e:
        maps_ok = str(e)

    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        client.models.generate_content(model="gemini-2.5-flash", contents="say ok")
        gemini_ok = True
    except Exception as e:
        gemini_ok = str(e)

    return {"maps": maps_ok, "gemini": gemini_ok}

@app.get("/test-gemini")
def test_gemini():
    from backend.services.gemini import parse_user_intent
    return parse_user_intent("I want to visit coffee shops and bookstores in New Brunswick this Saturday afternoon")

@app.get("/test-places")
def test_places():
    from backend.services.places import fetch_venues
    results = fetch_venues(interests=["coffee shop", "bookstore"], location="New Brunswick, NJ")
    return {"count": len(results), "venues": results[:5]}

@app.get("/test-clustering")
def test_clustering():
    from backend.services.places import fetch_venues
    from backend.services.clustering import build_itinerary
    venues = fetch_venues(interests=["coffee shop", "bookstore"], location="New Brunswick, NJ")
    itinerary = build_itinerary(venues, max_stops=4, n_clusters=2)
    return {"count": len(itinerary), "itinerary": itinerary}

@app.get("/debug/geocode")
def debug_geocode(location: str = "Brooklyn, NY"):
    from backend.services.places import geocode_location
    return {"result": geocode_location(location)}

@app.get("/debug/directions")
def debug_directions():
    from backend.routers.plan import get_directions_path
    test_stops = [
        {"name": "Stop 1", "lat": 40.4946938, "lng": -74.4481888},
        {"name": "Stop 2", "lat": 40.4950347, "lng": -74.4454951},
    ]
    result = get_directions_path(test_stops, mode="walking")
    return {"path_points": len(result), "first_5": result[:5]}