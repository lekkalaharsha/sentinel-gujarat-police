import { useEffect, useState } from "react";

// Renders an external, snapshot-only camera (Model 2's "unified viewer
// connecting >=2 different systems" — System B, Caltrans District 3's
// public CCTV API; see backend/app/external_camera_source.py). This is a
// periodically-refreshed still image, NOT continuous live video — it must
// never look like a LiveView tile (CLAUDE.md 24.11: a polished UI must not
// conceal a truthful distinction in feed type). The image URL is public
// (no credentials embedded), fetched directly by the browser.
const REFRESH_INTERVAL_MS = 60_000; // matches Caltrans's own ~60s update cadence

export default function SnapshotView({ imageUrl, sourceLabel }) {
  const [cacheBust, setCacheBust] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setCacheBust(Date.now()), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  const src = `${imageUrl}${imageUrl.includes("?") ? "&" : "?"}_t=${cacheBust}`;

  return (
    <div className="snapshot-view">
      <img src={src} alt={sourceLabel || "external camera snapshot"} className="snapshot-view__img" />
      <div className="snapshot-view__badge">EXTERNAL SOURCE — periodic snapshot, not live video</div>
    </div>
  );
}
