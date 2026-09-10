import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import CommandCenter from "./components/CommandCenter";
import LiveMapView from "./components/LiveMapView";
import GeoTemporalGraph from "./components/GeoTemporalGraph";
import VehicleIntelligence from "./components/VehicleIntelligence";
import CameraNetworkView from "./components/CameraNetworkView";
import CameraGridView from "./components/CameraGridView";
import LiveCameraView from "./components/LiveCameraView";
import AlertsView from "./components/AlertsView";
import WatchlistView from "./components/WatchlistView";
import SearchView from "./components/SearchView";
import InvestigationsView from "./components/InvestigationsView";
import EvidenceView from "./components/EvidenceView";
import ReportsView from "./components/ReportsView";
import SystemHealthView from "./components/SystemHealthView";
import ArchitectureView from "./components/ArchitectureView";
import SettingsView from "./components/SettingsView";
import "./App.css";

const CAMERA_POLL_MS = 15000;
const ALERT_POLL_MS = 6000;

export default function App() {
  const [view, setView] = useState("command");
  const [cameras, setCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState(null);
  const [vehicleResult, setVehicleResult] = useState(null);
  const [health, setHealth] = useState(null);
  const [gapAnalysis, setGapAnalysis] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [gapRefreshToken, setGapRefreshToken] = useState(0);
  const [pendingPlate, setPendingPlate] = useState("");

  const refreshCameras = useCallback(async () => {
    try {
      setCameras(await api.listCameras());
    } catch {
      // catalogue endpoint is polled again shortly; a transient failure
      // here isn't worth surfacing as an error banner
    }
  }, []);

  const refreshGapAnalysis = useCallback(async () => {
    try {
      setGapAnalysis(await api.gapAnalysis());
    } catch {
      // same tolerance as cameras — real endpoint, real transient failures
    }
  }, []);

  useEffect(() => {
    refreshCameras();
    const id = setInterval(refreshCameras, CAMERA_POLL_MS);
    return () => clearInterval(id);
  }, [refreshCameras, gapRefreshToken]);

  useEffect(() => {
    refreshGapAnalysis();
    const id = setInterval(refreshGapAnalysis, CAMERA_POLL_MS);
    return () => clearInterval(id);
  }, [refreshGapAnalysis, gapRefreshToken]);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    const id = setInterval(() => api.health().then(setHealth).catch(() => {}), CAMERA_POLL_MS);
    return () => clearInterval(id);
  }, []);

  const refreshAlerts = useCallback(async () => {
    try {
      setAlerts(await api.listAlerts());
    } catch {
      // AlertsView has its own error handling for the detailed feed;
      // this top-level poll only feeds the topbar/Command Center count.
    }
  }, []);

  useEffect(() => {
    refreshAlerts();
    const id = setInterval(refreshAlerts, ALERT_POLL_MS);
    return () => clearInterval(id);
  }, [refreshAlerts]);

  const activeAlertCount = alerts.filter((a) => (a.status || "new") !== "resolved" && (a.status || "new") !== "dismissed").length;
  const selectedCamera = cameras.find((c) => c.id === selectedCameraId) || null;

  function openGraph(plate) {
    setPendingPlate(plate);
    setView("graph");
  }
  function openVehicle(plate) {
    setPendingPlate(plate);
    setView("vehicle");
  }
  function openCamera(id) {
    setSelectedCameraId(id);
    setView("camera");
  }

  return (
    <div className="shell">
      <Sidebar view={view} onNavigate={setView} coverage={gapAnalysis} />
      <div className="main-area">
        <Topbar
          health={health}
          activeAlertCount={activeAlertCount}
          onSearchSubmit={openVehicle}
          onAuthenticated={() => {
            refreshCameras();
            refreshGapAnalysis();
            refreshAlerts();
          }}
        />
        {/* Conditional mounting, not always-mounted+CSS-hidden: caught by
            actually running this and watching the network tab — with every
            view mounted at once, all 8+ screens' on-mount data-fetches fired
            simultaneously on page load, before the API key was ever set,
            producing a burst of guaranteed 401s and continuous background
            polling for screens the user never opened. Only the active
            view's component exists in the tree now, matching the original
            app's tab behaviour (and normal React idiom). */}
        <div className="views2">
          <div className="view2 active">
            {view === "command" && <CommandCenter cameras={cameras} health={health} gapAnalysis={gapAnalysis} alerts={alerts} route={vehicleResult?.sightings} onOpenAlert={() => setView("alerts")} />}
            {view === "livemap" && <LiveMapView cameras={cameras} route={vehicleResult?.sightings} selectedCameraId={selectedCameraId} onSelectCamera={openCamera} />}
            {view === "graph" && <GeoTemporalGraph cameras={cameras} initialPlate={pendingPlate} />}
            {view === "vehicle" && <VehicleIntelligence initialPlate={pendingPlate} onResult={setVehicleResult} onOpenGraph={openGraph} />}
            {view === "network" && (
              <CameraNetworkView
                cameras={cameras}
                gapAnalysis={gapAnalysis}
                selectedCameraId={selectedCameraId}
                onSelectCamera={setSelectedCameraId}
                onOpenCamera={openCamera}
                gapRefreshToken={gapRefreshToken}
                onOnboarded={() => setGapRefreshToken((n) => n + 1)}
              />
            )}
            {view === "camera" && <LiveCameraView camera={selectedCamera} />}
            {view === "grid" && <CameraGridView cameras={cameras} />}
            {view === "alerts" && <AlertsView />}
            {view === "watchlist" && <WatchlistView />}
            {view === "search" && <SearchView onOpenPlate={openVehicle} />}
            {view === "investigations" && <InvestigationsView />}
            {view === "evidence" && <EvidenceView />}
            {view === "reports" && <ReportsView />}
            {view === "health" && <SystemHealthView health={health} gapAnalysis={gapAnalysis} />}
            {view === "architecture" && <ArchitectureView />}
            {view === "settings" && <SettingsView />}
          </div>
        </div>
      </div>
    </div>
  );
}
