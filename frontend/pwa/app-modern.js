// CHANGE THIS: Put your deployed backend URL here (e.g., "https://my-backend-app.vercel.app")
// If your frontend and backend are deployed together in the SAME project, you can just use "" or "/api"
const PROD_API_BASE = "/api";

const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? "http://localhost:8000"
  : PROD_API_BASE;
const HISTORY_KEY = "fisher_chat_history";
const MAX_HISTORY = 50;

const TOOL_LABELS = {
  get_sea_safety: { ml: "🌊 കടൽ നില പരിശോധിക്കുന്നു...", en: "🌊 Checking sea conditions..." },
  incois_scraper: { ml: "🛰️ INCOIS-ൽ നിന്ന് പുതിയ ഡാറ്റ ലഭ്യമാക്കുന്നു...", en: "🛰️ Fetching fresh INCOIS forecast..." },
  get_market_price: { ml: "💰 വിപണി വില പരിശോധിക്കുന്നു...", en: "💰 Checking fish prices..." },
  get_price_history: { ml: "📈 വില ചരിത്രം പരിശോധിക്കുന്നു...", en: "📈 Checking price history..." },
  get_scheme_info: { ml: "📋 പദ്ധതി വിവരങ്ങൾ ശേഖരിക്കുന്നു...", en: "📋 Searching support schemes..." },
};

const LABELS = {
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
    moreResults: count => `${count} കൂടുതൽ ഫലങ്ങൾ - കൂടുതൽ തിരയാൻ ടൈപ്പ് ചെയ്യുക`,
    districtText: district => `${district} ജില്ല`,
    quickActions: [
      "ഇന്ന് കടലിൽ പോകാൻ സുരക്ഷിതമാണോ?",
      "ഇന്ന് മീൻ വില എന്താണ്?",
      "എനിക്ക് ലഭിക്കാവുന്ന സർക്കാർ പദ്ധതികൾ എന്തൊക്കെയാണ്?",
      "🆘 കടലിൽ അപകടം ഉണ്ടായി"
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
    moreResults: count => `${count} more results - type to narrow down`,
    districtText: district => `${district} district`,
    quickActions: [
      "Is it safe to go fishing today?",
      "What are today's fish prices?",
      "Which government schemes can I use?",
      "🆘 Emergency! I had an accident at sea"
    ],
  },
};

let currentLang = localStorage.getItem("fisherLang") || "ml";
let audioEnabled = localStorage.getItem("audio_enabled") === "true";
let currentTheme = localStorage.getItem("fisherTheme") || "dark";
let mediaRecorder = null;
let audioChunks = [];
let selectedLocation = localStorage.getItem("fisherLocation") || null;
let selectedDistrict = localStorage.getItem("fisherDistrict") || null;
let pendingLocation = null;
let allLocations = [];
let messages = [];

const localeMap = { ml: "ml-IN", en: "en-IN" };

const chatWindow = document.getElementById("chatWindow");
const emptyState = document.getElementById("emptyState");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const langSelect = document.getElementById("langSelect");
const recordingOverlay = document.getElementById("recordingOverlay");
const stopRecordBtn = document.getElementById("stopRecordBtn");
const audioToggle = document.getElementById("audioToggle");
const audioIcon = document.getElementById("audioIcon");
const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");
const locationDisplay = document.getElementById("locationDisplay");
const districtDisplay = document.getElementById("districtDisplay");
const locationMeta = document.getElementById("locationMeta");
const languageStatus = document.getElementById("languageStatus");  // may be null
const audioStatus = document.getElementById("audioStatus");          // may be null
const messageCount = document.getElementById("messageCount");        // may be null
const searchLocationBtn = document.getElementById("searchLocationBtn");
const quickActions = document.getElementById("quickActions");
const locationModal = document.getElementById("locationModal");
const closeLocationModal = document.getElementById("closeLocationModal");
const settingsModal = document.getElementById("settingsModal");
const settingsBtn = document.getElementById("settingsBtn");
const closeSettingsModal = document.getElementById("closeSettingsModal");
const sarvamKeyInput = document.getElementById("sarvamKeyInput");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");
const cancelSettingsBtn = document.getElementById("cancelSettingsBtn");
const revertKeyBtn = document.getElementById("revertKeyBtn");
const settingsStatus = document.getElementById("settingsStatus");
const keyStatusDot = document.getElementById("keyStatusDot");
const keyStatusLabel = document.getElementById("keyStatusLabel");
const locationSearch = document.getElementById("locationSearch");
const locationList = document.getElementById("locationList");
const locationConfirm = document.getElementById("locationConfirm");
const locationConfirmText = document.getElementById("locationConfirmText");
const confirmLocationBtn = document.getElementById("confirmLocationBtn");
const changeLocationBtn = document.getElementById("changeLocationBtn");
const clearChatBtn = document.getElementById("clearChatBtn");
const composerHint = document.querySelector(".composer-hint");

function getLabels() {
  return LABELS[currentLang];
}

function scrollChat() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function hideEmpty() {
  emptyState.classList.add("hidden");
}

function showEmpty() {
  if (messages.length === 0) {
    emptyState.classList.remove("hidden");
  }
}

function formatTime(timestamp) {
  const date = timestamp ? new Date(timestamp) : new Date();
  return new Intl.DateTimeFormat(localeMap[currentLang], {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function autosizeInput() {
  textInput.style.height = "auto";
  textInput.style.height = `${Math.min(textInput.scrollHeight, 180)}px`;
}

function updateSendState() {
  sendBtn.disabled = !textInput.value.trim();
}

function updateStatusIndicators() {
  const L = getLabels();
  if (languageStatus) languageStatus.textContent = L.languageName;
  if (audioStatus) audioStatus.textContent = audioEnabled ? L.audioOn : L.audioOff;
  if (messageCount) messageCount.textContent = String(messages.length);
}

function updateLocationDisplay() {
  const L = getLabels();
  if (selectedLocation) {
    locationDisplay.textContent = selectedLocation;
    districtDisplay.textContent = selectedDistrict ? L.districtText(selectedDistrict) : L.districtUnset;
    locationMeta.textContent = selectedDistrict ? `${selectedLocation} · ${selectedDistrict}` : selectedLocation;
  } else {
    locationDisplay.textContent = L.locationUnset;
    districtDisplay.textContent = L.districtUnset;
    locationMeta.textContent = L.locationMetaUnset;
  }
}

function applyLanguage(lang) {
  currentLang = lang;
  localStorage.setItem("fisherLang", lang);

  if (langSelect) langSelect.value = lang;

  // For data-ml / data-en attributes, use the matching lang or fall back to English
  document.querySelectorAll("[data-ml][data-en]").forEach(el => {
    el.textContent = el.dataset[lang] || el.dataset.en;
  });

  document.querySelectorAll("[data-ml-placeholder][data-en-placeholder]").forEach(el => {
    el.placeholder = el.dataset[lang + "Placeholder"] || el.dataset.enPlaceholder;
  });

  document.querySelectorAll("[data-ml-title][data-en-title]").forEach(el => {
    el.title = el.dataset[lang + "Title"] || el.dataset.enTitle;
  });

  const L = getLabels();
  if (textInput) textInput.placeholder = L.inputPlaceholder;
  if (locationSearch) locationSearch.placeholder = L.searchPlaceholder;
  const recOverlayP = document.querySelector("#recordingOverlay p");
  if (recOverlayP) recOverlayP.textContent = L.recordingText;
  if (stopRecordBtn) stopRecordBtn.textContent = L.stopBtn;
  if (composerHint) composerHint.textContent = L.composerHint;

  renderQuickActions();
  updateLocationDisplay();
  updateStatusIndicators();
}

function applyAudio(enabled) {
  audioEnabled = enabled;
  localStorage.setItem("audio_enabled", String(enabled));
  audioIcon.textContent = enabled ? "🔊" : "🔇";
  audioToggle.classList.toggle("audio-on", enabled);
  updateStatusIndicators();
}

function applyTheme(theme) {
  currentTheme = theme;
  localStorage.setItem("fisherTheme", theme);
  document.documentElement.setAttribute("data-theme", theme);
  if (themeIcon) {
    themeIcon.textContent = theme === "light" ? "🌙" : "☀️";
  }
}

function appendNotice(text, className = "lang-divider-chat") {
  hideEmpty();
  const note = document.createElement("div");
  note.className = className;
  note.textContent = text;
  chatWindow.appendChild(note);
  scrollChat();
  return note;
}

function appendBubble(role, text, audioBlob = null, timestamp = new Date().toISOString()) {
  hideEmpty();

  const L = getLabels();
  const row = document.createElement("div");
  const bubble = document.createElement("article");
  const header = document.createElement("div");
  const label = document.createElement("span");
  const time = document.createElement("time");
  const body = document.createElement("div");

  const isUser = role === "user";

  row.className = `message-row ${isUser ? "user" : "bot"}`;
  bubble.className = "bubble";
  header.className = "message-header";
  label.className = "message-label";
  time.className = "message-time";
  body.className = "bubble-body";

  label.textContent = isUser ? L.userLabel : L.agentLabel;
  time.textContent = formatTime(timestamp);
  body.textContent = text;

  header.append(label, time);
  bubble.append(header, body);

  if (audioBlob) {
    const url = URL.createObjectURL(audioBlob);
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.autoplay = true;
    audio.src = url;
    bubble.appendChild(audio);
  }

  row.appendChild(bubble);
  chatWindow.appendChild(row);
  scrollChat();
}

function showTyping() {
  hideEmpty();
  const row = document.createElement("div");
  row.className = "message-row bot";
  row.id = "typingIndicator";

  const indicator = document.createElement("div");
  indicator.className = "typing-bubble";
  indicator.innerHTML = "<span></span><span></span><span></span>";

  row.appendChild(indicator);
  chatWindow.appendChild(row);
  scrollChat();
  return row;
}

function removeTyping() {
  const el = document.getElementById("typingIndicator");
  if (el) {
    el.remove();
  }
}

function showToolBadge(toolName) {
  const labels = TOOL_LABELS[toolName] || { ml: "🔍 പ്രവർത്തിക്കുന്നു...", en: "🔍 Working..." };
  return appendNotice(labels[currentLang] || labels.en, "tool-badge");
}

function renderQuickActions() {
  const L = getLabels();
  quickActions.innerHTML = "";
  L.quickActions.forEach(prompt => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-action";
    button.textContent = prompt;
    button.addEventListener("click", () => sendMessage(prompt));
    quickActions.appendChild(button);
  });
}

function saveConversation() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(messages.slice(-MAX_HISTORY)));
  } catch (_) {
    // Ignore storage failures and keep runtime state.
  }
}

function loadConversation() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) {
      showEmpty();
      return;
    }

    const history = JSON.parse(raw);
    if (!Array.isArray(history) || history.length === 0) {
      showEmpty();
      return;
    }

    messages = history;
    history.forEach(msg => {
      appendBubble(msg.role === "user" ? "user" : "agent", msg.text, null, msg.timestamp);
    });
  } catch (_) {
    localStorage.removeItem(HISTORY_KEY);
    messages = [];
  }

  showEmpty();
  updateStatusIndicators();
}

function clearConversation() {
  localStorage.removeItem(HISTORY_KEY);
  messages = [];
  chatWindow.querySelectorAll(".message-row, .typing-bubble, .tool-badge, .lang-divider-chat").forEach(el => el.remove());
  updateStatusIndicators();
  showEmpty();
}

function setLocation(name, district) {
  selectedLocation = name;
  selectedDistrict = district || null;
  localStorage.setItem("fisherLocation", name);

  if (district) {
    localStorage.setItem("fisherDistrict", district);
  } else {
    localStorage.removeItem("fisherDistrict");
  }

  updateLocationDisplay();
}

function showLocationConfirmation(name, district) {
  const L = getLabels();
  locationConfirmText.textContent = district ? `${name} · ${L.districtText(district)}` : name;
  locationList.classList.add("hidden");
  locationConfirm.classList.remove("hidden");
  locationModal.classList.remove("hidden");
}

async function loadAllLocations() {
  if (allLocations.length > 0) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/location/all`);
    if (res.ok) {
      const data = await res.json();
      allLocations = data.locations || [];
    }
  } catch (_) {
    // Non-fatal. Search fallback still works with empty data.
  }
}

async function resolveLocation(loc) {
  try {
    const res = await fetch(`${API_BASE}/location/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: loc }),
    });

    if (!res.ok) {
      return { location: loc, district: null };
    }

    const data = await res.json();
    const match = (data.matches || [])[0];
    if (!match) {
      return { location: loc, district: null };
    }

    const parsed = match.match(/^(.+?)\s+\((.+?)\)$/);
    return parsed ? { location: parsed[1], district: parsed[2] } : { location: loc, district: null };
  } catch (_) {
    return { location: loc, district: null };
  }
}

function renderLocationList(locations) {
  locationList.innerHTML = "";

  const slice = locations.slice(0, 60);
  slice.forEach(loc => {
    const item = document.createElement("div");
    item.className = "location-item";
    item.textContent = loc;
    item.addEventListener("click", async () => {
      pendingLocation = await resolveLocation(loc);
      showLocationConfirmation(pendingLocation.location, pendingLocation.district);
    });
    locationList.appendChild(item);
  });

  if (locations.length > 60) {
    const hint = document.createElement("div");
    hint.className = "location-hint";
    hint.textContent = getLabels().moreResults(locations.length - 60);
    locationList.appendChild(hint);
  }
}

function localSearchLocations(query) {
  const q = query.toLowerCase();

  return allLocations
    .map(loc => {
      const value = loc.toLowerCase();
      let score = 0;
      if (value === q) score = 100;
      else if (value.startsWith(q)) score = 80;
      else if (value.includes(q)) score = 40;
      return { loc, score };
    })
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score || a.loc.localeCompare(b.loc))
    .map(item => item.loc);
}

async function showLocationPicker() {
  await loadAllLocations();
  locationSearch.value = "";
  locationConfirm.classList.add("hidden");
  locationList.classList.remove("hidden");
  renderLocationList(allLocations);
  locationModal.classList.remove("hidden");
  locationSearch.focus();
}


async function* parseSSE(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventType = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ") && eventType) {
        try {
          yield { type: eventType, data: JSON.parse(line.slice(6)) };
        } catch (_) {
          // Ignore malformed SSE payloads.
        }
        eventType = null;
      }
    }
  }
}

function buildRecentHistory(limit = 6) {
  return messages
    .slice(-limit)
    .map(msg => ({
      role: msg.role === "user" ? "user" : "assistant",
      content: msg.text,
    }));
}

async function sendMessage(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return;
  }

  const recentHistory = buildRecentHistory();

  textInput.value = "";
  autosizeInput();
  updateSendState();

  const userTimestamp = new Date().toISOString();
  appendBubble("user", trimmed, null, userTimestamp);
  messages.push({ role: "user", text: trimmed, timestamp: userTimestamp, language: currentLang });
  saveConversation();
  updateStatusIndicators();

  showTyping();
  let toolBadges = [];

  try {
    const chatRes = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: trimmed,
        district: selectedDistrict || "",
        language: currentLang,
        history: recentHistory,
      }),
    });

    if (!chatRes.ok) {
      throw new Error(`Chat API error ${chatRes.status}`);
    }

    removeTyping();
    let response = null;
    const toolBadges = [];

    for await (const event of parseSSE(chatRes)) {
      if (event.type === "tool_call") {
        toolBadges.push(showToolBadge(event.data.tool));
      } else if (event.type === "message") {
        response = event.data.response;
      }
    }

    toolBadges.forEach(b => b.remove());

    if (!response) {
      throw new Error("No response received");
    }

    let audioBlob = null;
    if (audioEnabled) {
      try {
        let ttsText = response;

        if (currentLang === "en") {
          const transRes = await fetch(`${API_BASE}/translate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: response, target: "ml" }),
          });

          if (transRes.ok) {
            const { translated } = await transRes.json();
            ttsText = translated || response;
          }
        }

        const ttsRes = await fetch(`${API_BASE}/voice/synthesize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: ttsText }),
        });

        if (ttsRes.ok) {
          audioBlob = await ttsRes.blob();
        }
      } catch (_) {
        // TTS failure should not block the main response.
      }
    }

    const answerTimestamp = new Date().toISOString();
    appendBubble("agent", response, audioBlob, answerTimestamp);
    messages.push({ role: "agent", text: response, timestamp: answerTimestamp, language: currentLang });
    saveConversation();
    updateStatusIndicators();
  } catch (err) {
    removeTyping();
    toolBadges.forEach(b => b.remove());
    toolBadges = [];

    const errorText = `⚠️ ${getLabels().errorPrefix}: ${err.message}`;
    const errorTimestamp = new Date().toISOString();
    appendBubble("agent", errorText, null, errorTimestamp);
    messages.push({ role: "agent", text: errorText, timestamp: errorTimestamp, language: currentLang });
    saveConversation();
    updateStatusIndicators();
  }
}

langSelect.addEventListener("change", () => {
  applyLanguage(langSelect.value);
  appendNotice(getLabels().switched);
});

audioToggle.addEventListener("click", () => {
  applyAudio(!audioEnabled);
  const ripple = document.createElement("span");
  ripple.className = "ripple-effect";
  audioToggle.appendChild(ripple);
  ripple.addEventListener("animationend", () => ripple.remove());
});

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    applyTheme(currentTheme === "light" ? "dark" : "light");
    const ripple = document.createElement("span");
    ripple.className = "ripple-effect";
    themeToggle.appendChild(ripple);
    ripple.addEventListener("animationend", () => ripple.remove());
  });
}

sendBtn.addEventListener("click", () => sendMessage(textInput.value));

textInput.addEventListener("input", () => {
  autosizeInput();
  updateSendState();
});

textInput.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage(textInput.value);
  }
});

micBtn.addEventListener("click", async () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];

    // Pick the best supported MIME type; fall back to browser default
    const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"]
      .find(t => MediaRecorder.isTypeSupported(t)) || "";
    mediaRecorder = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream);

    const recordedMime = mediaRecorder.mimeType || "audio/webm";
    const ext = recordedMime.includes("ogg") ? "ogg" : "webm";

    // Collect data every 250 ms so chunks are never empty on short recordings
    mediaRecorder.ondataavailable = event => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(track => track.stop());
      recordingOverlay.classList.add("hidden");
      micBtn.classList.remove("recording");

      const blob = new Blob(audioChunks, { type: recordedMime });
      console.log("[Mic] chunks:", audioChunks.length, "size:", blob.size, "type:", blob.type);

      if (blob.size < 100) {
        appendBubble("agent", "⚠️ No audio captured. Check microphone permissions.");
        return;
      }

      showTyping();

      try {
        const formData = new FormData();
        formData.append("audio", blob, `recording.${ext}`);
        formData.append("language", currentLang);

        const res = await fetch(`${API_BASE}/voice/transcribe`, {
          method: "POST",
          body: formData,
        });

        const json = await res.json();
        console.log("[Mic] response:", res.status, json);
        removeTyping();

        if (!res.ok) {
          appendBubble("agent", `⚠️ Transcription error ${res.status}: ${json.detail || JSON.stringify(json)}`);
          return;
        }

        if (json.transcript) {
          sendMessage(json.transcript);
        } else {
          appendBubble("agent", getLabels().transcriptionFailed);
        }
      } catch (err) {
        removeTyping();
        console.error("[Mic] Error:", err);
        appendBubble("agent", `⚠️ ${err.message}`);
      }
    };

    mediaRecorder.start(250);  // fire ondataavailable every 250 ms
    micBtn.classList.add("recording");
    recordingOverlay.classList.remove("hidden");
  } catch (_) {
    appendBubble("agent", getLabels().micDenied);
  }
});

stopRecordBtn.addEventListener("click", () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }
});

confirmLocationBtn.addEventListener("click", () => {
  if (pendingLocation) {
    setLocation(pendingLocation.location, pendingLocation.district);
    pendingLocation = null;
  }

  locationModal.classList.add("hidden");
  locationConfirm.classList.add("hidden");
  locationList.classList.remove("hidden");
});

changeLocationBtn.addEventListener("click", () => {
  pendingLocation = null;
  locationConfirm.classList.add("hidden");
  locationList.classList.remove("hidden");
  locationSearch.value = "";
  renderLocationList(allLocations);
});

let searchTimer = null;
locationSearch.addEventListener("input", () => {
  clearTimeout(searchTimer);
  const query = locationSearch.value.trim();

  if (!query) {
    renderLocationList(allLocations);
    return;
  }

  searchTimer = setTimeout(async () => {
    try {
      const res = await fetch(`${API_BASE}/location/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (res.ok) {
        const data = await res.json();
        const names = (data.matches || []).map(match => {
          const parsed = match.match(/^(.+?)\s+\((.+?)\)$/);
          return parsed ? parsed[1] : match;
        });
        renderLocationList(names.length ? names : localSearchLocations(query));
      }
    } catch (_) {
      renderLocationList(localSearchLocations(query));
    }
  }, 150);
});

searchLocationBtn.addEventListener("click", showLocationPicker);
closeLocationModal.addEventListener("click", () => {
  locationModal.classList.add("hidden");
  pendingLocation = null;
});
clearChatBtn.addEventListener("click", clearConversation);

// ── Settings modal ───────────────────────────────────────────────────
async function loadKeyInfo() {
  try {
    const res = await fetch(`${API_BASE}/settings/key-info`);
    if (!res.ok) return;
    const info = await res.json();
    if (!info.has_key) {
      keyStatusDot.style.background = "#e53e3e";
      keyStatusLabel.textContent = currentLang === "ml" ? "കീ ഇല്ല" : "No key set";
      revertKeyBtn.style.display = "none";
    } else if (info.is_original) {
      keyStatusDot.style.background = "#38a169";
      keyStatusLabel.textContent = currentLang === "ml" ? "ഡെവലപ്പർ കീ ഉപയോഗിക്കുന്നു" : "Using Developer's Key";
      revertKeyBtn.style.display = "none";
    } else {
      keyStatusDot.style.background = "#d69e2e";
      keyStatusLabel.textContent = currentLang === "ml" ? "നിങ്ങളുടെ കീ ഉപയോഗിക്കുന്നു" : "Using Your Key";
      revertKeyBtn.style.display = "";
    }
  } catch (_) {}
}

settingsBtn.addEventListener("click", () => {
  sarvamKeyInput.value = "";
  settingsStatus.textContent = "";
  settingsModal.classList.remove("hidden");
  loadKeyInfo();
  sarvamKeyInput.focus();
});

function closeSettings() {
  settingsModal.classList.add("hidden");
}
closeSettingsModal.addEventListener("click", closeSettings);
cancelSettingsBtn.addEventListener("click", closeSettings);
settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) closeSettings();
});

saveSettingsBtn.addEventListener("click", async () => {
  const key = sarvamKeyInput.value.trim();
  if (!key) {
    settingsStatus.style.color = "var(--error, #e53e3e)";
    settingsStatus.textContent = currentLang === "ml" ? "കീ ഒഴിഞ്ഞിരിക്കരുത്." : "Key cannot be empty.";
    return;
  }
  saveSettingsBtn.disabled = true;
  settingsStatus.style.color = "inherit";
  settingsStatus.textContent = currentLang === "ml" ? "സേവ് ചെയ്യുന്നു…" : "Saving…";
  try {
    const res = await fetch(`${API_BASE}/settings/update-key`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sarvam_api_key: key }),
    });
    if (res.ok) {
      settingsStatus.style.color = "var(--success, #38a169)";
      settingsStatus.textContent = currentLang === "ml" ? "✓ സേവ് ചെയ്തു." : "✓ Saved.";
      await loadKeyInfo();
      sarvamKeyInput.value = "";
      setTimeout(closeSettings, 1200);
    } else {
      const err = await res.json().catch(() => ({}));
      settingsStatus.style.color = "var(--error, #e53e3e)";
      settingsStatus.textContent = err.detail || (currentLang === "ml" ? "പിശക് സംഭവിച്ചു." : "An error occurred.");
    }
  } catch (e) {
    settingsStatus.style.color = "var(--error, #e53e3e)";
    settingsStatus.textContent = currentLang === "ml" ? "സെർവറുമായി ബന്ധപ്പെടാൻ കഴിഞ്ഞില്ല." : "Could not reach server.";
  } finally {
    saveSettingsBtn.disabled = false;
  }
});

revertKeyBtn.addEventListener("click", async () => {
  revertKeyBtn.disabled = true;
  settingsStatus.style.color = "inherit";
  settingsStatus.textContent = currentLang === "ml" ? "മടങ്ങുന്നു…" : "Reverting…";
  try {
    const res = await fetch(`${API_BASE}/settings/revert-key`, { method: "POST" });
    if (res.ok) {
      settingsStatus.style.color = "var(--success, #38a169)";
      settingsStatus.textContent = currentLang === "ml" ? "✓ ഡെവലപ്പർ കീ ഉപയോഗിക്കുന്നു." : "✓ Switched to Developer's Key.";
      await loadKeyInfo();
      setTimeout(closeSettings, 1200);
    } else {
      const err = await res.json().catch(() => ({}));
      settingsStatus.style.color = "var(--error, #e53e3e)";
      settingsStatus.textContent = err.detail || (currentLang === "ml" ? "പിശക് സംഭവിച്ചു." : "An error occurred.");
    }
  } catch (_) {
    settingsStatus.style.color = "var(--error, #e53e3e)";
    settingsStatus.textContent = currentLang === "ml" ? "സെർവറുമായി ബന്ധപ്പെടാൻ കഴിഞ്ഞില്ല." : "Could not reach server.";
  } finally {
    revertKeyBtn.disabled = false;
  }
});

applyLanguage(currentLang);
applyAudio(audioEnabled);
applyTheme(currentTheme);
updateLocationDisplay();
renderQuickActions();
loadConversation();
autosizeInput();
updateSendState();
