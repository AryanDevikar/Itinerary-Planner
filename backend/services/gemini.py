from google import genai
from dotenv import load_dotenv
import os, re, json
from pathlib import Path

# Explicitly point to backend/.env regardless of where uvicorn is run from
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

SYSTEM_PROMPT = """
You are an event planner assistant. Extract structured intent from the user's message.
Return ONLY valid JSON with these fields:
{
  "interests": ["list", "of", "activity", "types"],
  "location": "city or neighborhood string",
  "date": "YYYY-MM-DD or null",
  "time_start": "HH:MM or null",
  "time_end": "HH:MM or null",
  "max_stops": 4
}
"""

def parse_user_intent(user_message: str) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{SYSTEM_PROMPT}\n\nUser: {user_message}"
    )
    text = response.text.strip()
    text = re.sub(r"^```json|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)