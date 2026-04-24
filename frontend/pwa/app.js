// CHANGE THIS: Put your deployed backend URL here (e.g., "https://my-backend-app.vercel.app")
// If your frontend and backend are deployed together in the SAME project, you can just use "" or "/api"
const PROD_API_BASE = "/api";

const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? "http://localhost:8000"
  : PROD_API_BASE;

const TOOL_LABELS = {
  get_sea_safety:   { ml: "🌊 കടൽ നിലവാരം പരിശോധിക്കുന്നു...", en: "🌊 Checking sea conditions..." },
  get_market_price: { ml: "💰 വില പരിശോധിക്കുന്നു...",           en: "💰 Checking fish prices..."   },
  get_scheme_info:  { ml: "📋 പദ്ധതികൾ തിരയുന്നു...",            en: "📋 Searching schemes..."      },
};

// ── UI labels (ml / en) ──────────────────────────────────────────
const LABELS = {
  ml: {
    headerSub:        "കേരള മത്സ്യത്തൊഴിലാളി സഹായി",
    inputPlaceholder: "സന്ദേശം ടൈപ്പ് ചെയ്യുക…",
    emptyState:       "നിങ്ങളുടെ ചോദ്യം ടൈപ്പ് ചെയ്യുക അല്ലെങ്കിൽ സംസാരിക്കുക",
    recordingText:    "റെക്കോർഡ് ചെയ്യുന്നു…",
    stopBtn:          "നിർത്തുക",
  },
  en: {
    headerSub:        "Kerala Fishermen Assistant",
    inputPlaceholder: "Type your message…",
    emptyState:       "Type or speak your question below",
    recordingText:    "Recording…",
    stopBtn:          "Stop",
  },
};

// ── State ────────────────────────────────────────────────────────
let currentLang    = localStorage.getItem("fisherLang") || "ml";
let audioEnabled   = localStorage.getItem("audio_enabled") === "true";
let mediaRecorder  = null;
let audioChunks    = [];
let selectedLocation = localStorage.getItem("fisherLocation") || null;
let selectedDistrict = localStorage.getItem("fisherDistrict") || null;
let pendingLocation  = null;
let allLocations     = [];
let messages         = [];   // in-memory mirror of persisted chat history

// ── DOM refs ─────────────────────────────────────────────────────
const chatWindow         = document.getElementById("chatWindow");
const emptyState         = document.getElementById("emptyState");
const textInput          = document.getElementById("textInput");
const sendBtn            = document.getElementById("sendBtn");
const micBtn             = document.getElementById("micBtn");
const langToggle         = document.getElementById("langToggle");
const optMl              = document.getElementById("optMl");
const optEn              = document.getElementById("optEn");
const recordingOverlay   = document.getElementById("recordingOverlay");
const stopRecordBtn      = document.getElementById("stopRecordBtn");
const audioToggle        = document.getElementById("audioToggle");
const audioIcon          = document.getElementById("audioIcon");
const locationDisplay    = document.getElementById("locationDisplay");
const autoDetectBtn      = document.getElementById("autoDetectBtn");
const searchLocationBtn  = document.getElementById("searchLocationBtn");
const locationModal      = document.getElementById("locationModal");
const closeLocationModal = document.getElementById("closeLocationModal");
const locationSearch     = document.getElementById("locationSearch");
const locationList       = document.getElementById("locationList");
const locationConfirm    = document.getElementById("locationConfirm");
const locationConfirmText= document.getElementById("locationConfirmText");
const confirmLocationBtn = document.getElementById("confirmLocationBtn");
const changeLocationBtn  = document.getElementById("changeLocationBtn");
const clearChatBtn       = document.getElementById("clearChatBtn");

// ── Language toggle ──────────────────────────────────────────────
function applyLanguage(lang) {
  currentLang = lang;
  localStorage.setItem("fisherLang", lang);

  // Toggle pill highlights
  optMl.classList.toggle("active", lang === "ml");
  optEn.classList.toggle("active", lang === "en");

  const L = LABELS[lang];

  // Update all data-ml / data-en elements
  document.querySelectorAll("[data-ml]").forEach(el => {
    el.textContent = lang === "ml" ? el.dataset.ml : el.dataset.en;
  });

  // Placeholder
  textInput.placeholder = L.inputPlaceholder;

  // Recording overlay texts
  document.querySelector("#recordingOverlay p").textContent = L.recordingText;
  stopRecordBtn.textContent = L.stopBtn;
}

langToggle.addEventListener("click", () => {
  const newLang = currentLang === "ml" ? "en" : "ml";
  applyLanguage(newLang);

  // Show a chat divider so the user sees the switch took effect
  const divider = document.createElement("div");
  divider.className = "lang-divider-chat";
  divider.textContent = newLang === "en" ? "Switched to English" : "മലയാളത്തിലേക്ക് മാറി";
  chatWindow.appendChild(divider);
  chatWindow.scrollTop = chatWindow.scrollHeight;
});

// ── Audio toggle ─────────────────────────────────────────────────
function applyAudio(enabled) {
  audioEnabled = enabled;
  localStorage.setItem("audio_enabled", enabled);
  audioIcon.textContent = enabled ? "🔊" : "🔇";
  audioToggle.classList.toggle("audio-on", enabled);
  audioToggle.title = enabled ? "Disable voice response" : "Enable voice response";
}

audioToggle.addEventListener("click", () => {
  applyAudio(!audioEnabled);

  // Ripple effect
  const ripple = document.createElement("span");
  ripple.className = "ripple-effect";
  audioToggle.appendChild(ripple);
  ripple.addEventListener("animationend", () => ripple.remove());
});

// ── SSE stream parser ────────────────────────────────
async function* parseSSE(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventType = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // keep incomplete last line

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ") && eventType) {
        try { yield { type: eventType, data: JSON.parse(line.slice(6)) }; }
        catch (_) { /* malformed JSON, skip */ }
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

// ── Tool badge ───────────────────────────────────────
function showToolBadge(toolName) {
  const labels = TOOL_LABELS[toolName] || { ml: "🔍 ...", en: "🔍 ..." };
  const badge = document.createElement("div");
  badge.className = "tool-badge";
  badge.textContent = labels[currentLang] || labels.en;
  chatWindow.appendChild(badge);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return badge;
}

// ── Chat helpers ─────────────────────────────────────────────────
function hideEmpty() {
  emptyState.classList.add("hidden");
}

function appendBubble(role, text, audioBlob) {
  hideEmpty();
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

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
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return row;
}

function showTyping() {
  const indicator = document.createElement("div");
  indicator.className = "typing-bubble";
  indicator.id = "typingIndicator";
  indicator.innerHTML = "<span></span><span></span><span></span>";
  chatWindow.appendChild(indicator);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return indicator;
}

function removeTyping() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

// ── Send message ─────────────────────────────────────────────────
async function sendMessage(text) {
  if (!text.trim()) return;
  const recentHistory = buildRecentHistory();
  textInput.value = "";

  appendBubble("user", text);
  messages.push({ role: "user", text, timestamp: new Date().toISOString(), language: currentLang });
  saveConversation();
  const typing = showTyping();

  let toolBadges = [];

  try {
    const chatRes = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message:  text,
        district: selectedDistrict || "",
        language: currentLang,
        history: recentHistory,
      }),
    });

    if (!chatRes.ok) throw new Error(`Chat API error ${chatRes.status}`);

    removeTyping();

    let response = null;

    for await (const event of parseSSE(chatRes)) {
      if (event.type === "tool_call") {
        toolBadges.push(showToolBadge(event.data.tool));
      } else if (event.type === "message") {
        response = event.data.response;
      }
    }

    toolBadges.forEach(b => b.remove());
    toolBadges = [];
    if (!response) throw new Error("No response received");

    // TTS — tool badge label is never passed here, only the final response
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
      } catch (_) { /* TTS failure is non-fatal */ }
    }

    appendBubble("bot", response, audioBlob);
    // Store text only — audio blobs cannot be serialised to JSON
    messages.push({ role: "agent", text: response, timestamp: new Date().toISOString(), language: currentLang });
    saveConversation();
  } catch (err) {
    removeTyping();
    toolBadges.forEach(b => b.remove());
    toolBadges = [];
    const errText = `⚠️ Error: ${err.message}`;
    appendBubble("bot", errText);
    messages.push({ role: "agent", text: errText, timestamp: new Date().toISOString(), language: currentLang });
    saveConversation();
  }
}

sendBtn.addEventListener("click", () => sendMessage(textInput.value));

textInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage(textInput.value);
  }
});

// ── Voice recording ──────────────────────────────────────────────
micBtn.addEventListener("click", async () => {
  if (mediaRecorder && mediaRecorder.state === "recording") return;

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      recordingOverlay.classList.add("hidden");
      micBtn.classList.remove("recording");

      const blob = new Blob(audioChunks, { type: "audio/wav" });
      const formData = new FormData();
      formData.append("audio", blob, "recording.wav");

      const typing = showTyping();
      try {
        const res = await fetch(`${API_BASE}/voice/transcribe`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error("Transcription failed");
        const { transcript } = await res.json();
        removeTyping();
        if (transcript) {
          sendMessage(transcript);
        } else {
          appendBubble("bot", "⚠️ Could not transcribe audio. Please try again.");
        }
      } catch (err) {
        removeTyping();
        appendBubble("bot", `⚠️ ${err.message}`);
      }
    };

    mediaRecorder.start();
    micBtn.classList.add("recording");
    recordingOverlay.classList.remove("hidden");
  } catch (err) {
    appendBubble("bot", "⚠️ Microphone access denied.");
  }
});

stopRecordBtn.addEventListener("click", () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }
});

// ── Location display ─────────────────────────────────────────────
function updateLocationDisplay() {
  if (selectedLocation) {
    const district = selectedDistrict ? `, ${selectedDistrict} district` : "";
    locationDisplay.textContent = `📍 ${selectedLocation}${district}`;
  } else {
    const L = LABELS[currentLang];
    locationDisplay.dataset.ml = "📍 തീരദേശ സ്ഥലം തിരഞ്ഞെടുക്കുക";
    locationDisplay.dataset.en = "📍 Select coastal location";
    locationDisplay.textContent = currentLang === "ml"
      ? "📍 തീരദേശ സ്ഥലം തിരഞ്ഞെടുക്കുക"
      : "📍 Select coastal location";
  }
}

function setLocation(name, district) {
  selectedLocation = name;
  selectedDistrict = district || null;
  localStorage.setItem("fisherLocation", name);
  if (district) localStorage.setItem("fisherDistrict", district);
  else localStorage.removeItem("fisherDistrict");
  updateLocationDisplay();
}

// ── Auto-detect location ──────────────────────────────────────────
async function autoDetectLocation() {
  if (!navigator.geolocation) {
    appendBubble("bot", "⚠️ Geolocation is not supported by this browser.");
    return;
  }
  locationDisplay.textContent = "📍 Detecting…";
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const { latitude: lat, longitude: lng } = pos.coords;
      try {
        const res = await fetch(`${API_BASE}/location/detect`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lat, lng }),
        });
        if (!res.ok) throw new Error("Detection failed");
        const data = await res.json();
        pendingLocation = data;
        showLocationConfirmation(data.location, data.district);
      } catch (err) {
        appendBubble("bot", `⚠️ Location detection failed: ${err.message}`);
        updateLocationDisplay();
      }
    },
    (err) => {
      appendBubble("bot", "⚠️ Could not get GPS location. Please search manually.");
      updateLocationDisplay();
    }
  );
}

function showLocationConfirmation(name, district) {
  const districtPart = district ? `, ${district} district` : "";
  locationConfirmText.textContent = `${name}${districtPart}`;
  locationList.classList.add("hidden");
  locationConfirm.classList.remove("hidden");
  locationModal.classList.remove("hidden");
}

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

// ── Location picker (searchable dropdown) ────────────────────────
async function loadAllLocations() {
  if (allLocations.length > 0) return;
  try {
    const res = await fetch(`${API_BASE}/location/all`);
    if (res.ok) {
      const data = await res.json();
      allLocations = data.locations || [];
    }
  } catch (_) { /* non-fatal */ }
}

function renderLocationList(locations) {
  locationList.innerHTML = "";
  const slice = locations.slice(0, 60);
  slice.forEach(loc => {
    const item = document.createElement("div");
    item.className = "location-item";
    item.textContent = loc;
    item.addEventListener("click", async () => {
      // Resolve district via search endpoint
      try {
        const res = await fetch(`${API_BASE}/location/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: loc }),
        });
        if (res.ok) {
          const data = await res.json();
          const match = (data.matches || [])[0];
          if (match) {
            const m = match.match(/^(.+?)\s+\((.+?)\)$/);
            if (m) {
              pendingLocation = { location: m[1], district: m[2] };
              showLocationConfirmation(m[1], m[2]);
              return;
            }
          }
        }
      } catch (_) { /* fall through */ }
      pendingLocation = { location: loc, district: null };
      showLocationConfirmation(loc, null);
    });
    locationList.appendChild(item);
  });
  if (locations.length > 60) {
    const hint = document.createElement("div");
    hint.className = "location-hint";
    hint.textContent = `${locations.length - 60} more — type to filter`;
    locationList.appendChild(hint);
  }
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

// Client-side relevance fallback when API is unavailable
function localSearchLocations(q) {
  const ql = q.toLowerCase();
  const scored = allLocations.map(loc => {
    const ll = loc.toLowerCase();
    let score = 0;
    if (ll === ql) score = 100;
    else if (ll.startsWith(ql)) score = 80;
    else if (ll.includes(ql)) score = 40;
    return { loc, score };
  }).filter(x => x.score > 0);
  scored.sort((a, b) => b.score - a.score || a.loc.localeCompare(b.loc));
  return scored.map(x => x.loc);
}

let _searchTimer = null;
locationSearch.addEventListener("input", () => {
  clearTimeout(_searchTimer);
  const q = locationSearch.value.trim();
  if (!q) {
    renderLocationList(allLocations);
    return;
  }
  // Small debounce (150ms) to avoid flooding the server on fast typing
  _searchTimer = setTimeout(async () => {
    try {
      const res = await fetch(`${API_BASE}/location/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      if (res.ok) {
        const data = await res.json();
        const names = (data.matches || []).map(m => {
          const match = m.match(/^(.+?)\s+\((.+?)\)$/);
          return match ? match[1] : m;
        });
        renderLocationList(names.length ? names : localSearchLocations(q));
      }
    } catch (_) {
      renderLocationList(localSearchLocations(q));
    }
  }, 150);
});

autoDetectBtn.addEventListener("click", autoDetectLocation);
searchLocationBtn.addEventListener("click", showLocationPicker);
closeLocationModal.addEventListener("click", () => {
  locationModal.classList.add("hidden");
  pendingLocation = null;
});

// ── Chat persistence ──────────────────────────────────────────────
const HISTORY_KEY = "fisher_chat_history";
const MAX_HISTORY = 50;

function saveConversation() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(messages.slice(-MAX_HISTORY)));
  } catch (_) { /* storage full — non-fatal */ }
}

function loadConversation() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return;
    const history = JSON.parse(raw);
    if (!Array.isArray(history) || history.length === 0) return;
    messages = history;
    history.forEach(msg => {
      appendBubble(msg.role === "user" ? "user" : "bot", msg.text);
      // no audio on reload — blobs cannot be serialised
    });
    chatWindow.scrollTop = chatWindow.scrollHeight;
  } catch (_) {
    localStorage.removeItem(HISTORY_KEY); // corrupted — start fresh
  }
}

function clearConversation() {
  localStorage.removeItem(HISTORY_KEY);
  messages = [];
  chatWindow.querySelectorAll(
    ".message-row, .typing-bubble, .tool-badge, .lang-divider-chat"
  ).forEach(el => el.remove());
  emptyState.classList.remove("hidden");

  const divider = document.createElement("div");
  divider.className = "lang-divider-chat";
  divider.textContent = currentLang === "ml" ? "സംഭാഷണം മായ്ച്ചു" : "Conversation cleared";
  chatWindow.appendChild(divider);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  setTimeout(() => divider.remove(), 3000);
}

clearChatBtn.addEventListener("click", clearConversation);

// ── Init ─────────────────────────────────────────────────────────
applyLanguage(currentLang);
applyAudio(audioEnabled);
updateLocationDisplay();
loadConversation();
