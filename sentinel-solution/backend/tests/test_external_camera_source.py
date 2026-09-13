"""Regression coverage for Model 2's "unified viewer connecting >=2
different systems" deliverable — System B is Caltrans District 3's real
public CCTV API (see app/external_camera_source.py). No network call in
these tests: parse() is exercised against a real-shaped fixture, and
sync_into_registry() has fetch_raw() monkeypatched."""
from __future__ import annotations

from app import external_camera_source as ecs
from app.db.models import CameraRegistry

CALTRANS_FIXTURE = {
    "data": [
        {
            "cctv": {
                "index": "1",
                "location": {
                    "locationName": "Hwy 5 at Pocket",
                    "nearbyPlace": "Sacramento",
                    "latitude": "38.481128",
                    "longitude": "-121.510528",
                },
                "inService": "true",
                "imageData": {
                    "static": {
                        "currentImageURL": "https://cwwp2.dot.ca.gov/data/d3/cctv/image/hwy5atpocket/hwy5atpocket.jpg",
                    }
                },
            }
        },
        {
            # Offline — must be skipped.
            "cctv": {
                "index": "2",
                "location": {"locationName": "Hwy 50", "nearbyPlace": "Sacramento", "latitude": "1", "longitude": "2"},
                "inService": "false",
                "imageData": {"static": {"currentImageURL": "https://example.com/x.jpg"}},
            }
        },
        {
            # No image URL — must be skipped even though "in service".
            "cctv": {
                "index": "3",
                "location": {"locationName": "Hwy 80", "nearbyPlace": "Sacramento", "latitude": "1", "longitude": "2"},
                "inService": "true",
                "imageData": {"static": {"currentImageURL": ""}},
            }
        },
    ]
}


def test_parse_keeps_only_in_service_with_image():
    cams = ecs.parse(CALTRANS_FIXTURE, max_cameras=10)
    assert len(cams) == 1
    cam = cams[0]
    assert cam["id"] == "ext-caltrans-1"
    assert "Hwy 5 at Pocket" in cam["location_name"]
    assert cam["latitude"] == 38.481128
    assert cam["snapshot_image_url"].endswith("hwy5atpocket.jpg")


def test_parse_respects_max_cameras():
    # Deep-ish copy per entry — CALTRANS_FIXTURE's dicts are shared module
    # state across tests, must not be mutated in place.
    in_service_entry = CALTRANS_FIXTURE["data"][0]
    entries = []
    for i in range(5):
        cctv = dict(in_service_entry["cctv"])
        cctv["index"] = str(100 + i)
        entries.append({"cctv": cctv})
    cams = ecs.parse({"data": entries}, max_cameras=2)
    assert len(cams) == 2


def test_sync_into_registry_upserts_and_is_idempotent(session, monkeypatch):
    monkeypatch.setattr(ecs, "fetch_raw", lambda: CALTRANS_FIXTURE)

    n = ecs.sync_into_registry(session, max_cameras=10)
    assert n == 1
    row = session.get(CameraRegistry, "ext-caltrans-1")
    assert row is not None
    assert row.source_system == ecs.SOURCE_SYSTEM
    assert row.snapshot_image_url.endswith("hwy5atpocket.jpg")
    assert row.is_healthy is True
    assert "External" in row.department

    # Re-sync must update the same row, not create a duplicate.
    n2 = ecs.sync_into_registry(session, max_cameras=10)
    assert n2 == 1
    assert session.query(CameraRegistry).count() == 1


def test_sync_into_registry_never_overwrites_a_non_external_row(session, monkeypatch):
    """Defensive check: even if an id collided with a real Gujarat camera
    (should be impossible given the ext-caltrans- prefix), the sync must
    refuse to overwrite it rather than silently clobbering real registry
    metadata with external data."""
    real_cam = CameraRegistry(id="ext-caltrans-1", department="Gujarat Police", source_system=None)
    session.add(real_cam)
    session.commit()

    monkeypatch.setattr(ecs, "fetch_raw", lambda: CALTRANS_FIXTURE)
    ecs.sync_into_registry(session, max_cameras=10)

    session.refresh(real_cam)
    assert real_cam.department == "Gujarat Police"
    assert real_cam.source_system is None
