import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TOOL_ROUNDS = 5

# Detects raw function-call syntax leaking into message content (weaker models)
_RAW_TOOL_RE = re.compile(
    r"<function=|<tool_call>|\[TOOL_CALLS\]|\"name\":\s*\"get_",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Emergency detection — bypasses LLM entirely
# ---------------------------------------------------------------------------

# Events that are inherently at-sea emergencies — no extra sea keyword needed
_EMERGENCY_INHERENT_RE = re.compile(
    r"accident\s+at\s+sea|sinking|drowning|capsiz|mayday|"
    r"help.*sea|sea.*help|boat.*sank|sank.*boat|"
    r"മുങ്ങ|അത്യാഹിതം|കടലിൽ\s*സഹായം|ബോട്ട്\s*മുങ്ങി",
    re.IGNORECASE,
)

# Sea context keywords — must appear in the message for fuel/accident to trigger
_SEA_CONTEXT_RE = re.compile(
    r"\b(sea|ocean|boat|vessel|fishing|trawler|harbour|harbor|shore|coast|കടൽ|ബോട്ട്|കര|തീരം|മത്സ്യബന്ധന)\b",
    re.IGNORECASE,
)

# Fuel/accident events that only count when sea context is also present
_EMERGENCY_CONDITIONAL_RE = re.compile(
    r"no\s+fuel|out\s+of\s+fuel|out\s+of\s+diesel|out\s+of\s+kerosene|"
    r"accident|rescue|emergency|"
    r"അപകടം|രക്ഷ|ഇന്ധനം\s*തീർന്നു|മണ്ണെണ്ണ\s*തീർന്നു|ഡീസൽ\s*തീർന്നു",
    re.IGNORECASE,
)


def is_emergency(text: str) -> bool:
    """Return True only when the message describes an at-sea emergency."""
    if _EMERGENCY_INHERENT_RE.search(text):
        return True
    if _EMERGENCY_CONDITIONAL_RE.search(text) and _SEA_CONTEXT_RE.search(text):
        return True
    return False


# Keep EMERGENCY_RE as an alias so existing imports don't break
class _EmergencyRE:
    """Mimics re.Pattern.search() but uses the is_emergency() logic."""
    def search(self, text: str):
        return is_emergency(text) or None


EMERGENCY_RE = _EmergencyRE()

EMERGENCY_RESPONSE = {
    "ml": (
        "🆘 ഉടൻ ഈ നമ്പറുകളിൽ വിളിക്കുക കടലിൽ നിങ്ങൾ കുഴപ്പത്തിലാണെങ്കിൽ:\n"
        "• കോസ്റ്റ് ഗാർഡ് (Coast Guard): 1554\n"
        "• ദേശീയ അത്യാഹിത (National Emergency): 112\n"
        "• കേരള പോലീസ് (Kerala Police): 100"
    ),
    "en": (
        "🆘 Call these numbers immediately if you are in trouble at sea:\n"
        "• Coast Guard: 1554\n"
        "• National Emergency: 112\n"
        "• Kerala Police: 100"
    ),
    
}

# ---------------------------------------------------------------------------
# Foul language guardrail
# ---------------------------------------------------------------------------

_FOUL_EN = re.compile(
    r"\b(fuck|fucking|fucker|shit|bitch|asshole|bastard|cunt|dick|cock|pussy|"
    r"motherfucker|whore|slut|nigger|faggot|damn\s+you|go\s+to\s+hell|"
    r"son\s+of\s+a\s+bitch|piece\s+of\s+shit)\b",
    re.IGNORECASE,
)

# Common Malayalam abuses (transliterated and Unicode)
_FOUL_ML = re.compile(
    r"thendi|thendiye|poorr|poori|myre|myru|maire|punda|pundachi|"
    r"kunna|kundi|kotham|kothamme|veṭṭi|vetti|chekkan|chakki|"
    r"thevidiya|thevidichi|അവൻ്റെ|പൂറ്|മൈര്|കുണ്ട|പണ്ട|തേവിടിശ്ശി|"
    r"ഭോഷ്|മണ്ടൻ|കഴുത",
    re.IGNORECASE,
)

FOUL_RESPONSE = {
    "ml": "ദയവായി മാന്യമായ ഭാഷ ഉപയോഗിക്കുക. നിങ്ങളെ സഹായിക്കാൻ ഞാൻ ഇവിടെ ഉണ്ട്.",
    "en": "Please use respectful language. I'm here to help you.",
}


def is_foul(text: str) -> bool:
    return bool(_FOUL_EN.search(text) or _FOUL_ML.search(text))


# ---------------------------------------------------------------------------
# History normalisation
# ---------------------------------------------------------------------------

def normalize_history(history) -> list[dict]:
    """Keep only the last 6 user/assistant turns in OpenAI chat format."""
    normalized = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role == "agent":
            role = "assistant"
        if role not in {"user", "assistant"}:
            continue
        content = (item.get("content") or item.get("text") or "").strip()
        if not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized[-6:]


