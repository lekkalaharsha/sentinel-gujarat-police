"""Evidence-labelled camera ANPR suitability from real event history.

This deliberately scores only what Sentinel currently measures: whether a
stored VehicleEvent produced a confident plate.  Vehicle bounding boxes are
not plate bounding boxes, and this deployment has no blur, glare, illuminance,
calibration, distance, or zoom measurements, so none is guessed here.
"""
from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from ..db.models import VehicleEvent

MINIMUM_SAMPLE_EVENTS = 5
CAPABLE_READ_RATE = 0.60


def anpr_suitability_by_camera(db: Session, camera_ids: list[str]) -> dict[str, dict]:
    """Return real OCR-read history and an explicitly limited recommendation.

    ``MARGINAL`` with ``insufficient_sample`` is intentionally not promoted
    to CAPABLE/UNSUITABLE until enough real detections exist to support that
    judgment.
    """
    if not camera_ids:
        return {}
    rows = (
        db.query(
            VehicleEvent.camera_id,
            func.count(VehicleEvent.id).label("events"),
            func.coalesce(func.sum(case((VehicleEvent.plate.is_not(None), 1), else_=0)), 0).label("reads"),
        )
        .filter(VehicleEvent.camera_id.in_(camera_ids))
        .group_by(VehicleEvent.camera_id)
        .all()
    )
    counts = {row.camera_id: (int(row.events), int(row.reads)) for row in rows}
    result: dict[str, dict] = {}
    for camera_id in camera_ids:
        events, reads = counts.get(camera_id, (0, 0))
        rate = (reads / events) if events else None
        if events < MINIMUM_SAMPLE_EVENTS:
            classification, data_status = "MARGINAL", "insufficient_sample"
            recommendation = "Collect at least 5 real vehicle events before changing camera placement or optics."
        elif rate is not None and rate >= CAPABLE_READ_RATE:
            classification, data_status = "CAPABLE", "measured"
            recommendation = "Continue monitoring real plate-read rate; no placement change is indicated by available data."
        elif reads:
            classification, data_status = "MARGINAL", "measured"
            recommendation = "Review framing and zoom, then collect another real sample after adjustment."
        else:
            classification, data_status = "UNSUITABLE", "measured"
            recommendation = "Reposition or zoom the camera for plates, then validate with real ANPR events."
        result[camera_id] = {
            "classification": classification,
            "data_status": data_status,
            "sample_vehicle_events": events,
            "confirmed_plate_reads": reads,
            "ocr_success_rate": rate,
            "measured_factors": ["confirmed_plate_read_history"],
            "unmeasured_factors": [
                "plate_pixel_width", "plate_pixel_height", "blur", "glare_or_low_light",
                "camera_resolution", "distance_or_zoom_proxy",
            ],
            "recommendation": recommendation,
        }
    return result
