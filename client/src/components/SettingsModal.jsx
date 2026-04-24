import React, { useState, useEffect, useCallback } from "react";
import { useApp } from "../context/AppContext.jsx";
import { fetchKeyInfo, updateKey, revertKey } from "../api.js";

export default function SettingsModal({ onClose }) {
  const { lang } = useApp();
  const [sarvamKey, setSarvamKey] = useState("");
  const [statusText, setStatusText] = useState("");
  const [statusColor, setStatusColor] = useState("inherit");
  const [keyInfo, setKeyInfo] = useState(null);
  const [saving, setSaving] = useState(false);
  const [reverting, setReverting] = useState(false);

  const loadKey = useCallback(async () => {
    try {
      const info = await fetchKeyInfo();
      setKeyInfo(info);
    } catch (_) {}
  }, []);

  useEffect(() => {
    loadKey();
  }, [loadKey]);

  async function handleSave() {
    const key = sarvamKey.trim();
    if (!key) {
      setStatusColor("var(--error, #e53e3e)");
      setStatusText(lang === "ml" ? "കീ ഒഴിഞ്ഞിരിക്കരുത്." : "Key cannot be empty.");
      return;
    }
    setSaving(true);
    setStatusColor("inherit");
    setStatusText(lang === "ml" ? "സേവ് ചെയ്യുന്നു…" : "Saving…");
    try {
      await updateKey(key);
      setStatusColor("var(--success, #38a169)");
      setStatusText(lang === "ml" ? "✓ സേവ് ചെയ്തു." : "✓ Saved.");
      await loadKey();
      setSarvamKey("");
      setTimeout(onClose, 1200);
    } catch (err) {
      setStatusColor("var(--error, #e53e3e)");
      setStatusText(err.message || (lang === "ml" ? "പിശക് സംഭവിച്ചു." : "An error occurred."));
    } finally {
      setSaving(false);
    }
  }

  async function handleRevert() {
    setReverting(true);
    setStatusColor("inherit");
    setStatusText(lang === "ml" ? "മടങ്ങുന്നു…" : "Reverting…");
    try {
      await revertKey();
      setStatusColor("var(--success, #38a169)");
      setStatusText(lang === "ml" ? "✓ ഡെവലപ്പർ കീ ഉപയോഗിക്കുന്നു." : "✓ Switched to Developer's Key.");
      await loadKey();
      setTimeout(onClose, 1200);
    } catch (err) {
      setStatusColor("var(--error, #e53e3e)");
      setStatusText(err.message || (lang === "ml" ? "സെർവറുമായി ബന്ധപ്പെടാൻ കഴിഞ്ഞില്ല." : "Could not reach server."));
    } finally {
      setReverting(false);
    }
  }

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) onClose();
  }

  let keyDotColor = "#e53e3e";
  let keyStatusLabel = lang === "ml" ? "കീ ഇല്ല" : "No key set";
  let showRevert = false;
  if (keyInfo) {
    if (!keyInfo.has_key) {
      keyDotColor = "#e53e3e";
      keyStatusLabel = lang === "ml" ? "കീ ഇല്ല" : "No key set";
    } else if (keyInfo.is_original) {
      keyDotColor = "#38a169";
      keyStatusLabel = lang === "ml" ? "ഡെവലപ്പർ കീ ഉപയോഗിക്കുന്നു" : "Using Developer's Key";
    } else {
      keyDotColor = "#d69e2e";
      keyStatusLabel = lang === "ml" ? "നിങ്ങളുടെ കീ ഉപയോഗിക്കുന്നു" : "Using Your Key";
      showRevert = true;
    }
  }

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-card">
        <div className="modal-header">
          <div>
            <p className="modal-eyebrow">{lang === "ml" ? "ക്രമീകരണങ്ങൾ" : "Settings"}</p>
            <h3>{lang === "ml" ? "Sarvam API Key" : "Sarvam API Key"}</h3>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div style={{ padding: "0 22px 22px", display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                background: keyDotColor,
                display: "inline-block",
                flexShrink: 0,
              }}
            />
            <span style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>{keyStatusLabel}</span>
          </div>

          <input
            type="password"
            className="location-search-input"
            style={{ margin: 0 }}
            placeholder={lang === "ml" ? "നിങ്ങളുടെ Sarvam API Key ഇവിടെ ഇടുക" : "Enter your Sarvam API Key"}
            value={sarvamKey}
            onChange={(e) => setSarvamKey(e.target.value)}
            autoFocus
          />

          {statusText && (
            <p style={{ margin: 0, color: statusColor, fontSize: "0.9rem" }}>{statusText}</p>
          )}

          <div className="confirm-buttons">
            <button className="secondary-button confirm-no" onClick={onClose}>
              {lang === "ml" ? "റദ്ദാക്കുക" : "Cancel"}
            </button>
            {showRevert && (
              <button
                className="secondary-button"
                onClick={handleRevert}
                disabled={reverting}
              >
                {lang === "ml" ? "ഡെവലപ്പർ കീ" : "Use Dev Key"}
              </button>
            )}
            <button
              className="secondary-button confirm-yes"
              onClick={handleSave}
              disabled={saving}
            >
              {lang === "ml" ? "സേവ് ചെയ്യുക" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
