import json
from openai import BadRequestError

from agent.client import _chat
from agent.prompts import SYSTEM_PROMPT, INTENT_TO_TOOLS, classify_intent
from agent.tools import TOOLS, TOOL_FUNCTIONS
from agent.guardrails import MAX_TOOL_ROUNDS, _RAW_TOOL_RE, normalize_history, EMERGENCY_RE, EMERGENCY_RESPONSE, is_foul, FOUL_RESPONSE


def call_llm_events(
    prompt: str,
    language: str = "ml",
    coastal_location: str = None,
    district: str = None,
    history=None,
):
    """Generator that yields dicts:
      {"type": "tool_call", "tool": <name>}   — before each tool executes
      {"type": "message",   "response": <str>} — final answer
    """
    if language == "en":
        lang_instruction = "\nCRITICAL: You must ALWAYS reply in English only, regardless of the language the user wrote in. Never switch to Malayalam."
    else:
        lang_instruction = "\nCRITICAL: You must ALWAYS reply in Malayalam only, regardless of the language the user wrote in. Never switch to English."

    # ── Foul language check ──────────────────────────────────────────────
    if is_foul(prompt):
        lang_key = language if language in FOUL_RESPONSE else "en"
        yield {"type": "message", "response": FOUL_RESPONSE[lang_key]}
        return

    # ── Emergency — hard short-circuit, never depends on LLM ───────────────
    if EMERGENCY_RE.search(prompt):
        lang_key = language if language in EMERGENCY_RESPONSE else "en"
        suffix = (
            "\n\nകടലിൽ അപകടം ഉണ്ടായതിന് ശേഷം നഷ്ടപരിഹാരം അല്ലെങ്കിൽ ഇൻഷുറൻസ് ആവശ്യമുണ്ടെങ്കിൽ, "
            "ഞാനോട് ചോദിക്കൂ — ഞാൻ സർക്കാർ പദ്ധതി വിവരം നൽകാം."
            if lang_key == "ml" else
            "\n\nOnce safe, ask me about accident compensation or insurance schemes available to you."
        )
        yield {"type": "message", "response": EMERGENCY_RESPONSE[lang_key] + suffix}
        return

    location_context = ""
    if coastal_location:
        dist_part = f" ({district} district)" if district else ""
        location_context = (
            f"\nFisherman's home location: {coastal_location}{dist_part}\n"
            "Use this location automatically for all sea safety and zone advisory queries "
            "unless the fisherman specifies a different location."
        )

    # ── Intent classification ────────────────────────────────────────
    classification   = classify_intent(prompt, history=normalize_history(history))
    confidence       = classification.get("confidence", "medium")
    needs_clarify    = classification.get("clarification_needed", False)
    intents          = classification.get("intents", [])
    clarify_question = classification.get("clarification_question", "")

    if (confidence == "low" or needs_clarify) and clarify_question:
        yield {"type": "message", "response": clarify_question}
        return

    # Build intent hint to steer tool selection
    relevant_tools = list({INTENT_TO_TOOLS[i] for i in intents if i in INTENT_TO_TOOLS})
    intent_hint = ""
    if relevant_tools:
        intent_hint = (
            f"\nDetected intent: {', '.join(intents)}. "
            f"You should call: {', '.join(relevant_tools)}."
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + location_context + lang_instruction + intent_hint},
        *normalize_history(history),
        {"role": "user", "content": prompt},
    ]
    seen_calls: set[str] = set()

    for _round in range(MAX_TOOL_ROUNDS):
        for attempt in range(3):
            try:
                response = _chat(messages=messages, tools=TOOLS)
                break
            except BadRequestError as e:
                if "tool_use_failed" in str(e) and attempt < 2:
                    print(f"[Malformed tool call, retrying {attempt + 1}/3...]")
                else:
                    raise

        msg = response.choices[0].message
        content = msg.content or ""

        if not msg.tool_calls:
            if _RAW_TOOL_RE.search(content):
                print(f"[Raw tool call detected in content, round {_round}] — dropping response")
                break
            yield {"type": "message", "response": content}
            return

        messages.append(msg)

        result_parts = []
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                print(f"[Bad tool args]: {tc.function.arguments}")
                result_parts.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"error": "Invalid arguments"}),
                })
                continue

            if tc.function.name == "get_sea_safety" and not args.get("district"):
                if district:
                    args["district"] = district
                    print(f"[Auto-location]: injected district={district}")
                else:
                    result_parts.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({
                            "error": "District not known. Ask the user which Kerala coastal district or city they are in before checking sea conditions."
                        }),
                    })
                    continue

            call_key = f"{tc.function.name}:{json.dumps(args, sort_keys=True)}"
            if call_key in seen_calls:
                print(f"[Skipped duplicate]: {tc.function.name} args={args}")
                result = {"note": "duplicate call skipped"}
            else:
                seen_calls.add(call_key)
                yield {"type": "tool_call", "tool": tc.function.name}
                print(f"[Tool]: {tc.function.name}  args={args}")
                result = TOOL_FUNCTIONS[tc.function.name](args)
                print(f"[Result]: {result}")
                if isinstance(result, dict) and result.pop("_incois_scraped", False):
                    yield {"type": "tool_call", "tool": "incois_scraper"}
                if tc.function.name == "get_price_history" and "history" in result:
                    yield {"type": "price_data", "data": result}

            result_parts.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

        messages.extend(result_parts)

    # Reached here via break (raw tool leak) or exhausted MAX_TOOL_ROUNDS
    fallback = (
        "ക്ഷമിക്കണം, ഇപ്പോൾ ഉത്തരം കിട്ടിയില്ല. വീണ്ടും ശ്രമിക്കുക."
        if language != "en"
        else "Sorry, I couldn't get an answer right now. Please try again."
    )
    yield {"type": "message", "response": fallback}


def call_llm(
    prompt: str,
    language: str = "ml",
    coastal_location: str = None,
    district: str = None,
    history=None,
) -> str:
    for event in call_llm_events(prompt, language, coastal_location, district, history):
        if event["type"] == "message":
            return event["response"]
