import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from "react";
import { LABELS, TOOL_LABELS, HISTORY_KEY, MAX_HISTORY } from "../constants.js";
import { parseSSE, streamChat, synthesizeSpeech, translateText } from "../api.js";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem("fisherLang") || "ml");
  const [audioEnabled, setAudioEnabled] = useState(() => localStorage.getItem("audio_enabled") === "true");
  const [theme, setTheme] = useState(() => localStorage.getItem("fisherTheme") || "dark");
  const [selectedLocation, setSelectedLocation] = useState(() => localStorage.getItem("fisherLocation") || null);
  const [selectedDistrict, setSelectedDistrict] = useState(() => localStorage.getItem("fisherDistrict") || null);
  const [messages, setMessages] = useState(() => {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  });
  const [isStreaming, setIsStreaming] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [toolBadges, setToolBadges] = useState([]);
  const [notices, setNotices] = useState([]);
  const [devLogs, setDevLogs] = useState([]);
  const noticeIdRef = useRef(0);

  const addDevLog = useCallback((entry) => {
    const time = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setDevLogs((prev) => [...prev.slice(-300), { time, ...entry }]);
  }, []);

  const clearDevLogs = useCallback(() => setDevLogs([]), []);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const saveConversation = useCallback((msgs) => {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(msgs.slice(-MAX_HISTORY)));
    } catch (_) {}
  }, []);

  const changeLang = useCallback((newLang) => {
    setLang(newLang);
    localStorage.setItem("fisherLang", newLang);
  }, []);

  const changeAudio = useCallback((enabled) => {
    setAudioEnabled(enabled);
    localStorage.setItem("audio_enabled", String(enabled));
  }, []);

  const changeTheme = useCallback((newTheme) => {
    setTheme(newTheme);
    localStorage.setItem("fisherTheme", newTheme);
  }, []);

  const setLocation = useCallback((name, district) => {
    setSelectedLocation(name);
    setSelectedDistrict(district || null);
    localStorage.setItem("fisherLocation", name);
    if (district) {
      localStorage.setItem("fisherDistrict", district);
    } else {
      localStorage.removeItem("fisherDistrict");
    }
  }, []);

  const addNotice = useCallback((text, className = "lang-divider-chat") => {
    const id = ++noticeIdRef.current;
    setNotices((prev) => [...prev, { id, text, className }]);
    return id;
  }, []);

  const removeNotice = useCallback((id) => {
    setNotices((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setNotices([]);
    localStorage.removeItem(HISTORY_KEY);
  }, []);

  const sendMessage = useCallback(
    async (text, langOverride) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      const activeLang = langOverride || lang;
      const L = LABELS[activeLang];

      const recentHistory = messages.slice(-6).map((msg) => ({
        role: msg.role === "user" ? "user" : "assistant",
        content: msg.text,
      }));

      const userTimestamp = new Date().toISOString();
      const userMsg = { role: "user", text: trimmed, timestamp: userTimestamp, language: activeLang };
      const nextMessages = [...messages, userMsg];
      setMessages(nextMessages);
      saveConversation(nextMessages);

      addDevLog({ type: "user", text: trimmed });
      addDevLog({ type: "system", text: `language=${activeLang}  district=${selectedDistrict || "unset"}` });

      setIsTyping(true);
      setIsStreaming(true);

      let currentToolBadgeIds = [];

      try {
        const chatRes = await streamChat({
          message: trimmed,
          district: selectedDistrict || "",
          language: activeLang,
          history: recentHistory,
        });

        setIsTyping(false);
        let response = null;
        const priceCharts = [];

        for await (const event of parseSSE(chatRes)) {
          if (event.type === "tool_call") {
            const toolName = event.data.tool;
            const toolLabels = TOOL_LABELS[toolName] || { ml: "🔍 പ്രവർത്തിക്കുന്നു...", en: "🔍 Working..." };
            const badgeId = ++noticeIdRef.current;
            currentToolBadgeIds.push(badgeId);
            setToolBadges((prev) => [...prev, { id: badgeId, text: toolLabels[activeLang] || toolLabels.en }]);
            addDevLog({ type: "tool", text: `→ ${toolName}()` });
          } else if (event.type === "price_data") {
            priceCharts.push(event.data);
            addDevLog({ type: "result", text: `← price_history  fish="${event.data.fish_type}"  days=${event.data.history?.length ?? "?"}` });
          } else if (event.type === "message") {
            response = event.data.response;
          }
        }

        if (!response) throw new Error("No response received");
        addDevLog({ type: "response", text: `← LLM response  words=${response.split(" ").length}` });

        let audioBlob = null;
        if (audioEnabled) {
          try {
            let ttsText = response;
            if (activeLang === "en") {
              const transRes = await translateText(response, "ml");
              ttsText = transRes.translated || response;
            }
            audioBlob = await synthesizeSpeech(ttsText);
          } catch (_) {
            // TTS failure is non-fatal
          }
        }

        const answerTimestamp = new Date().toISOString();
        const agentMsg = {
          role: "agent",
          text: response,
          timestamp: answerTimestamp,
          language: activeLang,
          audioBlob,
          priceCharts: priceCharts.length > 0 ? priceCharts : undefined,
        };
        const withAgent = [...nextMessages, agentMsg];
        // Clear badges and add message in the same render
        setToolBadges([]);
        currentToolBadgeIds = [];
        setMessages(withAgent);
        saveConversation(withAgent.map(({ audioBlob: _, ...m }) => m));
      } catch (err) {
        setIsTyping(false);
        setToolBadges([]);
        addDevLog({ type: "error", text: `✗ ${err.message}` });

        const errorText = `⚠️ ${L.errorPrefix}: ${err.message}`;
        const errorTimestamp = new Date().toISOString();
        const errorMsg = { role: "agent", text: errorText, timestamp: errorTimestamp, language: activeLang };
        const withError = [...nextMessages, errorMsg];
        setMessages(withError);
        saveConversation(withError);
      } finally {
        setIsStreaming(false);
      }
    },
    [lang, messages, selectedDistrict, audioEnabled, saveConversation, addDevLog]
  );

  const addAgentMessage = useCallback(
    (text) => {
      const timestamp = new Date().toISOString();
      const msg = { role: "agent", text, timestamp, language: lang };
      setMessages((prev) => {
        const next = [...prev, msg];
        saveConversation(next);
        return next;
      });
    },
    [lang, saveConversation]
  );

  const value = {
    lang,
    changeLang,
    audioEnabled,
    changeAudio,
    theme,
    changeTheme,
    selectedLocation,
    selectedDistrict,
    setLocation,
    messages,
    isStreaming,
    isTyping,
    toolBadges,
    notices,
    devLogs,
    addDevLog,
    clearDevLogs,
    sendMessage,
    clearMessages,
    addNotice,
    removeNotice,
    addAgentMessage,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
