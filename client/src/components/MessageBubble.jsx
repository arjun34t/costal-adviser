import React, { useEffect, useRef } from "react";
import { useApp } from "../context/AppContext.jsx";
import { LABELS, LOCALE_MAP } from "../constants.js";
import PriceChart from "./PriceChart.jsx";

function formatTime(timestamp, lang) {
  const date = timestamp ? new Date(timestamp) : new Date();
  return new Intl.DateTimeFormat(LOCALE_MAP[lang] || "en-IN", {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export default function MessageBubble({ message }) {
  const { lang } = useApp();
  const L = LABELS[lang];
  const audioRef = useRef(null);
  const audioBlobUrlRef = useRef(null);

  const isUser = message.role === "user";

  useEffect(() => {
    if (message.audioBlob && audioRef.current) {
      // Create object URL for the blob
      if (audioBlobUrlRef.current) {
        URL.revokeObjectURL(audioBlobUrlRef.current);
      }
      const url = URL.createObjectURL(message.audioBlob);
      audioBlobUrlRef.current = url;
      audioRef.current.src = url;
    }
    return () => {
      if (audioBlobUrlRef.current) {
        URL.revokeObjectURL(audioBlobUrlRef.current);
        audioBlobUrlRef.current = null;
      }
    };
  }, [message.audioBlob]);

  return (
    <div className={`message-row ${isUser ? "user" : "bot"}`}>
      <article className="bubble">
        <div className="message-header">
          <span className="message-label">{isUser ? L.userLabel : L.agentLabel}</span>
          <time className="message-time">{formatTime(message.timestamp, lang)}</time>
        </div>
        <div className="bubble-body">{message.text}</div>
        {message.priceCharts?.map((chartData, i) => (
          <PriceChart key={`${chartData.fish_type}-${i}`} data={chartData} />
        ))}
        {message.audioBlob && (
          <audio ref={audioRef} controls autoPlay />
        )}
      </article>
    </div>
  );
}
