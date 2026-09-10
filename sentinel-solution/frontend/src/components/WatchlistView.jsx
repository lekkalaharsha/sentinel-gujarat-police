import WatchlistPanel from "./WatchlistPanel";

export default function WatchlistView() {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Watchlist</h1>
          <div className="sub">Vehicles under active surveillance directive</div>
        </div>
      </div>
      <div className="card2">
        <WatchlistPanel />
      </div>
    </>
  );
}
