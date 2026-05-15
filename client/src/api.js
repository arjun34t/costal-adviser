import { API_BASE } from "./constants.js";

export async function* parseSSE(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventType = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ") && eventType) {
        try {
          yield { type: eventType, data: JSON.parse(line.slice(6)) };
        } catch (_) {}
        eventType = null;
      }
    }
  }
}

export async function fetchAllLocations() {
  const res = await fetch(`${API_BASE}/location/all`);
  if (!res.ok) throw new Error("Failed to fetch locations");
  const data = await res.json();
  return data.locations || [];
}

export async function searchLocations(query) {
  const res = await fetch(`${API_BASE}/location/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error("Search failed");
  const data = await res.json();
  return data.matches || [];
}

export async function resolveLocation(loc) {
  try {
    const matches = await searchLocations(loc);
    const match = matches[0];
    if (!match) return { location: loc, district: null };
    const parsed = match.match(/^(.+?)\s+\((.+?)\)$/);
    return parsed ? { location: parsed[1], district: parsed[2] } : { location: loc, district: null };
  } catch (_) {
    return { location: loc, district: null };
  }
}

export async function streamChat({ message, district, language, history }) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, district: district || "", language, history }),
  });
  if (!res.ok) throw new Error(`Chat API error ${res.status}`);
  return res;
}

export async function transcribeAudio(blob, ext, language) {
  const formData = new FormData();
  formData.append("audio", blob, `recording.${ext}`);
  formData.append("language", language);
  const res = await fetch(`${API_BASE}/voice/transcribe`, {
    method: "POST",
    body: formData,
  });
  const json = await res.json();
  if (!res.ok) throw new Error(`Transcription error ${res.status}: ${json.detail || JSON.stringify(json)}`);
  return json;
}

export async function synthesizeSpeech(text, language = "ml") {
  const res = await fetch(`${API_BASE}/voice/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });
  if (!res.ok) throw new Error("TTS failed");
  return res.blob();
}

export async function translateText(text, target = "ml") {
  const res = await fetch(`${API_BASE}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, target }),
  });
  if (!res.ok) throw new Error("Translation failed");
  return res.json();
}

export async function fetchKeyInfo() {
  const res = await fetch(`${API_BASE}/settings/key-info`);
  if (!res.ok) throw new Error("Failed to fetch key info");
  return res.json();
}

export async function updateKey(sarvam_api_key) {
  const res = await fetch(`${API_BASE}/settings/update-key`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sarvam_api_key }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.detail || "Failed to update key");
  return json;
}

export async function revertKey() {
  const res = await fetch(`${API_BASE}/settings/revert-key`, { method: "POST" });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.detail || "Failed to revert key");
  return json;
}
