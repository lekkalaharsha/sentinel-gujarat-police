import { useEffect, useState } from "react";
import { api } from "../api";

// GET /admin/audit-log existed on the backend (purpose-bound query log)
// with no frontend consumer — this IS the real accountability trail every
// /vehicle/* lookup writes, not a mocked activity feed.
export default function InvestigationsView() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);

  async function load() {
    try {
      setRows(await api.auditLog(200));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Investigations</h1>
          <div className="sub">Real audit trail — every purpose-bound query, who ran it, and why</div>
        </div>
        <div className="view-actions"><button className="btn2" onClick={load}>Refresh</button></div>
      </div>
      <div className="card2">
        {error && <p style={{ color: "var(--danger)", fontSize: 12 }}>{error}</p>}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--text-dim)", fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                <th style={{ padding: "0 10px 8px" }}>When</th>
                <th style={{ padding: "0 10px 8px" }}>User</th>
                <th style={{ padding: "0 10px 8px" }}>Purpose</th>
                <th style={{ padding: "0 10px 8px" }}>Case</th>
                <th style={{ padding: "0 10px 8px" }}>Query</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "8px 10px", fontFamily: "var(--mono)" }}>{new Date(r.created_at).toLocaleString()}</td>
                  <td style={{ padding: "8px 10px" }}>{r.user_id}</td>
                  <td style={{ padding: "8px 10px" }}>{r.purpose}</td>
                  <td style={{ padding: "8px 10px", fontFamily: "var(--mono)" }}>{r.case_id || "—"}</td>
                  <td style={{ padding: "8px 10px", fontFamily: "var(--mono)" }}>{r.query}</td>
                </tr>
              ))}
              {!rows.length && !error && <tr><td colSpan={5} style={{ padding: 10, color: "var(--text-dim)" }}>No queries logged yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
