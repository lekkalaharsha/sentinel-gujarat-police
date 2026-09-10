import { useEffect, useState } from "react";
import { api } from "../api";

// Fetches the REAL saved detection crop (see pipeline.py's _save_crop /
// GET /vehicle/event/{id}/crop) as an authenticated blob — a plain <img
// src> can't carry the API-key header. Shows an honest placeholder, not a
// stock photo, when the event predates the crop feature or the save failed.
export default function EvidenceViewer({ eventId, hasImage, label = "Evidence" }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setUrl(null);
    setError(null);
    if (!eventId || !hasImage) return;
    let cancelled = false;
    api.eventCropBlobUrl(eventId).then(
      (blobUrl) => { if (!cancelled) setUrl(blobUrl); },
      (err) => { if (!cancelled) setError(err.message); }
    );
    return () => { cancelled = true; };
  }, [eventId, hasImage]);

  return (
    <div className="evimg2">
      <span className="lbl2">{label}</span>
      {url ? (
        <img src={url} alt={`Evidence crop for event ${eventId}`} />
      ) : (
        <span className="ph2">
          {!hasImage ? "No evidence image saved for this sighting" : error ? `Failed to load: ${error}` : "Loading…"}
        </span>
      )}
    </div>
  );
}
