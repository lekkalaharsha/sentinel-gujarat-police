import GapAnalysisPanel from "./GapAnalysisPanel";
import MapView from "./MapView";

// Model 1's gap-analysis deliverable, given its own destination rather than
// living inside the registry screen. Reuses the existing real panel — the
// data is GET /cameras/gap-analysis, unchanged.
export default function CoverageGapsView({ cameras }) {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Coverage &amp; Gaps</h1>
          <div className="sub">
            Where the estate is blind, ageing, or missing metadata — Model 1 gap-analysis deliverable
          </div>
        </div>
      </div>
      <div className="cols2">
        <div className="card2" style={{ padding: 0 }}>
          <div className="mapwrap2">
            <MapView cameras={cameras} />
          </div>
        </div>
        <GapAnalysisPanel />
      </div>
    </>
  );
}
