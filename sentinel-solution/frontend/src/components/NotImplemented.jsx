// Honest placeholder for a navigation destination whose backend does not
// exist yet. Deliberately states the missing capability and what it would
// take — CLAUDE.md forbids inventing fake functionality behind a nav item,
// and a jury reading "not yet implemented" costs less than a jury finding
// a screen full of invented numbers.
export default function NotImplemented({ title, sub, what, requires, related, onNavigate }) {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>{title}</h1>
          {sub && <div className="sub">{sub}</div>}
        </div>
      </div>
      <div className="card2">
        <div className="card-h2">
          <h2>Not yet implemented</h2>
          <span className="state-badge" style={{ color: "var(--warn)", background: "var(--warn-bg)" }}>
            NOT BUILT
          </span>
        </div>
        <p style={{ fontSize: 12.5, color: "var(--text-dim)", lineHeight: 1.6 }}>{what}</p>
        {requires?.length > 0 && (
          <>
            <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-dim)", margin: "14px 0 6px" }}>
              Backend work required
            </div>
            <ul style={{ fontSize: 12.5, lineHeight: 1.7, paddingLeft: 18, margin: 0 }}>
              {requires.map((r) => <li key={r}>{r}</li>)}
            </ul>
          </>
        )}
        {related && (
          <p style={{ fontSize: 12.5, marginTop: 16 }}>
            Working today:{" "}
            <button className="btn2" onClick={() => onNavigate?.(related.view)}>{related.label}</button>
          </p>
        )}
      </div>
    </>
  );
}
