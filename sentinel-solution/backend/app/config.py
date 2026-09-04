"""Central configuration. Values are read from environment variables with
sane defaults so the service runs against the sandbox out of the box.

Per the Integrator's Guide, HLS and RTSP/WHEP are served from *different*
hosts: HLS rides the CDN (password-protected, works anywhere); RTSP/WHEP
carry raw TCP/UDP media that the CDN cannot proxy, so they're served
directly from the public static IP (or a dedicated non-proxied subdomain).
"""
import os

# CDN host — serves HLS + the camera catalogue, behind the access password
# issued by the Control Room "Request Feed Access" form.
CDN_HOST = os.environ.get("SENTINEL_CDN_HOST", "cctv.corp8.cloud")

# Public static IP (or dedicated non-proxied subdomain, e.g. stream.corp8.cloud)
# serving RTSP/WHEP directly — no Tailscale/device registration required.
STREAM_HOST = os.environ.get("SENTINEL_STREAM_HOST", "103.250.160.189")

CATALOGUE_URL = os.environ.get(
    "SENTINEL_CATALOGUE_URL", f"https://{CDN_HOST}/cameras.json"
)
RTSP_PORT = int(os.environ.get("SENTINEL_RTSP_PORT", "8554"))
WHEP_PORT = int(os.environ.get("SENTINEL_WHEP_PORT", "8889"))
WHEP_UDP_PORT = int(os.environ.get("SENTINEL_WHEP_UDP_PORT", "8189"))

# Access password issued by the Control Room registration form. Required for
# the CDN host (HLS + catalogue); sent as a bearer token / cookie depending
# on what the portal's auth flow turns out to expect — adjust
# `catalogue.py`'s request headers once you've inspected a real 401 response.
SENTINEL_ACCESS_TOKEN = os.environ.get("SENTINEL_ACCESS_TOKEN", "")

# The CDN login form (/auth/login) requires BOTH an email and the access
# password — sending password alone gets a silent 200 re-render of the login
# form, not an error, so this is easy to miss without inspecting the page.
SENTINEL_ACCESS_EMAIL = os.environ.get("SENTINEL_ACCESS_EMAIL", "")

# Reconnect policy (guide §3: start ~2s, cap ~30s, exponential backoff)
RECONNECT_INITIAL_DELAY_S = float(os.environ.get("RECONNECT_INITIAL_DELAY_S", "2"))
RECONNECT_MAX_DELAY_S = float(os.environ.get("RECONNECT_MAX_DELAY_S", "30"))
RECONNECT_BACKOFF_FACTOR = float(os.environ.get("RECONNECT_BACKOFF_FACTOR", "2"))

# How often to refresh the camera catalogue (ids/availability can change).
CATALOGUE_REFRESH_INTERVAL_S = float(os.environ.get("CATALOGUE_REFRESH_INTERVAL_S", "60"))

# Database
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./sentinel.db")

# Analytics sampling — process every Nth frame per camera to keep CPU/GPU load
# bounded across many simultaneous cameras. Tune per hardware.
ANALYTICS_FRAME_STRIDE = int(os.environ.get("ANALYTICS_FRAME_STRIDE", "5"))

# Pretrained COCO weights — good enough for car/truck/bus/motorcycle/person
# out of the box (see analytics/detector.py); no fine-tuning needed for
# vehicle-class detection, unlike plate OCR.
YOLO_WEIGHTS = os.environ.get("SENTINEL_YOLO_WEIGHTS", "yolov8n.pt")

# Low-confidence plate-read suppression (see analytics/pipeline.py): a fused
# plate confidence below this is treated as UNREAD — the vehicle is still
# logged anonymously by appearance/attributes, but the shaky plate string is
# withheld rather than spawning a false identity or false watchlist alert.
# 0.5 is a conservative default; tune against real footage.
PLATE_MIN_CONFIDENCE = float(os.environ.get("SENTINEL_PLATE_MIN_CONFIDENCE", "0.5"))

# Data-retention window (DPDP storage-limitation, see db/retention.py). Vehicle
# events/identities/alerts older than this are purged. Modelled on the UK
# National ANPR system's 12-month default (see RESEARCH_EXISTING_SYSTEMS.md);
# default here is shorter for a pilot. Audit logs are kept LONGER (see below)
# — the accountability trail should outlive the personal data it describes.
RETENTION_DAYS = int(os.environ.get("SENTINEL_RETENTION_DAYS", "30"))
AUDIT_RETENTION_DAYS = int(os.environ.get("SENTINEL_AUDIT_RETENTION_DAYS", "365"))
# How often the purge job runs, in seconds (default 6h).
RETENTION_SWEEP_INTERVAL_S = float(os.environ.get("SENTINEL_RETENTION_SWEEP_INTERVAL_S", str(6 * 3600)))

API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))
