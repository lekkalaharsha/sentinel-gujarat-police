import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import MapView from "./components/MapView";
import CameraList from "./components/CameraList";
import ApiKeyBar from "./components/ApiKeyBar";
import LiveView from "./components/LiveView";
import VehicleSearch from "./components/VehicleSearch";
import AlertsPanel from "./components/AlertsPanel";
import WatchlistPanel from "./components/WatchlistPanel";
import GapAnalysisPanel from "./components/GapAnalysisPanel";
import OnboardCameraForm from "./components/OnboardCameraForm";
import "./App.css";

const CAMERA_POLL_MS = 15000;

export default function App() {
  const [cameras, setCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState(null);
  const [vehicleResult, setVehicleResult] = useState(null);
  const [health, setHealth] = useState(null);
  const [tab, setTab] = useState("map");
  const [gapRefreshToken, setGapRefreshToken] = useState(0);

  const refreshCameras = useCallback(async () => {
    try {
      setCameras(await api.listCameras());
    } catch {
      // catalogue endpoint is polled again shortly; a transient failure here
      // isn't worth surfacing as an error banner
    }
  }, []);

  useEffect(() => {
    refreshCameras();
    const id = setInterval(refreshCameras, CAMERA_POLL_MS);
    return () => clearInterval(id);
  }, [refreshCameras]);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div className="app">
      <header className="app__header">
        <h1>Sentinel</h1>
        <span className="app__subtitle">Unified CCTV interoperability &amp; analytics layer — Model 1 + Model 2</span>
        {health && (
          <span className="app__health">
            {health.active_camera_workers?.length ?? 0} active workers · {health.catalogue_size} cameras known
          </span>
        )}
        <ApiKeyBar />
      </header>

      <nav className="app__tabs">
        <button className={tab === "map" ? "active" : ""} onClick={() => setTab("map")}>
          Map &amp; Registry
        </button>
        <button className={tab === "vehicle" ? "active" : ""} onClick={() => setTab("vehicle")}>
          Vehicle Tracking
        </button>
        <button className={tab === "watchlist" ? "active" : ""} onClick={() => setTab("watchlist")}>
          Watchlist
        </button>
        <button className={tab === "registry-ops" ? "active" : ""} onClick={() => setTab("registry-ops")}>
          Registry Ops
        </button>
      </nav>

      <main className="app__main">
        {tab === "map" && (
          <div className="layout layout--map">
            <div className="layout__sidebar">
              <CameraList cameras={cameras} selectedCameraId={selectedCameraId} onSelectCamera={setSelectedCameraId} />
            </div>
            <div className="layout__map">
              <MapView cameras={cameras} onSelectCamera={setSelectedCameraId} selectedCameraId={selectedCameraId} />
            </div>
            <div className="layout__live">
              <LiveView cameraId={selectedCameraId} />
            </div>
          </div>
        )}

        {tab === "vehicle" && (
          <div className="layout layout--vehicle">
            <div className="layout__sidebar">
              <VehicleSearch onResult={setVehicleResult} />
            </div>
            <div className="layout__map">
              <MapView cameras={cameras} route={vehicleResult?.sightings} />
            </div>
          </div>
        )}

        {tab === "watchlist" && (
          <div className="layout layout--watchlist">
            <WatchlistPanel />
            <AlertsPanel />
          </div>
        )}

        {tab === "registry-ops" && (
          <div className="layout layout--watchlist">
            <OnboardCameraForm
              onOnboarded={() => {
                refreshCameras();
                setGapRefreshToken((n) => n + 1);
              }}
            />
            <GapAnalysisPanel onRefresh={gapRefreshToken} />
          </div>
        )}
      </main>
    </div>
  );
}
