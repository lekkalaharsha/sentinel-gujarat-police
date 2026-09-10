"""Shared fixtures for the regression test suite (SWE-4).

The backend is a plain package (no packaging/install), so tests run with
`backend/` on sys.path to make `app.*` importable regardless of the
invocation directory. Everything below is self-contained: an in-memory
SQLite DB per test (see the identity.py/geo.py DB-backed resolver paths) and
no network or ML dependencies.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base


@pytest.fixture()
def session():
    """Fresh in-memory SQLite session per test. `create_all` on a brand-new
    engine builds the partial-unique index on vehicle_identity.plate that
    identity.py's IntegrityError handling depends on, mirroring the real DB."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()
    engine.dispose()