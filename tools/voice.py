import os
import re
import io
import wave
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
STT_URL        = "https://api.sarvam.ai/speech-to-text"
TTS_URL        = "https://api.sarvam.ai/text-to-speech"
TIMEOUT        = 30

_SARVAM_LANG = {
    "ml": "ml-IN", "en": "en-IN", "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN",
}
_MIME_MAP = {
    ".webm": "audio/webm", ".ogg": "audio/ogg", ".wav": "audio/wav",
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
}

# ── Malayalam term replacements (English → Malayalam script) ────────────
_ML_TERMS = [
    # Fish names
    (r"\bPomfret\b",   "പോംഫ്രെറ്റ്"),
    (r"\bMackerel\b",  "അയല"),
    (r"\bSardine\b",   "മത്തി"),
    (r"\bPrawn\b",     "ചെമ്മീൻ"),
    (r"\bCrab\b",      "ഞണ്ട്"),
    (r"\bTuna\b",      "ചൂര"),
    (r"\bSeer\b",      "നെയ്മീൻ"),
    (r"\bKarimeen\b",  "കരിമീൻ"),
    (r"\bKingfish\b",  "നെയ്മീൻ"),
    # Scheme acronyms
    (r"\bPMSBY\b",     "പ്രധാനമന്ത്രി സുരക്ഷ ബീമ"),
    (r"\bPMJJBY\b",    "പ്രധാനമന്ത്രി ജീവൻ ജ്യോതി"),
    (r"\bKMFRI\b",     "കേരള മത്സ്യ ഗവേഷണ സ്ഥാപനം"),
    (r"\bFISFED\b",    "ഫിസ്ഫെഡ്"),
    # Common English words that sound bad in Malayalam TTS
    (r"\bdistrict\b",  "ജില്ല"),
    (r"\bscheme\b",    "പദ്ധതി"),
    (r"\bsubsidy\b",   "സബ്സിഡി"),
]


def _preprocess_for_tts(text: str) -> str:
    """Clean and normalise Malayalam TTS input."""

    # 1. Strip markdown formatting
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)          # **bold**
    text = re.sub(r"\*(.*?)\*",     r"\1", text)           # *italic*
    text = re.sub(r"`(.*?)`",       r"\1", text)           # `code`
    text = re.sub(r"^#{1,6}\s+",   "",    text, flags=re.MULTILINE)  # ## headers
    text = re.sub(r"^[•\-\*]\s+",  "",    text, flags=re.MULTILINE)  # • bullets
    text = re.sub(r"\[.*?\]\(.*?\)", "",  text)            # [links](url)

    # 2. Currency — ₹450 → "450 രൂപ"
    text = re.sub(
        r"₹\s*(\d[\d,]*(?:\.\d+)?)",
        lambda m: m.group(1).replace(",", "") + " രൂപ",
        text,
    )

    # 3. Units → Malayalam
    text = re.sub(r"(\d+(?:\.\d+)?)\s*km/h\b", r"\1 കിലോമീറ്റർ", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*km\b",   r"\1 കിലോമീറ്റർ", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*m\b",    r"\1 മീറ്റർ",     text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*kg\b",   r"\1 കിലോഗ്രാം", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%\b",    r"\1 ശതമാനം",    text)

    # 4. English terms → Malayalam script (case-insensitive)
    for pattern, replacement in _ML_TERMS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 5. Collapse multiple blank lines / extra whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ",  text)

    return text.strip()


def _split_sentences(text: str, max_chars: int = 400) -> list:
    """Split text into TTS-safe chunks at sentence boundaries."""
    # Split on sentence-ending punctuation and newlines
    raw = re.split(r"(?<=[.!?।\n])\s+|\n{2,}", text)
    chunks = []
    current = ""

    for part in raw:
        part = part.strip()
        if not part:
            continue

        if len(current) + len(part) + 1 <= max_chars:
            current = (current + " " + part).strip()
        else:
            if current:
                chunks.append(current)
            # If a single part is itself too long, force-split by words
            if len(part) > max_chars:
                words = part.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= max_chars:
                        current = (current + " " + word).strip()
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = part

    if current:
        chunks.append(current)

    return chunks


def _merge_wav_bytes(wav_chunks: list) -> bytes:
    """Merge a list of raw WAV byte strings into a single WAV."""
    if len(wav_chunks) == 1:
        return wav_chunks[0]

    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        params_written = False
        for chunk in wav_chunks:
            with wave.open(io.BytesIO(chunk), "rb") as src:
                if not params_written:
                    out.setparams(src.getparams())
                    params_written = True
                out.writeframes(src.readframes(src.getnframes()))

    return buf.getvalue()


def _call_sarvam_tts(inputs: list, language: str = "ml") -> list:
    """Call Sarvam TTS with a list of text inputs. Returns list of raw WAV bytes."""
    lang_code = _SARVAM_LANG.get(language, "ml-IN")
    response = requests.post(
        TTS_URL,
        headers={
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "inputs": inputs,
            "target_language_code": lang_code,
            "model": "bulbul:v2",
        },
        timeout=TIMEOUT,
    )

    if response.status_code == 401:
        raise RuntimeError("Invalid Sarvam API key")

    response.raise_for_status()

    audios = response.json().get("audios", [])
    if not audios:
        raise RuntimeError("No audio returned from Sarvam TTS")

    return [base64.b64decode(a) for a in audios]


# ── Public API ──────────────────────────────────────────────────────────

def transcribe_audio(audio_file_path: str, language: str = "ml") -> str:
    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not set.")

    lang_code = _SARVAM_LANG.get(language, "ml-IN")
    ext  = os.path.splitext(audio_file_path)[1].lower()
    mime = _MIME_MAP.get(ext, "audio/webm")

    with open(audio_file_path, "rb") as f:
        response = requests.post(
            STT_URL,
            headers={"api-subscription-key": SARVAM_API_KEY},
            files={"file": (os.path.basename(audio_file_path), f, mime)},
            data={"model": "saaras:v3", "language_code": lang_code},
            timeout=TIMEOUT,
        )

    print(f"[STT] Status: {response.status_code}")
    if not response.ok:
        print(f"[STT] Error body: {response.text[:300]}")
    response.raise_for_status()

    body = response.json()
    print(f"[STT] Response body: {body}")
    transcript = body.get("transcript", "") or body.get("text", "")
    print(f"[STT] Transcribed ({len(transcript)} chars)")
    return transcript


def text_to_speech(text: str, output_path: str, language: str = "ml") -> bool:
    if not text.strip():
        print("[TTS] Empty text — skipping.")
        return False

    if not SARVAM_API_KEY:
        print("[TTS Error] SARVAM_API_KEY not set.")
        return False

    try:
        # Step 1: preprocess
        clean = _preprocess_for_tts(text)
        print(f"[TTS] Preprocessed: {len(text)} → {len(clean)} chars")

        # Step 2: split into sentence chunks (≤400 chars each)
        chunks = _split_sentences(clean)
        print(f"[TTS] Split into {len(chunks)} chunk(s)")

        # Step 3: call Sarvam in batches of 3 (API-safe batch size)
        BATCH = 3
        all_wav: list = []
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i : i + BATCH]
            print(f"[TTS] Sending batch {i // BATCH + 1}: {[len(c) for c in batch]} chars")
            wav_parts = _call_sarvam_tts(batch, language)
            all_wav.extend(wav_parts)

        # Step 4: merge and write
        merged = _merge_wav_bytes(all_wav)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(merged)

        print(f"[TTS] Saved {len(merged):,} bytes → {output_path}")
        return True

    except requests.exceptions.Timeout:
        print("[TTS Error] Request timed out.")
        return False
    except Exception as e:
        print(f"[TTS Error] {e}")
        return False
