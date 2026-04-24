import React, { useRef, useEffect, useState, useCallback } from "react";
import { useApp } from "../context/AppContext.jsx";
import { fetchKeyInfo, updateKey, revertKey } from "../api.js";

const LOG_COLORS = {
  user:     "#7dd3fc", // sky blue
  system:   "#a3a3a3", // muted gray
  tool:     "#fbbf24", // amber
  result:   "#34d399", // emerald
  response: "#a78bfa", // violet
  error:    "#f87171", // red
};

const LOG_PREFIX = {
  user:     "USER   ",
  system:   "SYS    ",
  tool:     "CALL   ",
  result:   "DATA   ",
  response: "LLM    ",
  error:    "ERROR  ",
};

export default function DevPanel({ onClose }) {
  const { devLogs, clearDevLogs, lang } = useApp();
  const logRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // API key state
  const [sarvamKey, setSarvamKey] = useState("");
  const [keyInfo, setKeyInfo] = useState(null);
  const [statusText, setStatusText] = useState("");
  const [statusColor, setStatusColor] = useState("inherit");
  const [saving, setSaving] = useState(false);
  const [reverting, setReverting] = useState(false);

  const loadKey = useCallback(async () => {
    try {
      const info = await fetchKeyInfo();
      setKeyInfo(info);
    } catch (_) {}
  }, []);

  useEffect(() => { loadKey(); }, [loadKey]);

  // Auto-scroll terminal
  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [devLogs, autoScroll]);

  function handleScroll() {
    if (!logRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logRef.current;
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 40);
  }

  async function handleSave() {
    const key = sarvamKey.trim();
    if (!key) { setStatusColor("#f87171"); setStatusText("Key cannot be empty."); return; }
    setSaving(true);
    setStatusColor("inherit");
    setStatusText("Saving…");
    try {
      await updateKey(key);
      setStatusColor("#34d399");
      setStatusText("✓ Saved.");
      await loadKey();
      setSarvamKey("");
    } catch (err) {
      setStatusColor("#f87171");
      setStatusText(err.message || "Error saving key.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRevert() {
    setReverting(true);
    setStatusColor("inherit");
    setStatusText("Reverting…");
    try {
      await revertKey();
      setStatusColor("#34d399");
      setStatusText("✓ Switched to Developer's Key.");
      await loadKey();
    } catch (err) {
      setStatusColor("#f87171");
      setStatusText(err.message || "Could not reach server.");
    } finally {
      setReverting(false);
    }
  }

  let keyDot = "#e53e3e";
  let keyLabel = "No key set";
  let showRevert = false;
  if (keyInfo) {
    if (!keyInfo.has_key) {
      keyDot = "#e53e3e"; keyLabel = "No key set";
    } else if (keyInfo.is_original) {
      keyDot = "#34d399"; keyLabel = "Developer's Key active";
    } else {
      keyDot = "#fbbf24"; keyLabel = "Your Key active";
      showRevert = true;
    }
  }

  return (
    <div className="dev-panel">
      {/* Header */}
      <div className="dev-panel-header">
        <div className="dev-panel-title">
          <span className="dev-panel-icon">&lt;/&gt;</span>
          <span>Developer Console</span>
          <span className="dev-panel-badge">{devLogs.length}</span>
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            className="dev-btn-sm"
            onClick={clearDevLogs}
            title="Clear logs"
          >
            CLR
          </button>
          <button
            className="dev-btn-sm"
            onClick={onClose}
            title="Close"
            style={{ color: "#f87171" }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Terminal log */}
      <div
        className="dev-terminal"
        ref={logRef}
        onScroll={handleScroll}
      >
        {devLogs.length === 0 ? (
          <div className="dev-empty">Send a message to see the agent trace here.</div>
        ) : (
          devLogs.map((log, i) => (
            <div key={i} className="dev-log-line">
              <span className="dev-log-time">{log.time}</span>
              <span
                className="dev-log-type"
                style={{ color: LOG_COLORS[log.type] || "#a3a3a3" }}
              >
                {LOG_PREFIX[log.type] || "       "}
              </span>
              <span
                className="dev-log-text"
                style={{ color: log.type === "user" ? "#e5e5e5" : LOG_COLORS[log.type] || "#a3a3a3" }}
              >
                {log.text}
              </span>
            </div>
          ))
        )}
        {!autoScroll && (
          <button
            className="dev-scroll-btn"
            onClick={() => {
              setAutoScroll(true);
              if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
            }}
          >
            ↓ Jump to bottom
          </button>
        )}
      </div>

      {/* API Key section */}
      <div className="dev-api-section">
        <div className="dev-api-title">
          <span style={{ opacity: 0.5, fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.1em" }}>
            Sarvam API Key
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: keyDot, display: "inline-block", flexShrink: 0 }} />
            <span style={{ fontSize: "0.75rem", color: "#a3a3a3" }}>{keyLabel}</span>
          </span>
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          <input
            type="password"
            className="dev-key-input"
            placeholder="Enter Sarvam API key…"
            value={sarvamKey}
            onChange={(e) => setSarvamKey(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSave(); }}
          />
          <button
            className="dev-btn-action"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "…" : "SET"}
          </button>
          {showRevert && (
            <button
              className="dev-btn-action"
              style={{ color: "#34d399", borderColor: "#34d399" }}
              onClick={handleRevert}
              disabled={reverting}
              title="Switch back to Developer's Key"
            >
              {reverting ? "…" : "DEV"}
            </button>
          )}
        </div>
        {statusText && (
          <p style={{ margin: "4px 0 0", fontSize: "0.75rem", color: statusColor }}>{statusText}</p>
        )}
      </div>
    </div>
  );
}
