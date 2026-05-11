from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.services.gemini import parse_user_intent
from backend.services.places import fetch_venues, get_travel_times, get_place_details
from backend.services.clustering import build_itinerary
from backend.services.calendar import get_calendar_service, export_itinerary
from backend.routers.auth import get_stored_token
import os, requests
from collections import deque
from datetime import datetime

_query_history = deque(maxlen=5)
router = APIRouter()

class PlanRequest(BaseModel):
    message: str
    max_stops: Optional[int] = 4
    radius_meters: Optional[int] = 5000
    mode: Optional[str] = "walking"
    origin: Optional[str] = None 

class ExportRequest(BaseModel):
    itinerary: List[dict]
    date: str
    time_start: str
    travel_times: Optional[List[dict]] = []
    visit_duration_min: Optional[int] = 60

class RecalcRequest(BaseModel):
    stops: List[dict]
    mode: Optional[str] = "walking"
    origin: Optional[dict] = None

@router.post("/api/plan")
def plan(req: PlanRequest):
    try:
        intent = parse_user_intent(req.message)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse intent: {e}")

    if not intent.get("location"):
        raise HTTPException(status_code=422, detail="Could not extract a location.")
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

    # Resolve origin to lat/lng if provided
    origin_coords = None
    if req.origin and req.origin.strip():
        from backend.services.places import geocode_location
        coords = geocode_location(req.origin)
        if coords:
            origin_coords = {"lat": coords[0], "lng": coords[1], "name": req.origin}

    travel_times    = get_travel_times(itinerary, mode=req.mode, origin=origin_coords)
    directions_path = get_directions_path(itinerary, mode=req.mode, origin=origin_coords)

    # Record this search in history (fixes broken history after refactor)
    _query_history.append({
        "message":   req.message,
        "timestamp": datetime.utcnow().isoformat(),
        "location":  intent.get("location", ""),
        "stops": [
            {
                "name":         s.get("name", ""),
                "address":      s.get("address", ""),
                "place_id":     s.get("place_id", ""),
                "lat":          s.get("lat"),
                "lng":          s.get("lng"),
                "rating":       s.get("rating", 0),
                "interest_tag": s.get("interest_tag", ""),
            }
            for s in itinerary
        ],
    })

    return {
        "intent":             intent,
        "itinerary":          itinerary,
        "alternatives":       alternatives,
        "travel_times":       travel_times,
        "directions_path":    directions_path,
        "origin":             origin_coords,
        "total_venues_found": len(venues),
        "mode":               req.mode
    }

@router.post("/api/recalculate")
def recalculate(req: RecalcRequest):
    travel_times    = get_travel_times(req.stops, mode=req.mode, origin=req.origin)
    directions_path = get_directions_path(req.stops, mode=req.mode, origin=req.origin)
    return {"travel_times": travel_times, "directions_path": directions_path}

@router.get("/debug/history")
def query_history():
    return {"queries": list(_query_history)}

@router.get("/api/recent-places")
def recent_places():
    """Return the 5 most recently visited unique places across all searches."""
    seen_ids = set()
    places   = []
    # Walk history newest-first (deque is oldest-first, so reverse)
    for entry in reversed(list(_query_history)):
        for stop in entry.get("stops", []):
            pid = stop.get("place_id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                places.append({**stop, "searched_at": entry.get("timestamp", "")})
            if len(places) >= 5:
                break
        if len(places) >= 5:
            break
    return {"places": places}

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


def get_directions_path(stops: list, mode: str = "walking", origin: dict = None) -> list:
    if len(stops) < 1:
        return []

    api_key = os.getenv("GOOGLE_API_KEY")

    # Use origin if provided, otherwise start from first stop
    if origin:
        route_origin = f"{origin['lat']},{origin['lng']}"
    else:
        route_origin = f"{stops[0]['lat']},{stops[0]['lng']}"

    dest      = f"{stops[-1]['lat']},{stops[-1]['lng']}"

    # Waypoints = all stops except last (and exclude first if no custom origin)
    if origin:
        waypoint_stops = stops[:-1]
    else:
        waypoint_stops = stops[1:-1]

    waypoints = "|".join(f"{s['lat']},{s['lng']}" for s in waypoint_stops)

    dir_mode = {
        "walking": "walking", "driving": "driving",
        "transit": "transit", "bicycling": "bicycling"
    }.get(mode, "walking")

    params = {
        "origin":      route_origin,
        "destination": dest,
        "mode":        dir_mode,
        "key":         api_key
    }
    if waypoints:
        params["waypoints"] = waypoints

    resp = requests.get("https://maps.googleapis.com/maps/api/directions/json", params=params)
    data = resp.json()

    print(f"[directions] status={data.get('status')} mode={dir_mode} origin={'custom' if origin else 'first_stop'}")

    if data.get("status") != "OK":
        # Fallback to straight lines
        fallback = []
        if origin:
            fallback.append({"lat": origin["lat"], "lng": origin["lng"]})
        fallback.extend([{"lat": s["lat"], "lng": s["lng"]} for s in stops])
        return fallback

    path = []
    for leg in data["routes"][0]["legs"]:
        for step in leg["steps"]:
            path.extend(_decode_polyline(step["polyline"]["points"]))
    return path


def get_travel_times(stops: list, mode: str = "walking", origin: dict = None) -> list:
    if len(stops) < 1:
        return []

    api_key      = os.getenv("GOOGLE_API_KEY")
    travel_times = []

    # Build the full sequence: origin (if any) + all stops
    sequence = []
    if origin:
        sequence.append({"name": origin.get("name", "Starting point"), "lat": origin["lat"], "lng": origin["lng"]})
    sequence.extend(stops)

    for i in range(len(sequence) - 1):
        frm = sequence[i]
        to  = sequence[i + 1]

        resp = requests.get(
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            params={
                "origins":      f"{frm['lat']},{frm['lng']}",
                "destinations": f"{to['lat']},{to['lng']}",
                "mode":         mode,
                "key":          api_key
            }
        )
        data = resp.json()

        try:
            element = data["rows"][0]["elements"][0]
            if element["status"] == "OK":
                travel_times.append({
                    "from":          frm["name"],
                    "to":            to["name"],
                    "duration_sec":  element["duration"]["value"],
                    "duration_text": element["duration"]["text"],
                    "distance_text": element["distance"]["text"],
                    "mode":          mode
                })
            else:
                travel_times.append({"from": frm["name"], "to": to["name"], "duration_sec": 0, "duration_text": "Unknown", "distance_text": "Unknown", "mode": mode})
        except Exception as e:
            print(f"[travel] ERROR: {e}")
            travel_times.append({"from": frm["name"], "to": to["name"], "duration_sec": 0, "duration_text": "Unknown", "distance_text": "Unknown", "mode": mode})

    return travel_times


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