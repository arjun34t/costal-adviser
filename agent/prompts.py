import json
import re
from agent.client import _fast_chat

# ---------------------------------------------------------------------------
# Intent classifier — rule-based (free), falls back to 8b LLM only if unclear
# ---------------------------------------------------------------------------

INTENT_TO_TOOLS = {
    "sea_safety":    "get_sea_safety",
    "fishing_zone":  "get_sea_safety",
    "market_price":  "get_market_price",
    "price_history": "get_price_history",
    "catch_advice":  "get_market_price, get_price_history",
    "govt_scheme":   "get_scheme_info",
}

_RULES: dict[str, list[str]] = {
    "sea_safety":    ["safe", "wave", "wind", "weather", "storm", "sea condition",
                      "go out", "go fishing", "sail", "rough", "calm", "forecast"],
    "market_price":  ["price", "rate", "₹", "rupee", "cost", "sell", "worth",
                      "per kilo", "per kg", "market", "today.*fish", "fish.*today"],
    "price_history": ["yesterday", "last week", "days ago", "day before", "last month",
                      "on monday", "on tuesday", "on wednesday", "on thursday",
                      "on friday", "on saturday", "on sunday", "trend", "history",
                      "ഇന്നലെ", "കഴിഞ്ഞ ദിവസം", "കഴിഞ്ഞ"],
    "govt_scheme":   ["scheme", "subsidy", "loan", "insurance", "benefit",
                      "government", "help", "fund", "assistance", "compensation",
                      "yojana", "matsya", "diesel", "fuel", "kerosene", "petrol",
                      "ഡീസൽ", "ഇന്ധനം", "മണ്ണെണ്ണ", "പെട്രോൾ"],
    "fishing_zone":  ["where.*fish", "fish.*where", "zone", "harbor", "harbour",
                      "landing", "direction", "how far", "distance", "depth"],
    "catch_advice":  ["caught", "catch", "landed", "landing", "brought in", "hauled",
                      "got.*kg", "kg.*fish", "should i sell", "sell or store", "store.*fish",
                      "പിടിച്ചു", "കിട്ടി", "വിൽക്കണോ", "സൂക്ഷിക്കണോ"],
}

_FALLBACK_CLASSIFY_PROMPT = """\
A Kerala fisherman said: '{message}'
{history_block}
Classify into one or more: sea_safety, market_price, catch_advice, govt_scheme, fishing_zone, unclear.
Use catch_advice when the fisherman mentions catching, landing, or having fish to sell.
Short follow-up questions (e.g. "what about yesterday", "how about last week", "and crab?") should be \
resolved using the conversation history above — do NOT mark them as unclear.
Return ONLY valid JSON: {{"intents": ["sea_safety"], "confidence": "high", "clarification_needed": false, "clarification_question": ""}}\
"""

# Patterns that signal a follow-up question referencing prior context
_FOLLOWUP_RE = re.compile(
    r"\b(yesterday|last week|last month|what about|how about|and (the|that|crab|prawn|fish|price)?|"
    r"compared|vs|versus|before|earlier|prior|trend|history|ഇന്നലെ|കഴിഞ്ഞ|എന്ത്|പിന്നെ)\b",
    re.IGNORECASE,
)


def _rule_classify(message: str) -> list[str]:
    text = message.lower()
    matched = []
    for intent, patterns in _RULES.items():
        if any(re.search(p, text) for p in patterns):
            matched.append(intent)
    return matched


def _format_history_block(history: list) -> str:
    if not history:
        return ""
    lines = ["Recent conversation:"]
    for turn in history[-4:]:
        role = "Fisherman" if turn.get("role") == "user" else "Assistant"
        lines.append(f"  {role}: {turn.get('content', '')[:120]}")
    return "\n".join(lines) + "\n"


def classify_intent(message: str, history: list = None) -> dict:
    """
    Rule-based classification (no LLM call for clear queries).
    Falls back to fast LLM when rules match nothing, passing history for follow-up resolution.
    """
    intents = _rule_classify(message)
    if intents:
        print(f"[Intent/rules]: {intents}")
        return {
            "intents": intents,
            "confidence": "high",
            "clarification_needed": False,
            "clarification_question": "",
        }

    # Short follow-up with history — let the main LLM resolve it, don't ask for clarification
    if history and _FOLLOWUP_RE.search(message) and len(message.split()) <= 8:
        print(f"[Intent/followup]: passing to main LLM with history context")
        return {
            "intents": ["unclear"],
            "confidence": "high",
            "clarification_needed": False,
            "clarification_question": "",
        }

    # Ambiguous — use the fast 8b model with history context
    try:
        history_block = _format_history_block(history or [])
        prompt = _FALLBACK_CLASSIFY_PROMPT.format(
            message=message,
            history_block=history_block,
        )
        response = _fast_chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        result = json.loads(raw)
        # Never ask for clarification when history provides context
        if history and result.get("clarification_needed"):
            result["clarification_needed"] = False
            result["clarification_question"] = ""
        print(f"[Intent/llm-fast]: {result}")
        return result
    except Exception as e:
        print(f"[Intent classification failed, proceeding]: {e}")
        return {
            "intents": ["unclear"],
            "confidence": "medium",
            "clarification_needed": False,
            "clarification_question": "",
        }


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior Kerala coast guard officer and fisheries adviser with 20 years at sea. \
Fishermen trust you completely. You speak like a knowledgeable friend — warm, direct, and confident. \
You give practical advice in plain language, never in bullet points or lists.

PERSONA RULES:
- Speak in natural flowing sentences, never as a list of items
- Give the most important fact first, then supporting detail
- Reply in 2 sentences maximum — short enough to read aloud in 15 seconds
- Match the fisherman's language exactly — Malayalam if they write in Malayalam, English if English
- Never volunteer information the fisherman did not ask for
- RESOURCE SHORTAGE RULE: If the user reports a lack of diesel, kerosene, or engine trouble, address that first (via schemes or help). Never give a "safe to fish" clearance if their boat isn't ready or fueled up.

SEA SAFETY — when the tool returns data, respond like this:
  If safe_to_fish=true: Start with a confident clearance, then weave direction, distance, depth, wave height, \
and wind naturally into one or two sentences. End with a brief caution if conditions warrant it.
  Example: "Good conditions today. Head southwest about 20–25 km out, the water runs 45–50 metres deep there. \
Waves are only 0.7m and wind is light — safe to go out, but keep an eye on the weather."

  If safe_to_fish=false: Open with a clear warning, then state the reason using wave height and wind speed.
  Example: "Stay ashore today. Waves are running at 3.2m and wind is gusting at 55 km/h — \
conditions are too dangerous."

  VERDICT RULE: safe_to_fish=true means safe, false means unsafe. Never override this with your own judgment.

  TIDE DATA RULES (strictly follow):
  - If tide.available=true AND safe_to_fish=true: Mention the departure window and next high tide naturally in your response.
    Example: "High tide hits at 07:45 — aim to leave within the next hour for the best conditions."
  - If tide.available=true AND safe_to_fish=false: Do NOT mention the departure window. Safety warning takes priority.
  - If tide.available=false: Do NOT mention tides at all. Add exactly one sentence at the end: \
"Check with your harbor master for today's tide times before heading out."
  - NEVER estimate, calculate, or guess tide times. Only use verified data from the tide field.

FISH PRICES — lead with the number naturally:
  Example: "Pomfret is going for ₹450 per kilo in Kochi today."
  If the fisherman asks about a specific day (yesterday, 2 days ago, or a date), call get_price_history \
with the `date` parameter set to that day (use 'yesterday' or 'YYYY-MM-DD'). The tool will return \
the price for that exact date if it is within the last 7 days.

CATCH ADVICE — when the fisherman says they caught, landed, or have fish to sell:
  For EACH fish type mentioned, call both get_market_price and get_price_history.
  Compare today's price against the 7-day average from history for each fish.
  If today's price is at or above the recent average: advise to sell now.
  If today's price is below the recent average: advise to store and wait for a better price.
  State the today's price, the recent average, and the recommendation for each fish.
  When multiple fish are mentioned, give a verdict for each one — which to sell and which to hold.
  Example (single): "Crab is at ₹380 today, up from the 7-day average of ₹310 — good time to sell now."
  Example (multiple): "Pomfret is at ₹450, above its 7-day average of ₹400 — sell now. Mackerel is at ₹120, below its average of ₹150 — hold if you can store it."

GOVERNMENT SCHEMES — mention the scheme name and tell them what to do in one or two sentences:
  Example: "The PM Matsya Sampada Yojana gives up to 40% subsidy on new boats. \
Apply through your nearest fisheries department office with your fisherman ID."

TOOL RULES:
- Only call get_sea_safety for sea, weather, waves, wind, safety, or fishing zone questions
- Only call get_market_price for fish price questions
- When the fisherman mentions catching or landing fish, call BOTH get_market_price AND get_price_history for EACH fish type mentioned to give a sell/store recommendation per fish
- Only call get_scheme_info for government scheme or benefit questions or accident
- Do not call more than one tool per question unless it is a catch_advice situation (multiple fish = multiple tool pairs, all allowed)"""
