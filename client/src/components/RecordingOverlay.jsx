import React from "react";
import { useApp } from "../context/AppContext.jsx";
import { LABELS } from "../constants.js";

export default function RecordingOverlay({ onStop }) {
  const { lang } = useApp();
  const L = LABELS[lang];

  return (
    <div className="recording-overlay">
      <div className="recording-card">
        <div className="recording-pulse" />
        <p>{L.recordingText}</p>
        <button onClick={onStop}>{L.stopBtn}</button>
      </div>
    </div>
  );
}
