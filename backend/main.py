import sys
import os
import tempfile
import math
from contextlib import asynccontextmanager

# Ensure project root is on the path so agent/ and tools/ are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json as _json

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional

from agent.llm import call_llm, call_llm_events
from agent.client import update_llm_key, get_key_info, _ORIGINAL_KEY
from tools.voice import transcribe_audio, text_to_speech
from tools.translator import detect_and_translate
from tools.location_finder import (
    find_location,
    get_district_for_location,
    KERALA_COASTAL_LOCATIONS,
    LOCATION_TO_DISTRICT,
)
from database.profiles import (
    create_profile,
    get_profile,
    update_location,
    update_last_seen,
    get_all_profiles,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Fisher Adviser API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TTS_OUTPUT_PATH = os.path.join(
    "/tmp" if os.path.exists("/tmp") else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    ),
    "tts_output.wav",
)


class ChatRequest(BaseModel):
    message: str
    district: str
    language: Optional[str] = "ml"   # "ml", "en", "hi", "ta", "te"
    phone: Optional[str] = None       # if provided, load profile location
    history: Optional[list[dict]] = None


class SynthesizeRequest(BaseModel):
    text: str


class TranslateRequest(BaseModel):
    text: str
    target: str   # "en" or "ml"


class DetectLocationRequest(BaseModel):
    lat: float
    lng: float


class SearchLocationRequest(BaseModel):
    query: str


class UpdateLocationRequest(BaseModel):
    phone: str
    coastal_location: str


class CreateProfileRequest(BaseModel):
    name: str
    phone: str
    coastal_location: Optional[str] = None
    district: Optional[str] = None
    preferred_species: Optional[str] = None
    fishing_zone: Optional[str] = None
    boat_type: Optional[str] = None
    registration_number: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "agent": "Fisher Adviser"}


@app.post("/chat")
def chat(req: ChatRequest):
    lang = req.language or "ml"

    # Resolve profile location if phone provided
    coastal_location = None
    profile_district = None
    if req.phone:
        profile = get_profile(req.phone)
        if profile:
            coastal_location = profile.get("coastal_location")
            profile_district = profile.get("district")
            update_last_seen(req.phone)

    # Use profile district as fallback if no district sent
    effective_district = req.district or profile_district or ""

    active_district = effective_district or None

    try:
        if lang == "en":
            english_message = detect_and_translate(req.message, "en")
            prompt = f"[District: {effective_district}] {english_message}"
            response_text = call_llm(
                prompt, language="en",
                coastal_location=coastal_location,
                district=active_district,
                history=req.history,
            )
        else:
            prompt = f"[District: {effective_district}] {req.message}"
            response_text = call_llm(
                prompt, language="ml",
                coastal_location=coastal_location,
                district=active_district,
                history=req.history,
            )
    except Exception as e:
        err = str(e)
        print(f"[ChatError] {type(e).__name__}: {err}")
        if any(k in err.lower() for k in ("429", "rate_limit", "quota", "resource_exhausted")):
            response_text = "⚠️ സേവനം തിരക്കിലാണ്. ഒരു മിനിറ്റ് കഴിഞ്ഞ് വീണ്ടും ശ്രമിക്കൂ." if lang == "ml" else "⚠️ Too many requests right now — please wait a moment and try again."
        else:
            response_text = "⚠️ എന്തോ കുഴപ്പം സംഭവിച്ചു. വീണ്ടും ശ്രമിക്കുക." if lang == "ml" else "⚠️ Something went wrong. Please try again."

    return {"response": response_text, "tools_called": [], "language": lang}


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    lang = req.language or "ml"

    coastal_location = None
    profile_district = None
    if req.phone:
        profile = get_profile(req.phone)
        if profile:
            coastal_location = profile.get("coastal_location")
            profile_district = profile.get("district")
            update_last_seen(req.phone)

    effective_district = req.district or profile_district or ""
    active_district = effective_district or None

    if lang == "en":
        english_message = detect_and_translate(req.message, "en")
        prompt = f"[District: {effective_district}] {english_message}"
    else:
        prompt = f"[District: {effective_district}] {req.message}"

    def generate():
        # Send a keepalive comment immediately so the browser doesn't drop the connection
        yield ": keepalive\n\n"
        try:
            for event in call_llm_events(
                prompt, language=lang,
                coastal_location=coastal_location,
                district=active_district,
                history=req.history,
            ):
                if event["type"] == "tool_call":
                    yield f"event: tool_call\ndata: {_json.dumps({'tool': event['tool']})}\n\n"
                elif event["type"] == "price_data":
                    yield f"event: price_data\ndata: {_json.dumps(event['data'])}\n\n"
                elif event["type"] == "message":
                    yield f"event: message\ndata: {_json.dumps({'response': event['response']})}\n\n"
        except Exception as e:
            err = str(e)
            print(f"[ChatError] {type(e).__name__}: {err}")
            if any(k in err.lower() for k in ("429", "rate_limit", "quota", "resource_exhausted")):
                msg = "⚠️ സേവനം തിരക്കിലാണ്. ഒരു മിനിറ്റ് കഴിഞ്ഞ് വീണ്ടും ശ്രമിക്കൂ." if lang == "ml" else "⚠️ Too many requests right now — please wait a moment and try again."
            else:
                msg = "⚠️ എന്തോ കുഴപ്പം സംഭവിച്ചു. വീണ്ടും ശ്രമിക്കുക." if lang == "ml" else "⚠️ Something went wrong. Please try again."
            yield f"event: message\ndata: {_json.dumps({'response': msg})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/translate")
def translate(req: TranslateRequest):
    translated = detect_and_translate(req.text, req.target)
    return {"translated": translated}


@app.get("/settings/key-info")
def settings_key_info():
    return get_key_info()

class UpdateKeyRequest(BaseModel):
    sarvam_api_key: str

@app.post("/settings/revert-key")
def settings_revert_key():
    if not _ORIGINAL_KEY:
        raise HTTPException(status_code=400, detail="No original key to revert to.")
    update_llm_key(_ORIGINAL_KEY)
    return {"status": "ok"}

@app.post("/settings/update-key")
def settings_update_key(req: UpdateKeyRequest):
    key = req.sarvam_api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    update_llm_key(key)
    # Persist to .env so it survives restarts
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
            with open(env_path, "w") as f:
                written = False
                for line in lines:
                    if line.startswith("SARVAM_API_KEY="):
                        f.write(f"SARVAM_API_KEY={key}\n")
                        written = True
                    else:
                        f.write(line)
                if not written:
                    f.write(f"\nSARVAM_API_KEY={key}\n")
    except Exception as e:
        print(f"[Settings] Could not persist key to .env: {e}")
    return {"status": "ok"}


@app.post("/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...), language: str = Form("ml")):
    suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        transcript = transcribe_audio(tmp_path, language=language)
    finally:
        os.unlink(tmp_path)

    if not transcript or not transcript.strip():
        raise HTTPException(status_code=422, detail="Could not transcribe audio — both STT services returned empty.")

    return {"transcript": transcript}


@app.post("/voice/synthesize")
def voice_synthesize(req: SynthesizeRequest):
    success = text_to_speech(req.text, TTS_OUTPUT_PATH)
    if not success:
        raise HTTPException(status_code=500, detail="TTS failed")
    return FileResponse(TTS_OUTPUT_PATH, media_type="audio/wav", filename="tts_output.wav")


# ── Known lat/lng for major coastal locations (top 20) ──────────────
_LOCATION_COORDS = {
    "Trivandrum":               (8.5241,  76.9366),
    "Vizhinjam&Kottapuram":     (8.3833,  76.9833),
    "Neendakara":               (8.9333,  76.5500),
    "Quilon":                   (8.8932,  76.6141),
    "Alappuzha":                (9.4981,  76.3388),
    "AlleppeyBeach":            (9.5000,  76.3333),
    "Ernakulam":                (9.9816,  76.2999),
    "MunambamFH":               (10.1833, 76.1667),
    "Calicut":                  (11.2588, 75.7804),
    "Beypore":                  (11.1667, 75.8167),
    "Ponnani":                  (10.7667, 75.9167),
    "Chavakkad":                (10.5833, 76.0167),
    "Thrissur":                 (10.5276, 76.2144),
    "Kannur":                   (11.8745, 75.3704),
    "Tellicherry":              (11.7483, 75.4925),
    "Kasaragod":                (12.4996, 74.9869),
    "Bekal":                    (12.4167, 75.0333),
    "Vadanappally":             (10.6333, 76.0167),
    "Thottappally":             (9.3167,  76.4167),
    "Sakthikulangara":          (8.9167,  76.5667),
}


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@app.post("/location/detect")
def location_detect(req: DetectLocationRequest):
    best_name = None
    best_dist = float("inf")
    for name, (lat, lng) in _LOCATION_COORDS.items():
        d = _haversine(req.lat, req.lng, lat, lng)
        if d < best_dist:
            best_dist = d
            best_name = name
    district = LOCATION_TO_DISTRICT.get(best_name)
    return {"location": best_name, "district": district, "distance_km": round(best_dist, 1)}


@app.post("/location/search")
def location_search(req: SearchLocationRequest):
    matches = find_location(req.query)
    return {"matches": matches}


@app.get("/location/all")
def location_all():
    from tools.location_finder import LOCATION_TO_DISTRICT
    locations = [
        f"{loc}, {LOCATION_TO_DISTRICT.get(loc, 'Unknown')}"
        for loc in KERALA_COASTAL_LOCATIONS
    ]
    return {"locations": locations}


# ── Profile endpoints ────────────────────────────────────────────────

@app.post("/profile/create")
def profile_create(req: CreateProfileRequest):
    try:
        profile = create_profile(
            name=req.name,
            phone=req.phone,
            coastal_location=req.coastal_location,
            district=req.district,
            preferred_species=req.preferred_species,
            fishing_zone=req.fishing_zone,
            boat_type=req.boat_type,
            registration_number=req.registration_number,
        )
        return {"profile": profile}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/profile/{phone}")
def profile_get(phone: str):
    profile = get_profile(phone)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    update_last_seen(phone)
    return {"profile": profile}


@app.post("/profile/update-location")
def profile_update_location(req: UpdateLocationRequest):
    profile = get_profile(req.phone)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    district = get_district_for_location(req.coastal_location)
    updated = update_location(req.phone, req.coastal_location, district or profile.get("district"))
    return {"profile": updated}


@app.get("/admin/profiles")
def admin_profiles():
    return {"profiles": get_all_profiles()}
