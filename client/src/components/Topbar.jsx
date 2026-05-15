import React from "react";
import { useApp } from "../context/AppContext.jsx";
import { LABELS } from "../constants.js";

export default function Topbar({ devPanelOpen, onToggleDevPanel, onToggleSidebar }) {
  const { lang, changeLang, audioEnabled, changeAudio, theme, changeTheme, addNotice } = useApp();
  const L = LABELS[lang];

  function handleLangChange(e) {
    const newLang = e.target.value;
    changeLang(newLang);
    addNotice(LABELS[newLang].switched);
  }

  return (
    <header className="topbar">
      <div className="brand-block">
        <button
          className="icon-button mobile-menu-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle menu"
        >
          ☰
        </button>
        <div className="brand-mark">🐟</div>
        <div className="brand-copy">
          <p className="eyebrow">Fisher Adviser</p>
          <h1>{lang === "ml" ? "കേരള തീരസഹായി" : "Kerala Coastal Assistant"}</h1>
          <p className="brand-sub">{lang === "ml" ? "മത്സ്യബന്ധന സഹായി" : "Your fishing companion"}</p>
        </div>
      </div>
      <div className="topbar-actions">
        <button
          className="icon-button"
          onClick={() => changeTheme(theme === "light" ? "dark" : "light")}
          title={theme === "light" ? "Switch to dark" : "Switch to light"}
          aria-label="Toggle theme"
        >
          {theme === "light" ? "🌙" : "☀️"}
        </button>
        <button
          className={`icon-button audio-toggle${audioEnabled ? " audio-on" : ""}`}
          onClick={() => changeAudio(!audioEnabled)}
          aria-label={audioEnabled ? "Disable audio" : "Enable audio"}
          title={audioEnabled ? L.audioOn : L.audioOff}
        >
          {audioEnabled ? "🔊" : "🔇"}
        </button>
        <button
          className={`icon-button dev-toggle-btn${devPanelOpen ? " dev-toggle-active" : ""}`}
          onClick={onToggleDevPanel}
          aria-label="Toggle developer console"
          title="Developer Console"
        >
          &lt;/&gt;
        </button>
        <select
          className="lang-select"
          value={lang}
          onChange={handleLangChange}
          aria-label="Select language"
        >
          <option value="ml">മലയാളം</option>
          <option value="en">English</option>
        </select>
      </div>
    </header>
  );
}
