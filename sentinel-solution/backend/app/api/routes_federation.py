"""Model 3 — VMS Federation & Middleware Integration.

Not built until now (2026-09-11) — see
`sentinel-solution/docs/models/model-3-vms-federation/`. Federates two
real, independently-formatted event sources: Sentinel's own Model 1/2
stack ("sentinel") and NYC Open Data's public "Open Parking and Camera
Violations" dataset ("nyc_open_data") — a real, independent public
dataset used to demonstrate genuine format-heterogeneity handling, NOT a
second Gujarat departmental VMS (none is available to federate against).
See `analytics/federation.py`'s module docstring for the full honesty
caveat, which every response from this router must carry forward — there
is zero real plate overlap between the two sources by construction.
"""
from __future__ import annotations

import datetime as dt
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from .. import config
from ..analytics.federation import SOURCE_DEMO_PARTNER_VMS
from ..db.models import FederatedEvent
from .auth import Principal, require_role
from .deps import get_db

router = APIRouter(prefix="/federation", tags=["federation"])

HONESTY_NOTE = (
    "Three source systems are federated here, and they are honest in "
    "different ways. System A ('sentinel') is Sentinel's own real Model 1/2 "
    "stack. System B ('nyc_open_data') is a real, independent, public "
    "dataset (NYC Open Data's 'Open Parking and Camera Violations') used to "
    "demonstrate genuine cross-system format normalization — it is NOT a "
    "second Gujarat departmental VMS, and it has zero real plate overlap "
    "with the Sentinel sandbox by construction (different countries), so it "
    "correlates with nothing. System C ('demo_partner_vms') is SYNTHETIC: "
    "every one of its rows was hand-written, replaying plates Sentinel "
    "really did read as if a partner system had also seen them. It exists "
    "so the correlation engine can be exercised end-to-end rather than only "
    "by unit tests. Correlations below therefore prove that the adapter and "
    "correlation pipeline work; they do NOT prove that any vehicle was "
    "really observed by two agencies."
)


def _compute_correlations(db: Session) -> dict:
    """Shared by the JSON endpoint and the PDF export so the two never
    drift — same pattern as routes_cameras.py's `_compute_gap_analysis`.

    Groups `FederatedEvent` rows by plate, then within each plate's group
    finds the closest-in-time pair of events from two DIFFERENT
    source_systems, within `config.FEDERATION_CORRELATION_WINDOW_S`. This
    is a batch/pull correlation over a time window, not real-time stream
    processing — see RESEARCH.md for why that's the honest framing.
    """
    rows = db.query(FederatedEvent).order_by(FederatedEvent.plate, FederatedEvent.observed_at).all()
    by_plate: dict[str, list[FederatedEvent]] = {}
    for row in rows:
        by_plate.setdefault(row.plate, []).append(row)

    correlations = []
    for plate, events in by_plate.items():
        sources = {e.source_system for e in events}
        if len(sources) < 2:
            continue
        best = None
        for i, a in enumerate(events):
            for b in events[i + 1 :]:
                if a.source_system == b.source_system:
                    continue
                gap_s = abs((b.observed_at - a.observed_at).total_seconds())
                if gap_s > config.FEDERATION_CORRELATION_WINDOW_S:
                    continue
                if best is None or gap_s < best[0]:
                    best = (gap_s, a, b)
        if best is not None:
            gap_s, a, b = best
            # Mirrors Model 2's link_score design: an explainable score, not
            # a black box — inverse of time gap, 1.0 at gap=0.
            confidence = 1.0 / (1.0 + gap_s / config.FEDERATION_CORRELATION_WINDOW_S)
            correlations.append(
                {
                    "plate": plate,
                    "sources": sorted(sources),
                    "time_gap_s": gap_s,
                    "correlation_confidence": round(confidence, 3),
                    # Set when either side came from the hand-written demo
                    # fixture, so no caller can render a seeded match as a
                    # real cross-agency sighting without opting into it.
                    "involves_synthetic_source": SOURCE_DEMO_PARTNER_VMS
                    in (a.source_system, b.source_system),
                    "events": [
                        {"source_system": a.source_system, "camera_id": a.camera_id, "observed_at": a.observed_at.isoformat()},
                        {"source_system": b.source_system, "camera_id": b.camera_id, "observed_at": b.observed_at.isoformat()},
                    ],
                }
            )
    correlations.sort(key=lambda c: c["time_gap_s"])
    return {
        "correlation_window_s": config.FEDERATION_CORRELATION_WINDOW_S,
        "total_federated_events": len(rows),
        "sources_present": sorted({r.source_system for r in rows}),
        "correlated_plate_count": len(correlations),
        "correlations": correlations,
        "honesty_note": HONESTY_NOTE,
    }


@router.get("/correlations")
def get_correlations(db: Session = Depends(get_db), _principal: Principal = Depends(require_role("investigator"))):
    """Model 3's 'unified event-correlation dashboard' data source — same
    role gate as Model 1's gap-analysis (investigator+, not public)."""
    return _compute_correlations(db)


@router.get("/correlations/export.pdf")
def export_correlations_pdf(db: Session = Depends(get_db), _principal: Principal = Depends(require_role("investigator"))):
    """Model 3's 'sample federated analytics report' deliverable, reusing
    the reportlab pattern from Model 1's gap-analysis PDF — same library,
    no new dependency, same "render, don't recompute" discipline."""
    pdf_bytes = _render_correlations_pdf(_compute_correlations(db))
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=sentinel_federation_report.pdf"},
    )


def _render_correlations_pdf(report: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Sentinel Federated Correlation Report")
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Sentinel — Model 3 Federated Correlation Report", styles["Title"]),
        Paragraph(f"Generated {dt.datetime.utcnow().isoformat()}Z", styles["Normal"]),
        Spacer(1, 10),
        Paragraph(report["honesty_note"], styles["Italic"]),
        Spacer(1, 16),
    ]

    summary_rows = [
        ["Metric", "Value"],
        ["Correlation window (s)", report["correlation_window_s"]],
        ["Total federated events", report["total_federated_events"]],
        ["Source systems present", ", ".join(report["sources_present"]) or "(none)"],
        ["Correlated plates found", report["correlated_plate_count"]],
    ]
    summary_table = Table(summary_rows, colWidths=[220, 260])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements += [summary_table, Spacer(1, 16)]

    elements.append(Paragraph("Correlated plates", styles["Heading2"]))
    corr_rows = [["Plate", "Sources", "Time gap (s)", "Confidence", "Basis"]] + (
        [
            [
                c["plate"],
                " + ".join(c["sources"]),
                f"{c['time_gap_s']:.0f}",
                f"{c['correlation_confidence']:.2f}",
                "SYNTHETIC" if c["involves_synthetic_source"] else "real sources",
            ]
            for c in report["correlations"]
        ]
        or [["(none — the two real sources share no plates by construction)", "", "", "", ""]]
    )
    corr_table = Table(corr_rows, colWidths=[100, 160, 70, 70, 80])
    corr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements += [corr_table]

    doc.build(elements)
    return buf.getvalue()
