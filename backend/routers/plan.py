from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.services.gemini import parse_user_intent
from backend.services.places import fetch_venues, get_travel_times, get_place_details
from backend.services.clustering import build_itinerary
from backend.services.calendar import get_calendar_service, export_itinerary
from backend.routers.auth import get_stored_token
import os, requests

router = APIRouter()

class PlanRequest(BaseModel):
    message: str
    max_stops: Optional[int] = 4
    radius_meters: Optional[int] = 5000
    mode: Optional[str] = "walking"

class ExportRequest(BaseModel):
    itinerary: List[dict]
    date: str
    time_start: str
    travel_times: Optional[List[dict]] = []
    visit_duration_min: Optional[int] = 60

class RecalcRequest(BaseModel):
    stops: List[dict]
    mode: Optional[str] = "walking"

@router.post("/api/plan")
def plan(req: PlanRequest):
    try:
        intent = parse_user_intent(req.message)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse intent: {e}")

    if not intent.get("location"):
        raise HTTPException(status_code=422, detail="Could not extract a location. Please mention a city or neighborhood.")
    if not intent.get("interests"):
        raise HTTPException(status_code=422, detail="Could not extract interests.")

    max_stops = intent.get("max_stops") or req.max_stops
    venues = fetch_venues(
        interests=intent["interests"],
        location=intent["location"],
        max_per_type=max_stops + 3,
        radius_meters=req.radius_meters
    )

    if not venues:
        raise HTTPException(status_code=404, detail=f"No venues found near {intent['location']}.")

    itinerary = build_itinerary(venues=venues, max_stops=max_stops, n_clusters=min(2, len(venues)))

    itinerary_ids = {s["place_id"] for s in itinerary}
    alternatives  = {}
    for stop in itinerary:
        tag  = stop.get("interest_tag")
        alts = [v for v in venues if v.get("interest_tag") == tag and v["place_id"] not in itinerary_ids and v["place_id"] != stop["place_id"]][:3]
        alternatives[stop["place_id"]] = alts

    travel_times    = get_travel_times(itinerary, mode=req.mode)
    directions_path = get_directions_path(itinerary, mode=req.mode)

    return {
        "intent":             intent,
        "itinerary":          itinerary,
        "alternatives":       alternatives,
        "travel_times":       travel_times,
        "directions_path":    directions_path,
        "total_venues_found": len(venues),
        "mode":               req.mode
    }

@router.post("/api/recalculate")
def recalculate(req: RecalcRequest):
    travel_times    = get_travel_times(req.stops, mode=req.mode)
    directions_path = get_directions_path(req.stops, mode=req.mode)
    return {"travel_times": travel_times, "directions_path": directions_path}

@router.get("/api/place/{place_id}")
def place_details(place_id: str):
    return get_place_details(place_id)

@router.post("/api/export")
def export(req: ExportRequest):
    token   = get_stored_token()
    service = get_calendar_service(token)
    links   = export_itinerary(
        service=service, itinerary=req.itinerary,
        date=req.date, time_start=req.time_start,
        travel_times=req.travel_times, visit_duration_min=req.visit_duration_min
    )
    return {"exported": len(links), "event_links": links}


def get_directions_path(stops: list, mode: str = "walking") -> list:
    if len(stops) < 2:
        return [{"lat": s["lat"], "lng": s["lng"]} for s in stops]

    api_key   = os.getenv("GOOGLE_API_KEY")
    origin    = f"{stops[0]['lat']},{stops[0]['lng']}"
    dest      = f"{stops[-1]['lat']},{stops[-1]['lng']}"
    waypoints = "|".join(f"{s['lat']},{s['lng']}" for s in stops[1:-1])

    dir_mode = {
        "walking": "walking", "driving": "driving",
        "transit": "transit", "bicycling": "bicycling"
    }.get(mode, "walking")

    params = {
        "origin":      origin,
        "destination": dest,
        "mode":        dir_mode,
        "key":         api_key
    }
    if waypoints:
        params["waypoints"] = waypoints

    resp = requests.get("https://maps.googleapis.com/maps/api/directions/json", params=params)
    data = resp.json()

    print(f"[directions] status={data.get('status')} mode={dir_mode} error={data.get('error_message','none')}")

    if data.get("status") != "OK":
        # Fallback to straight lines between stops
        return [{"lat": s["lat"], "lng": s["lng"]} for s in stops]

    path = []
    for leg in data["routes"][0]["legs"]:
        for step in leg["steps"]:
            path.extend(_decode_polyline(step["polyline"]["points"]))

    return path


def _decode_polyline(encoded: str) -> list:
    points, index, lat, lng = [], 0, 0, 0
    while index < len(encoded):
        for is_lng in [False, True]:
            result, shift = 0, 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift  += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if is_lng:
                lng += delta
            else:
                lat += delta
        points.append({"lat": lat / 1e5, "lng": lng / 1e5})
    return points