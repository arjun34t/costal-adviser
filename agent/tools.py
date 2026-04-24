from tools.sea_safety import get_sea_safety
from tools.market_prices import get_market_price, get_price_history
from tools.govt_schemes import get_scheme_info

# ---------------------------------------------------------------------------
# OpenAI tool schemas — passed to the LLM on every chat call
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sea_safety",
            "description": (
                "Call ONLY when the fisherman explicitly asks about sea safety, waves, wind, "
                "weather, or whether it is safe to go fishing. Returns wave height, wind speed, "
                "safe_to_fish flag, and up to 3 INCOIS fishing zone advisories (direction, "
                "distance, depth) for the district. Do NOT call this for price or scheme questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "district": {
                        "type": "string",
                        "description": "Kerala coastal district name, e.g. Kozhikode, Kochi, Alappuzha.",
                    }
                },
                "required": ["district"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_price",
            "description": "Returns today's fish price in rupees per kg at a Kerala fish market.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fish_type": {
                        "type": "string",
                        "description": "Type of fish, e.g. Pomfret, Sardine, Mackerel, Tuna, Prawns, Karimeen.",
                    },
                    "market": {
                        "type": "string",
                        "description": "Market/district name, e.g. Kozhikode, Kochi, Alappuzha.",
                    },
                },
                "required": ["fish_type", "market"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": (
                "Returns the 7-day price trend for a fish variety. "
                "When multiple fish are mentioned, call this tool once per fish type in parallel. "
                "Call this (along with get_market_price) when the fisherman mentions "
                "catching, landing, or having fish to sell — to compare today's price "
                "against recent prices and advise whether to sell now or store. "
                "If the fisherman asks about a specific day ('yesterday', '2 days ago', "
                "or a date like '2026-04-08'), pass that as the `date` parameter to get "
                "the price for that exact day."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fish_type": {
                        "type": "string",
                        "description": "Type of fish, e.g. Pomfret, Sardine, Mackerel, Tuna, Prawns, Crab.",
                    },
                    "market": {
                        "type": "string",
                        "description": "Market/district name, e.g. Kozhikode, Kochi, Alappuzha.",
                    },
                    "date": {
                        "type": "string",
                        "description": (
                            "Optional. Specific date to look up. Accepts 'yesterday', "
                            "'2 days ago', or an ISO date string 'YYYY-MM-DD'. "
                            "Omit to get the full 7-day trend."
                        ),
                    },
                },
                "required": ["fish_type", "market"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scheme_info",
            "description": (
                "Searches Kerala and central government welfare schemes for fishermen using "
                "semantic search. Pass a descriptive phrase, not a single word."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": (
                            "Descriptive search phrase, e.g. 'financial help to buy a new fishing boat', "
                            "'accident compensation for fisherman death', 'diesel fuel subsidy for boats', "
                            "'loan for fishing equipment'."
                        ),
                    }
                },
                "required": ["keyword"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool dispatch — maps tool name → callable
# ---------------------------------------------------------------------------

TOOL_FUNCTIONS = {
    "get_sea_safety":    lambda args: get_sea_safety(**args),
    "get_market_price":  lambda args: get_market_price(**args),
    "get_price_history": lambda args: get_price_history(**args),
    "get_scheme_info":   lambda args: get_scheme_info(**args),
}
