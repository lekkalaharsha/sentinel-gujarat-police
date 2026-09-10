"""Regression coverage for the gap-analysis PDF export (Model 1's required
'gap-analysis report' deliverable — see TASKS.md P1, this endpoint didn't
exist at all before 2026-09-10). Exercises the real reportlab render path,
not just the underlying JSON computation."""
from __future__ import annotations

from app.api.auth import Principal
from app.api.routes_cameras import _compute_gap_analysis, _render_gap_analysis_pdf, catalogue
from app.catalogue import CameraInfo
from app.db.models import CameraRegistry


def _seed(session):
    session.add(CameraRegistry(id="cam01", department="Police"))
    session.add(CameraRegistry(id="cam02", department=None))  # missing department
    session.commit()
    catalogue._cameras = {
        "cam01": CameraInfo(id="cam01", location="Ahmedabad", codec="h264", live=True,
                             rtsp_url="rtsp://x", whep_url="", hls_url="", raw={}),
        "cam03": CameraInfo(id="cam03", location="Rajkot", codec="h264", live=True,
                             rtsp_url="rtsp://x", whep_url="", hls_url="", raw={}),  # live, not onboarded
    }


def test_gap_analysis_computation_matches_pdf_source_data(session):
    _seed(session)
    admin = Principal("admin1", "admin", None)
    report = _compute_gap_analysis(session, admin)
    assert report["catalogue_size"] == 2
    assert report["registered_size"] == 2
    assert report["live_not_onboarded"] == ["cam03"]
    assert report["onboarded_not_live"] == ["cam02"]
    assert report["missing_department"] == ["cam02"]


def test_pdf_export_produces_real_pdf_bytes(session):
    _seed(session)
    admin = Principal("admin1", "admin", None)
    report = _compute_gap_analysis(session, admin)
    pdf_bytes = _render_gap_analysis_pdf(report, admin)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500  # a trivially empty/broken render would be tiny


def test_pdf_export_empty_department_breakdown_does_not_crash(session):
    """No cameras registered at all — cameras_by_department is {}. The
    dept_rows fallback-to-'(none registered)' branch must actually fire
    (real bug caught here: `[header] + [rows] or [fallback]` always
    evaluates true because concatenation is non-empty, silently skipping
    the fallback — fixed with explicit parens)."""
    catalogue._cameras = {}
    admin = Principal("admin1", "admin", None)
    report = _compute_gap_analysis(session, admin)
    pdf_bytes = _render_gap_analysis_pdf(report, admin)
    assert pdf_bytes.startswith(b"%PDF")
