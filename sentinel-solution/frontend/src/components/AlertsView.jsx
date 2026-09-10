import AlertsPanel from "./AlertsPanel";

export default function AlertsView() {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Alerts</h1>
          <div className="sub">Real-time watchlist correlation feed — governed lifecycle, not a fire-and-forget toast</div>
        </div>
      </div>
      <div className="card2">
        <AlertsPanel />
      </div>
    </>
  );
}
