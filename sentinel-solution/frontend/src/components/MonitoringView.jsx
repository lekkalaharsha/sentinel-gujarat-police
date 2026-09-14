import AlertsPanel from "./AlertsPanel";
import WatchlistPanel from "./WatchlistPanel";

// Watchlist and alerts are one operational loop — a directive is added, a
// match fires, an operator works it — so they share a destination rather
// than forcing a nav round-trip mid-incident. Both panels are unchanged and
// still talk to their own real endpoints.
export default function MonitoringView() {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Watchlist &amp; Alerts</h1>
          <div className="sub">
            Active surveillance directives and the governed alert lifecycle they produce
          </div>
        </div>
      </div>
      <div className="cols2">
        <div className="card2">
          <div className="card-h2"><h2>Alerts</h2></div>
          <AlertsPanel />
        </div>
        <div className="card2">
          <div className="card-h2"><h2>Watchlist</h2></div>
          <WatchlistPanel />
        </div>
      </div>
    </>
  );
}
