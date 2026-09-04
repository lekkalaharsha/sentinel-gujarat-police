import { useEffect, useState } from "react";
import { api } from "../api";

export default function WatchlistPanel() {
  const [entries, setEntries] = useState([]);
  const [plate, setPlate] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState(null);

  async function load() {
    try {
      setEntries(await api.listWatchlist());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submit(e) {
    e.preventDefault();
    if (!plate || !reason) return;
    try {
      await api.addWatchlist(plate.trim(), reason.trim());
      setPlate("");
      setReason("");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="watchlist-panel">
      <h3>Watchlist</h3>
      <form onSubmit={submit} className="watchlist-panel__form">
        <input placeholder="Plate" value={plate} onChange={(e) => setPlate(e.target.value)} />
        <input placeholder="Reason (stolen, wanted, ...)" value={reason} onChange={(e) => setReason(e.target.value)} />
        <button type="submit">Add</button>
      </form>
      {error && <p className="watchlist-panel__error">{error}</p>}
      <ul>
        {entries.map((e) => (
          <li key={e.plate}>
            <strong>{e.plate}</strong> — {e.reason}
          </li>
        ))}
      </ul>
    </div>
  );
}
