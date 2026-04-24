import React, { useState, useEffect, useCallback, useRef } from "react";
import { useApp } from "../context/AppContext.jsx";
import { LABELS } from "../constants.js";
import { fetchAllLocations, searchLocations, resolveLocation } from "../api.js";

const MAX_DISPLAY = 60;

export default function LocationModal({ onClose }) {
  const { lang, setLocation } = useApp();
  const L = LABELS[lang];
  const [allLocations, setAllLocations] = useState([]);
  const [displayedLocations, setDisplayedLocations] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [pendingLocation, setPendingLocation] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const searchTimerRef = useRef(null);

  useEffect(() => {
    fetchAllLocations()
      .then((locs) => {
        setAllLocations(locs);
        setDisplayedLocations(locs.slice(0, MAX_DISPLAY));
      })
      .catch(() => {});
  }, []);

  // Parse "Name, District" format
  function parseEntry(entry) {
    const idx = entry.indexOf(", ");
    if (idx === -1) return { location: entry, district: null };
    return { location: entry.slice(0, idx), district: entry.slice(idx + 2) };
  }

  function localSearch(query) {
    const q = query.toLowerCase();
    return allLocations
      .map((entry) => {
        const value = entry.toLowerCase();
        let score = 0;
        if (value === q) score = 100;
        else if (value.startsWith(q)) score = 80;
        else if (value.includes(q)) score = 40;
        return { entry, score };
      })
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || a.entry.localeCompare(b.entry))
      .map((item) => item.entry);
  }

  function handleSearch(e) {
    const query = e.target.value;
    setSearchQuery(query);
    clearTimeout(searchTimerRef.current);

    if (!query.trim()) {
      setDisplayedLocations(allLocations.slice(0, MAX_DISPLAY));
      return;
    }

    searchTimerRef.current = setTimeout(async () => {
      try {
        const matches = await searchLocations(query.trim());
        // matches already in "Name, District" format
        setDisplayedLocations(matches.length ? matches.slice(0, MAX_DISPLAY) : localSearch(query.trim()).slice(0, MAX_DISPLAY));
      } catch (_) {
        setDisplayedLocations(localSearch(query.trim()).slice(0, MAX_DISPLAY));
      }
    }, 150);
  }

  async function handleLocationClick(entry) {
    const { location, district } = parseEntry(entry);
    setPendingLocation({ location, district });
    setShowConfirm(true);
  }

  function handleConfirm() {
    if (pendingLocation) {
      setLocation(pendingLocation.location, pendingLocation.district);
    }
    onClose();
  }

  function handleBack() {
    setPendingLocation(null);
    setShowConfirm(false);
    setSearchQuery("");
    setDisplayedLocations(allLocations.slice(0, MAX_DISPLAY));
  }

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-card">
        <div className="modal-header">
          <div>
            <p className="modal-eyebrow">{lang === "ml" ? "സ്ഥലം" : "Location"}</p>
            <h3>{lang === "ml" ? "തീരദേശ സ്ഥലം തിരഞ്ഞെടുക്കുക" : "Select Coastal Location"}</h3>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {!showConfirm ? (
          <>
            <input
              type="text"
              className="location-search-input"
              placeholder={L.searchPlaceholder}
              value={searchQuery}
              onChange={handleSearch}
              autoFocus
            />
            <div className="location-list">
              {displayedLocations.map((entry, i) => {
                const { location, district } = parseEntry(entry);
                return (
                  <div
                    key={i}
                    className="location-item"
                    onClick={() => handleLocationClick(entry)}
                  >
                    <span>{location}</span>
                    {district && (
                      <span style={{ opacity: 0.5, fontSize: "0.8em", marginLeft: "0.4em" }}>
                        {district}
                      </span>
                    )}
                  </div>
                );
              })}
              {allLocations.length > MAX_DISPLAY && !searchQuery && (
                <div className="location-hint">
                  {L.moreResults(allLocations.length - MAX_DISPLAY)}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="location-confirm">
            <p className="confirm-title">{lang === "ml" ? "ഈ സ്ഥലം തിരഞ്ഞെടുക്കണോ?" : "Confirm this location?"}</p>
            <p>
              {pendingLocation?.location}
              {pendingLocation?.district ? ` · ${L.districtText(pendingLocation.district)}` : ""}
            </p>
            <div className="confirm-buttons">
              <button className="secondary-button confirm-no" onClick={handleBack}>
                {lang === "ml" ? "തിരിച്ചു പോകുക" : "Go back"}
              </button>
              <button className="secondary-button confirm-yes" onClick={handleConfirm}>
                {lang === "ml" ? "✓ ഉറപ്പിക്കുക" : "✓ Confirm"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
