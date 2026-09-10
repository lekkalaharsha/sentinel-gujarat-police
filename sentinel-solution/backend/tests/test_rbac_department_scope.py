"""Department-scoped RBAC (Model 1's "department-wise RBAC" deliverable —
see api/auth.py's department_scope and api/routes_cameras.py's
_registered_cameras). Regression coverage for the failure mode a future
refactor could reintroduce: a non-admin key silently seeing another
department's cameras."""
from __future__ import annotations

from app.api.auth import Principal, department_scope
from app.api.routes_cameras import _registered_cameras
from app.db.models import CameraRegistry


def _seed(session):
    session.add(CameraRegistry(id="cam_police", department="Police"))
    session.add(CameraRegistry(id="cam_health", department="Health"))
    session.add(CameraRegistry(id="cam_unassigned", department=None))
    session.commit()


def test_admin_sees_all_departments(session):
    _seed(session)
    admin = Principal("admin1", "admin", None)
    assert department_scope(admin) is None
    ids = {c.id for c in _registered_cameras(session, admin)}
    assert ids == {"cam_police", "cam_health", "cam_unassigned"}


def test_department_scoped_investigator_sees_only_own_department(session):
    _seed(session)
    police_inv = Principal("inv1", "investigator", "Police")
    assert department_scope(police_inv) == "Police"
    ids = {c.id for c in _registered_cameras(session, police_inv)}
    assert ids == {"cam_police"}


def test_department_scoped_investigator_cannot_see_other_departments(session):
    _seed(session)
    health_inv = Principal("inv2", "investigator", "Health")
    ids = {c.id for c in _registered_cameras(session, health_inv)}
    assert "cam_police" not in ids
    assert ids == {"cam_health"}


def test_no_department_key_is_unrestricted(session):
    """An investigator/viewer key provisioned with department=None (the
    ApiKeyEntry field is nullable) is NOT scoped — matches the "admin OR no
    department set = unrestricted" contract in department_scope's
    docstring, not a bug where an unset department silently blocks
    everything."""
    _seed(session)
    unscoped_inv = Principal("inv3", "investigator", None)
    assert department_scope(unscoped_inv) is None
    ids = {c.id for c in _registered_cameras(session, unscoped_inv)}
    assert ids == {"cam_police", "cam_health", "cam_unassigned"}


def test_viewer_role_also_department_scoped(session):
    _seed(session)
    viewer = Principal("v1", "viewer", "Police")
    ids = {c.id for c in _registered_cameras(session, viewer)}
    assert ids == {"cam_police"}
