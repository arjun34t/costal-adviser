import React, { useEffect, useRef } from "react";
import { useApp } from "../context/AppContext.jsx";
import { LABELS } from "../constants.js";
import MessageBubble from "./MessageBubble.jsx";
import ComposerInput from "./ComposerInput.jsx";

export default function ChatPanel() {
  const { lang, selectedLocation, selectedDistrict, messages, isTyping, toolBadges, notices } = useApp();
  const L = LABELS[lang];
  const chatWindowRef = useRef(null);

  // Auto-scroll to bottom when messages/typing changes
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages, isTyping, toolBadges, notices]);

  const locationMeta = selectedLocation
    ? selectedDistrict
      ? `${selectedLocation} · ${selectedDistrict}`
      : selectedLocation
    : L.locationMetaUnset;

  const isEmpty = messages.length === 0 && notices.length === 0 && !isTyping && toolBadges.length === 0;

  return (
    <section className="chat-panel">
      <div className="conversation-head">
        <div>
          <p className="conversation-label">{lang === "ml" ? "സംഭാഷണം" : "Conversation"}</p>
          <h2>{lang === "ml" ? "ഫിഷർ അഡൈ്വസർ" : "Fisher Adviser"}</h2>
        </div>
        <div className="conversation-meta">
          <span className="meta-pill">📍 {locationMeta}</span>
        </div>
      </div>

      <div className="chat-window" ref={chatWindowRef}>
        {isEmpty && (
          <div className="empty-state">
            <div className="empty-state-card">
              <div className="empty-icon">🌊</div>
              <h3>{lang === "ml" ? "നമസ്കാരം! സഹായി ഇവിടെ ഉണ്ട്." : "Hello! Your assistant is here."}</h3>
              <p>{lang === "ml" ? "കടൽ, മീൻ, അല്ലെങ്കിൽ സർക്കാർ പദ്ധതികൾ - ഏതും ചോദിക്കൂ." : "Ask anything about sea conditions, fish prices, or government schemes."}</p>
            </div>
          </div>
        )}

        {notices.map((notice) => (
          <div key={notice.id} className={notice.className}>
            {notice.text}
          </div>
        ))}

        {messages.map((msg, i) => (
          <MessageBubble key={`${msg.timestamp}-${i}`} message={msg} />
        ))}

        {toolBadges.map((badge) => (
          <div key={badge.id} className="tool-badge">
            {badge.text}
          </div>
        ))}

        {isTyping && (
          <div className="message-row bot" id="typingIndicator">
            <div className="typing-bubble">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
      </div>

      <ComposerInput />
    </section>
  );
}
