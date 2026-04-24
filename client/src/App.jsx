import React, { useState } from "react";
import { AppProvider } from "./context/AppContext.jsx";
import Topbar from "./components/Topbar.jsx";
import Sidebar from "./components/Sidebar.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import LocationModal from "./components/LocationModal.jsx";
import DevPanel from "./components/DevPanel.jsx";

function AppShell() {
  const [locationModalOpen, setLocationModalOpen] = useState(false);
  const [devPanelOpen, setDevPanelOpen] = useState(false);

  return (
    <div className="app-shell">
      <Topbar
        devPanelOpen={devPanelOpen}
        onToggleDevPanel={() => setDevPanelOpen((v) => !v)}
      />
      <main className="workspace">
        <div className="sidebar-wrapper">
          <Sidebar onOpenLocation={() => setLocationModalOpen(true)} />
          {devPanelOpen && (
            <DevPanel onClose={() => setDevPanelOpen(false)} />
          )}
        </div>
        <ChatPanel />
      </main>
      {locationModalOpen && (
        <LocationModal onClose={() => setLocationModalOpen(false)} />
      )}
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppShell />
    </AppProvider>
  );
}
