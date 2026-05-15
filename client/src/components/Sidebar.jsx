import React from "react";
import { useApp } from "../context/AppContext.jsx";
import { LABELS } from "../constants.js";

export default function Sidebar({ onOpenLocation, onClose }) {
  const { lang, selectedLocation, selectedDistrict, messages, clearMessages, sendMessage, addNotice } = useApp();
  const L = LABELS[lang];

  function handleClear() {
    clearMessages();
    addNotice(L.cleared);
  }

  const locationName = selectedLocation || L.locationUnset;
  const districtName = selectedDistrict ? L.districtText(selectedDistrict) : L.districtUnset;

  return (
    <aside className="sidebar-card">
      <button className="icon-button mobile-close-btn" onClick={onClose} aria-label="Close menu">
        ✕
      </button>
      <div className="sidebar-section">
        <div className="section-head">
          <h2>{lang === "ml" ? "സ്ഥലം" : "Location"}</h2>
          <span className="section-badge">📍</span>
        </div>
        <button className="location-summary" onClick={onOpenLocation} aria-label="Select location">
          <div className="location-icon">📍</div>
          <div className="location-text">
            <strong>{locationName}</strong>
            <small>{districtName}</small>
          </div>
        </button>
        <div className="sidebar-actions">
          <button className="secondary-button danger-button" onClick={handleClear}>
            {lang === "ml" ? "🗑 ചാറ്റ് മായ്ക്കുക" : "🗑 Clear Chat"}
          </button>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="section-head">
          <h2>{lang === "ml" ? "വേഗം ചോദിക്കുക" : "Quick Actions"}</h2>
        </div>
        <div className="quick-actions">
          {L.quickActions.map((prompt, i) => (
            <button
              key={i}
              className="quick-action"
              onClick={() => sendMessage(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
