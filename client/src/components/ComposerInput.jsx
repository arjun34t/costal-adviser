import React, { useRef, useState, useCallback } from "react";
import { useApp } from "../context/AppContext.jsx";
import { LABELS } from "../constants.js";
import { useVoice } from "../hooks/useVoice.js";
import RecordingOverlay from "./RecordingOverlay.jsx";

export default function ComposerInput() {
  const { lang, sendMessage, isStreaming } = useApp();
  const L = LABELS[lang];
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef(null);
  const { isRecording, startRecording, stopRecording } = useVoice();

  const autosize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, []);

  function handleInput(e) {
    setInputValue(e.target.value);
    autosize();
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleSend() {
    if (!inputValue.trim() || isStreaming) return;
    sendMessage(inputValue);
    setInputValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  return (
    <>
      <div className="composer-card">
        <div className="composer-tools">
          <p className="composer-hint">{L.composerHint}</p>
        </div>
        <div className="composer-row">
          <div style={{ flex: 1, display: "flex", alignItems: "flex-end", gap: "12px" }}>
            <textarea
              ref={textareaRef}
              className="text-input"
              value={inputValue}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder={L.inputPlaceholder}
              rows={1}
              disabled={isStreaming}
              aria-label="Message input"
            />
            <button
              className={`icon-button mic-btn${isRecording ? " recording" : ""}`}
              onClick={isRecording ? stopRecording : startRecording}
              aria-label={isRecording ? "Stop recording" : "Start recording"}
              disabled={isStreaming && !isRecording}
            >
              🎙️
            </button>
          </div>
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!inputValue.trim() || isStreaming}
            aria-label="Send message"
          >
            ➤
          </button>
        </div>
      </div>
      {isRecording && <RecordingOverlay onStop={stopRecording} />}
    </>
  );
}
