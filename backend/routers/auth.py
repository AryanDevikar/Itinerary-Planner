from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from pathlib import Path

router = APIRouter()

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CLIENT_SECRET_PATH = Path(__file__).parent.parent / "client_secret.json"
REDIRECT_URI = "http://localhost:8000/auth/callback"

# Store the whole flow object so login and callback share the same session
_store = {}

@router.get("/auth/login")
def login():
    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_PATH),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    # Store the entire flow object — callback must use the same instance
    _store["flow"]  = flow
    _store["state"] = state
    return RedirectResponse(auth_url)

@router.get("/auth/callback")
def callback(code: str, state: str):
    if state != _store.get("state"):
        raise HTTPException(status_code=400, detail="Invalid OAuth state. Try /auth/login again.")

    # Reuse the same flow object from login — do NOT recreate it
    flow = _store.get("flow")
    if not flow:
        raise HTTPException(status_code=400, detail="No active login session. Visit /auth/login first.")

    flow.fetch_token(code=code)
    creds = flow.credentials

    _store["token"] = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret
    }

    # Clean up flow from store
    _store.pop("flow", None)
    _store.pop("state", None)

    return JSONResponse({
        "status": "authenticated",
        "message": "You can now export itineraries to Google Calendar."
    })

def get_stored_token() -> dict:
    token = _store.get("token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Visit /auth/login first."
        )
    return token