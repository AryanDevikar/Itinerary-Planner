from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from typing import List
import math

def get_calendar_service(token_dict: dict):
    creds = Credentials(
        token=token_dict["token"],
        refresh_token=token_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_dict["client_id"],
        client_secret=token_dict["client_secret"],
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    return build("calendar", "v3", credentials=creds)

def export_itinerary(
    service,
    itinerary: List[dict],
    date: str,
    time_start: str = "10:00",
    travel_times: List[dict] = None,
    visit_duration_min: int = 60
) -> List[str]:
    """
    Exports itinerary to Google Calendar with travel-aware spacing.
    Each stop gets visit_duration_min minutes, then travel time is
    added before the next stop starts.
    """
    event_links = []
    current_dt  = datetime.strptime(f"{date} {time_start}", "%Y-%m-%d %H:%M")
    travel_times = travel_times or []

    for i, stop in enumerate(itinerary):
        end_dt = current_dt + timedelta(minutes=visit_duration_min)

        # Build travel note for description
        travel_note = ""
        if i < len(travel_times):
            t = travel_times[i]
            travel_note = f"\n\nTravel to next stop: {t['duration_text']} ({t['distance_text']}) by {t['mode']}"

        event = {
            "summary":     stop["name"],
            "location":    stop["address"],
            "description": (
                f"Stop {i+1} of {len(itinerary)}\n"
                f"Rating: {stop.get('rating', 'N/A')}\n"
                f"Category: {stop.get('interest_tag', '')}"
                f"{travel_note}"
            ),
            "start": {"dateTime": current_dt.isoformat(), "timeZone": "America/New_York"},
            "end":   {"dateTime": end_dt.isoformat(),     "timeZone": "America/New_York"},
        }

        created = service.events().insert(calendarId="primary", body=event).execute()
        event_links.append(created.get("htmlLink", ""))

        # Advance time: visit duration + travel to next stop (rounded up to nearest minute)
        travel_sec = travel_times[i]["duration_sec"] if i < len(travel_times) else 0
        travel_min = math.ceil(travel_sec / 60)
        current_dt = end_dt + timedelta(minutes=travel_min)

    return event_links