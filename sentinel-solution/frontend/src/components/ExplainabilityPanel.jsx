const METHOD_LABEL = {
  new_identity: "New identity — first sighting, nothing to link against yet",
  plate_continuation: "Same plate read again — direct continuation",
  plate_upgrade: "Plate read HERE upgraded an earlier anonymous appearance match",
  appearance_match: "Linked by appearance only — plate not read at this camera",
};

function Bar({ label, value, tone }) {
  const pct = value == null ? 0 : Math.round(value * 100);
  return (
    <div className="explain-bar">
      <span className="explain-bar__label">{label}</span>
      <div className="explain-bar__track">
        <div className={`explain-bar__fill explain-bar__fill--${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="explain-bar__value">{value == null ? "n/a" : `${pct}%`}</span>
    </div>
  );
}

export default function ExplainabilityPanel({ sighting }) {
  if (!sighting) return null;
  const link = sighting.link || {};
  return (
    <div className="explain-panel">
      <h4>Why was this sighting linked?</h4>
      <p className="explain-panel__method">{METHOD_LABEL[link.method] || link.method || "unknown"}</p>
      <Bar label="Plate consensus strength" value={sighting.plate_confidence} tone="plate" />
      <Bar label="Appearance (Re-ID) similarity" value={link.reid_similarity} tone="reid" />
      <Bar label="Temporal consistency" value={link.temporal_consistency} tone="temporal" />
      <div className="explain-panel__fused">
        Fused association score:{" "}
        <strong>{link.fused_score == null ? "n/a (no fusion needed)" : `${Math.round(link.fused_score * 100)}%`}</strong>
      </div>
      {link.time_since_previous_sighting_s != null && (
        <p className="explain-panel__gap">
          {Math.round(link.time_since_previous_sighting_s)}s since this identity's previous sighting.
        </p>
      )}
      <p className="explain-panel__note">
        Heuristic weighting (plate 50% / appearance 35% / recency 15%), not a calibrated probability —
        shown for investigator transparency, not as ground truth.
      </p>
    </div>
  );
}
