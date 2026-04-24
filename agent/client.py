import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SARVAM_MODEL = "sarvam-30b"

# Key loaded at server start — used as the "revert to original" target
_ORIGINAL_KEY = os.environ.get("SARVAM_API_KEY", "")

class SarvamClient:
    def __init__(self):
        self.sarvam_key = os.environ.get("SARVAM_API_KEY")
        # Ensure we always return an OpenAI client, or fail gracefully later
        if self.sarvam_key:
            self.client = OpenAI(api_key=self.sarvam_key, base_url="https://api.sarvam.ai/v1")
        else:
            self.client = None

    def chat(self, messages, tools=None, tool_choice=None, temperature=None):
        if not self.client:
            raise ValueError("SARVAM_API_KEY is not set.")
        kwargs = {
            "model": SARVAM_MODEL,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        if temperature is not None:
            kwargs["temperature"] = temperature
            
        return self.client.chat.completions.create(**kwargs)

_client = SarvamClient()

def update_llm_key(new_key: str):
    """Hot-reload the Sarvam API key without restarting the server."""
    os.environ["SARVAM_API_KEY"] = new_key
    _client.sarvam_key = new_key
    _client.client = OpenAI(api_key=new_key, base_url="https://api.sarvam.ai/v1")

def get_key_info() -> dict:
    """Return masked current key and whether it matches the original."""
    current = _client.sarvam_key or ""
    original = _ORIGINAL_KEY
    masked = (current[:6] + "…" + current[-4:]) if len(current) > 10 else ("*" * len(current))
    return {
        "masked": masked,
        "is_original": current == original,
        "has_key": bool(current),
    }

def _chat(messages, tools=None, tool_choice=None, temperature=None):
    return _client.chat(messages, tools=tools, tool_choice=tool_choice, temperature=temperature)

def _fast_chat(messages, temperature=None):
    return _client.chat(messages, temperature=temperature)
