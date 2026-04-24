export const API_BASE =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "/api";

export const HISTORY_KEY = "fisher_chat_history";
export const MAX_HISTORY = 50;

export const LABELS = {
  ml: {
    inputPlaceholder: "ചോദ്യം ടൈപ്പ് ചെയ്യുക…",
    recordingText: "റെക്കോർഡ് ചെയ്യുന്നു…",
    stopBtn: "നിർത്തുക",
    switched: "മലയാളത്തിലേക്ക് മാറ്റി",
    cleared: "സംഭാഷണം മായ്ച്ചു",
    errorPrefix: "പിശക്",
    transcriptionFailed: "⚠️ ശബ്ദം മനസിലാക്കാൻ കഴിഞ്ഞില്ല. വീണ്ടും ശ്രമിക്കുക.",
    micDenied: "⚠️ മൈക്രോഫോൺ അനുമതി ലഭിച്ചില്ല.",
    geolocationUnsupported: "⚠️ ഈ ബ്രൗസറിൽ സ്ഥലം കണ്ടെത്തൽ പിന്തുണയ്ക്കുന്നില്ല.",
    gpsFailed: "⚠️ GPS സ്ഥലം ലഭിച്ചില്ല. ദയവായി മാനുവലായി തിരഞ്ഞെടുക്കുക.",
    locationUnset: "തീരദേശ സ്ഥലം തിരഞ്ഞെടുക്കുക",
    districtUnset: "ജില്ല ലഭ്യമല്ല",
    locationMetaUnset: "സ്ഥലം തിരഞ്ഞെടുത്തിട്ടില്ല",
    detecting: "സ്ഥലം കണ്ടെത്തുന്നു…",
    languageName: "മലയാളം",
    audioOn: "ഓൺ",
    audioOff: "ഓഫ്",
    userLabel: "നിങ്ങൾ",
    agentLabel: "സഹായി",
    composerHint: "ഉദാഹരണം: ഇന്ന് ബേപ്പൂരിൽ കടൽ നില എങ്ങനെയാണ്?",
    searchPlaceholder: "സ്ഥലം തിരയുക…",
    moreResults: (count) => `${count} കൂടുതൽ ഫലങ്ങൾ - കൂടുതൽ തിരയാൻ ടൈപ്പ് ചെയ്യുക`,
    districtText: (district) => `${district} ജില്ല`,
    quickActions: [
      "ഇന്ന് കടലിൽ പോകാൻ സുരക്ഷിതമാണോ?",
      "ഇന്ന് മീൻ വില എന്താണ്?",
      "എനിക്ക് ലഭിക്കാവുന്ന സർക്കാർ പദ്ധതികൾ എന്തൊക്കെയാണ്?",
      "🆘 കടലിൽ അപകടം ഉണ്ടായി",
    ],
  },
  en: {
    inputPlaceholder: "Type your question…",
    recordingText: "Recording…",
    stopBtn: "Stop",
    switched: "Switched to English",
    cleared: "Conversation cleared",
    errorPrefix: "Error",
    transcriptionFailed: "⚠️ Could not transcribe audio. Please try again.",
    micDenied: "⚠️ Microphone access denied.",
    geolocationUnsupported: "⚠️ Geolocation is not supported by this browser.",
    gpsFailed: "⚠️ Could not get GPS location. Please search manually.",
    locationUnset: "Select coastal location",
    districtUnset: "District not set",
    locationMetaUnset: "No location selected",
    detecting: "Detecting location…",
    languageName: "English",
    audioOn: "On",
    audioOff: "Off",
    userLabel: "You",
    agentLabel: "Assistant",
    composerHint: "Example: How are sea conditions in Beypore today?",
    searchPlaceholder: "Search location…",
    moreResults: (count) => `${count} more results - type to narrow down`,
    districtText: (district) => `${district} district`,
    quickActions: [
      "Is it safe to go fishing today?",
      "What are today's fish prices?",
      "Which government schemes can I use?",
      "🆘 Emergency! I had an accident at sea",
    ],
  },
};

export const TOOL_LABELS = {
  get_sea_safety: { ml: "🌊 കടൽ നില പരിശോധിക്കുന്നു...", en: "🌊 Checking sea conditions..." },
  incois_scraper: { ml: "🛰️ INCOIS-ൽ നിന്ന് പുതിയ ഡാറ്റ ലഭ്യമാക്കുന്നു...", en: "🛰️ Fetching fresh INCOIS forecast..." },
  get_market_price: { ml: "💰 വിപണി വില പരിശോധിക്കുന്നു...", en: "💰 Checking fish prices..." },
  get_price_history: { ml: "📈 വില ചരിത്രം പരിശോധിക്കുന്നു...", en: "📈 Checking price history..." },
  get_scheme_info: { ml: "📋 പദ്ധതി വിവരങ്ങൾ ശേഖരിക്കുന്നു...", en: "📋 Searching support schemes..." },
};

export const LOCALE_MAP = { ml: "ml-IN", en: "en-IN" };
