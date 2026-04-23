from pathlib import Path
from dotenv import load_dotenv
import os, requests
from typing import List

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GEOCODE_URL       = "https://maps.googleapis.com/maps/api/geocode/json"

def geocode_location(location: str):
    api_key = os.getenv("GOOGLE_API_KEY")
    resp = requests.get(GEOCODE_URL, params={"address": location, "key": api_key})
    data = resp.json()
    if not data.get("results"):
        print(f"[geocode] ERROR: No results for '{location}'")
        return None
    loc = data["results"][0]["geometry"]["location"]
    print(f"[geocode] '{location}' → {loc}")
    return (loc["lat"], loc["lng"])

def fetch_venues(interests: List[str], location: str, max_per_type: int = 5, radius_meters: int = 5000) -> List[dict]:
    api_key = os.getenv("GOOGLE_API_KEY")
    coords  = geocode_location(location)
    if not coords:
        return []

    venues   = []
    seen_ids = set()

    for interest in interests:
        try:
            resp = requests.post(
                PLACES_SEARCH_URL,
                headers={
                    "Content-Type":     "application/json",
                    "X-Goog-Api-Key":   api_key,
                    "X-Goog-FieldMask": (
                        "places.id,"
                        "places.displayName,"
                        "places.formattedAddress,"
                        "places.location,"
                        "places.rating,"
                        "places.userRatingCount,"
                        "places.types,"
                        "places.currentOpeningHours"
                    )
                },
                json={
                    "textQuery":    interest,
                    "locationBias": {
                        "circle": {
                            "center": {"latitude": coords[0], "longitude": coords[1]},
                            "radius": radius_meters
                        }
                    },
                    "rankPreference": "RELEVANCE",
                    "maxResultCount": max_per_type
                }
            )

            data = resp.json()
            print(f"[places] '{interest}' → status {resp.status_code}, {len(data.get('places', []))} results")

            if resp.status_code != 200:
                print(f"[places] ERROR body: {data}")
                continue

            for place in data.get("places", []):
                place_id = place.get("id")
                if not place_id or place_id in seen_ids:
                    continue
                seen_ids.add(place_id)

                venues.append({
                    "place_id":      place_id,
                    "name":          place.get("displayName", {}).get("text", "Unknown"),
                    "address":       place.get("formattedAddress", ""),
                    "lat":           place["location"]["latitude"],
                    "lng":           place["location"]["longitude"],
                    "rating":        place.get("rating", 0),
                    "total_ratings": place.get("userRatingCount", 0),
                    "types":         place.get("types", []),
                    "open_now":      place.get("currentOpeningHours", {}).get("openNow"),
                    "interest_tag":  interest
                })

        except Exception as e:
            print(f"[places] EXCEPTION for '{interest}': {e}")

    venues.sort(key=lambda v: (v["rating"] or 0, v["total_ratings"]), reverse=True)
    print(f"[places] Total unique venues: {len(venues)}")
    return venues

def get_travel_times(stops: list, mode: str = "walking") -> list:
    """
    Returns list of travel time dicts between sequential stops.
    mode: "walking", "driving", "transit", "bicycling"
    """
    if len(stops) < 2:
        return []

    api_key = os.getenv("GOOGLE_API_KEY")
    travel_times = []

    for i in range(len(stops) - 1):
        origin      = stops[i]
        destination = stops[i + 1]

        resp = requests.get(
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            params={
                "origins":      f"{origin['lat']},{origin['lng']}",
                "destinations": f"{destination['lat']},{destination['lng']}",
                "mode":         mode,
                "key":          api_key
            }
        )
        data = resp.json()

        try:
            element = data["rows"][0]["elements"][0]
            if element["status"] == "OK":
                travel_times.append({
                    "from":          origin["name"],
                    "to":            destination["name"],
                    "duration_sec":  element["duration"]["value"],
                    "duration_text": element["duration"]["text"],
                    "distance_text": element["distance"]["text"],
                    "mode":          mode
                })
            else:
                # Fallback if route not found
                travel_times.append({
                    "from":          origin["name"],
                    "to":            destination["name"],
                    "duration_sec":  0,
                    "duration_text": "Unknown",
                    "distance_text": "Unknown",
                    "mode":          mode
                })
        except Exception as e:
            print(f"[travel] ERROR between {origin['name']} and {destination['name']}: {e}")
            travel_times.append({
                "from": origin["name"], "to": destination["name"],
                "duration_sec": 0, "duration_text": "Unknown",
                "distance_text": "Unknown", "mode": mode
            })

    return travel_times

def get_place_details(place_id: str) -> dict:
    """
    Fetch rich place details including photos using Places API (New).
    Photos are returned as base64-ready URLs via the Places photo endpoint.
    """
    api_key = os.getenv("GOOGLE_API_KEY")

    resp = requests.get(
        f"https://places.googleapis.com/v1/places/{place_id}",
        headers={
            "X-Goog-Api-Key":   api_key,
            "X-Goog-FieldMask": (
                "id,displayName,formattedAddress,location,"
                "rating,userRatingCount,types,currentOpeningHours,"
                "regularOpeningHours,editorialSummary,photos,"
                "priceLevel,websiteUri,nationalPhoneNumber"
            )
        }
    )

    data = resp.json()

    if resp.status_code != 200:
        return {"error": data.get("error", {}).get("message", "Failed to fetch details")}

    # Build photo URLs — Places API (New) uses a media endpoint
    photos = []
    for photo in data.get("photos", [])[:6]:  # max 6 photos
        name = photo.get("name", "")
        if name:
            photo_url = (
                f"https://places.googleapis.com/v1/{name}/media"
                f"?maxHeightPx=400&maxWidthPx=600&key={api_key}"
            )
            photos.append(photo_url)

    # Parse opening hours
    hours = []
    oh = data.get("regularOpeningHours") or data.get("currentOpeningHours", {})
    if oh:
        hours = oh.get("weekdayDescriptions", [])

    return {
        "place_id":    data.get("id"),
        "name":        data.get("displayName", {}).get("text", ""),
        "address":     data.get("formattedAddress", ""),
        "rating":      data.get("rating"),
        "total_ratings": data.get("userRatingCount"),
        "types":       data.get("types", []),
        "summary":     data.get("editorialSummary", {}).get("text", ""),
        "price_level": data.get("priceLevel", ""),
        "website":     data.get("websiteUri", ""),
        "phone":       data.get("nationalPhoneNumber", ""),
        "hours":       hours,
        "photos":      photos,
        "open_now":    data.get("currentOpeningHours", {}).get("openNow")
    }