import {
  IconGrid, IconMap, IconGraph, IconCar, IconCamera, IconAlert, IconEye,
  IconSearch, IconFolder, IconEvidence, IconReport, IconPulse, IconLayers,
  IconSettings, IconShield,
} from "../icons";

// IconLayers doubles as the Model 3 federation icon below (no dedicated
// icon exists yet, and this repo's icon set is deliberately small — see
// icons.jsx) — matches the reuse-over-new-abstraction convention already
// used for "Architecture" above.

const NAV = [
  { group: "Operations", items: [
    { id: "command", label: "Command Center", icon: IconGrid },
    { id: "livemap", label: "Live Map", icon: IconMap },
    { id: "graph", label: "Geo-Temporal Graph", icon: IconGraph, core: true },
    { id: "vehicle", label: "Vehicle Intelligence", icon: IconCar },
    { id: "network", label: "Camera Network", icon: IconCamera },
    { id: "grid", label: "Camera Grid", icon: IconLayers },
  ]},
  { group: "Monitoring", items: [
    { id: "alerts", label: "Alerts", icon: IconAlert },
    { id: "watchlist", label: "Watchlist", icon: IconEye },
    { id: "federation", label: "Federation (Model 3)", icon: IconLayers },
  ]},
  { group: "Investigation", items: [
    { id: "search", label: "Search", icon: IconSearch },
    { id: "investigations", label: "Investigations", icon: IconFolder },
    { id: "evidence", label: "Evidence", icon: IconEvidence },
    { id: "reports", label: "Reports", icon: IconReport },
  ]},
  { group: "System", items: [
    { id: "health", label: "System Health", icon: IconPulse },
    { id: "architecture", label: "Architecture", icon: IconLayers },
    { id: "settings", label: "Settings", icon: IconSettings },
  ]},
];

export default function Sidebar({ view, onNavigate, coverage }) {
  return (
    <nav className="sidebar">
      <div className="brand">
        <div className="brand-mark"><IconShield width={16} height={16} /></div>
        <div>
          <div className="brand-name">SENTINEL</div>
          <div className="brand-tag">Geo-Temporal Intel</div>
        </div>
      </div>

      {NAV.map((g) => (
        <div className="navgroup" key={g.group}>
          <div className="navgroup-label">{g.group}</div>
          {g.items.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.id}
                className={`navitem ${view === item.id ? "active" : ""}`}
                onClick={() => onNavigate(item.id)}
              >
                <Icon />
                {item.label}
                {item.core && <span className="core-tag">CORE</span>}
              </div>
            );
          })}
        </div>
      ))}

      <div className="coverage-box">
        <div className="coverage-title">Gujarat coverage</div>
        <div className="coverage-row"><span>Cameras known</span><b>{coverage?.catalogue_size ?? "—"}</b></div>
        <div className="coverage-row"><span>Onboarded</span><b>{coverage?.registered_size ?? "—"}</b></div>
        <div className="coverage-row"><span>Mode</span><b style={{ color: "var(--confirmed)" }}>Unified</b></div>
      </div>
      <div className="sidebar-foot">Sentinel — Model 1 + 2 hybrid<br />Gujarat Police Innovation Challenge 2026</div>
    </nav>
  );
}
