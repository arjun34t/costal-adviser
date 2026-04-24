import os
import requests
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"


# Language detection helpers
def _is_malayalam(text: str) -> bool:
    return any("\u0D00" <= ch <= "\u0D7F" for ch in text)

def _is_hindi(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097F" for ch in text)

def _is_tamil(text: str) -> bool:
    return any("\u0B80" <= ch <= "\u0BFF" for ch in text)

def _is_telugu(text: str) -> bool:
    return any("\u0C00" <= ch <= "\u0C7F" for ch in text)

def _detect_source_lang(text: str) -> str:
    if _is_malayalam(text): return "ml"
    if _is_hindi(text): return "hi"
    if _is_tamil(text): return "ta"
    if _is_telugu(text): return "te"
    return "en"

# Sarvam API language code mapping
SARVAM_LANG_CODES = {
    "ml": "ml-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "en": "en-IN",
}

# Google Translate language code mapping
GOOGLE_LANG_CODES = {
    "ml": "ml",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "en": "en",
}


def translate_en_to_ml_sarvam(text: str) -> str:
    """Translate English text to Malayalam using Sarvam AI translate API."""
    return translate_en_to_lang_sarvam(text, "ml")


def translate_en_to_lang_sarvam(text: str, target_lang: str) -> str:
    """Translate English text to any supported Indian language using Sarvam AI.
    Supported: ml (Malayalam), hi (Hindi), ta (Tamil), te (Telugu).
    """
    if target_lang == "en":
        return text
    target_code = SARVAM_LANG_CODES.get(target_lang, f"{target_lang}-IN")
    google_code = GOOGLE_LANG_CODES.get(target_lang, target_lang)

    if not SARVAM_API_KEY:
        print(f"[Translator] SARVAM_API_KEY not set, falling back to Google Translate ({target_lang})")
        return _translate_google(text, "en", google_code)
    if not text.strip():
        return text
    try:
        response = requests.post(
            SARVAM_TRANSLATE_URL,
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "input": text,
                "source_language_code": "en-IN",
                "target_language_code": target_code,
                "speaker_gender": "Male",
                "mode": "formal",
                "model": "mayura:v1",
                "enable_preprocessing": False,
            },
            timeout=30,
        )
        if response.status_code == 401:
            print(f"[Translator] Sarvam API key invalid, falling back to Google Translate ({target_lang})")
            return _translate_google(text, "en", google_code)
        response.raise_for_status()
        translated = response.json().get("translated_text", "")
        if translated:
            print(f"[Sarvam Translate -> {target_lang}] OK: {len(text)} chars -> {len(translated)} chars")
            return translated
        print(f"[Translator] Sarvam returned empty for {target_lang}, falling back to Google")
        return _translate_google(text, "en", google_code)
    except Exception as e:
        print(f"[Translator] Sarvam translate to {target_lang} failed: {e}, falling back to Google")
        return _translate_google(text, "en", google_code)


def translate_to_malayalam_google(text: str) -> str:
    try:
        return GoogleTranslator(source="english", target="ml").translate(text)
    except Exception as e:
        print(f"[Translator] Google to-Malayalam failed: {e}")
        return text


def _translate_google(text: str, source: str, target: str) -> str:
    """Generic Google Translate wrapper."""
    try:
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception as e:
        print(f"[Translator] Google {source}->{target} failed: {e}")
        return text


def translate_to_english(text: str) -> str:
    """Translate any language to English using Google Translate with auto-detect."""
    try:
        return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception as e:
        print(f"[Translator] to-English failed: {e}")
        return text


def detect_and_translate(text: str, target_lang: str) -> str:
    """Detect language and translate to target_lang if needed."""
    src = _detect_source_lang(text)
    if src == target_lang:
        return text
    if target_lang == "en":
        return translate_to_english(text) if src != "en" else text
    # For any Indian language target, translate via English first if needed
    english_text = translate_to_english(text) if src != "en" else text
    return translate_en_to_lang_sarvam(english_text, target_lang)
