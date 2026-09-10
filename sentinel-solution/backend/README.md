# Sentinel backend

FastAPI backend for the Sentinel solution (registry + GIS, live viewing,
plate-first tracking, cross-camera identity). Full architecture, run and
demo instructions live in `../README.md` — this file covers backend-only
concerns not already documented there.

## Tests

Regression suite for the three riskiest analytics modules
(`analytics/identity.py`, `analytics/tracker.py`, `analytics/geo.py`) —
the SWE-4 gap; each has had a real bug caught only by manual testing. See
`tests/` and `../docs/REVIEW_FINDINGS.md`.

The suite is fully self-contained: in-memory SQLite DB, no camera/sandbox
access, no ML dependencies (ultralytics/paddleocr). Run from this
directory:

```
python -m pytest tests -v
```

`pytest` is pinned in `requirements.txt`. Adding a test is just a new
`tests/test_*.py` file; the `session` fixture (fresh in-memory DB per test)
lives in `tests/conftest.py`.