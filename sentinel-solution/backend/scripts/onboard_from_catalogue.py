"""One-shot script: pull the real sandbox catalogue and bulk-onboard every
camera into the registry with a best-guess department tag, closing the
"no department attribution anywhere" gap (see README/architecture review).

Why this is a script, not automatic: `cameras.json` only returns {id, name}
(see catalogue.py's CameraInfo.from_api comment) — it does NOT return a
department field. The sandbox dataset spans 5 known departments (Health,
Police, GSRTC, Panchayat, Municipal Corporation — HACKATHON_DETAILS.md §12),
so this infers department from keywords in each camera's `name`/`location`
string. That's a heuristic, not ground truth — ALWAYS review the output
before trusting it in front of a jury; a camera named just "CAM-14" with no
department-suggestive words will fall into "Unassigned" and needs a human
to look at the actual feed and tag it manually via POST /cameras.

Usage:
    cd backend
    SENTINEL_ACCESS_TOKEN=<password> SENTINEL_ADMIN_API_KEY=<key from /auth/api-keys> \\
        python scripts/onboard_from_catalogue.py [--api-base http://localhost:8000] [--dry-run]

Never pass tokens/keys as command-line arguments (they'd land in shell
history and process listings) — always via environment variables, per this
project's secret-handling rule.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests

from app import config
from app.catalogue import CatalogueClient

# Keyword -> department. Checked in order; first match wins. Extend this
# list once you've actually seen the real cameras.json `name` values —
# these are best guesses from HACKATHON_DETAILS.md §12's department names,
# not confirmed against real data.
DEPARTMENT_KEYWORDS = [
    (("hospital", "health", "civil", "phc", "chc"), "Health"),
    (("police", "pcr", "chowky", "thana", "traffic"), "Police"),
    (("gsrtc", "bus", "depot", "st stand", "st-stand"), "GSRTC"),
    (("panchayat", "gram", "village"), "Panchayat"),
    (("municipal", "corporation", "amc", "smc", "vmc", "rmc"), "Municipal Corporation"),
]


def infer_department(name: str | None) -> str | None:
    if not name:
        return None
    lowered = name.lower()
    for keywords, department in DEPARTMENT_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return department
    return None


# Area-centroid GPS, NOT measured camera GPS — the catalogue provides no
# coordinates at all (see CameraInfo.from_api), so this is a best-effort
# fallback for the GIS map rather than leaving every camera un-plotted.
# Deliberately conservative: only town/city names confidently identified are
# listed here. An unmatched/ambiguous name (e.g. a small village name with
# no confident reference) is left with NO coordinates rather than a guessed
# one — a wrong pin on a police GIS map is worse than an honestly-missing
# pin. Always verify against real survey data before operational use.
AREA_COORDS: dict[str, tuple[float, float]] = {
    "ahmedabad": (23.0225, 72.5714),
    "gandhinagar": (23.2156, 72.6369),
    "adalaj": (23.1667, 72.5833),
    "junagadh": (21.5222, 70.4579),
    "somnath": (20.8880, 70.4017),
    "gir-somnath": (20.8880, 70.4017),
    "rajkot": (22.3039, 70.8022),
    "navsari": (20.9467, 72.9520),
    "bilimora": (20.7667, 72.9500),
    "patan": (23.8493, 72.1266),
    "gandhidham": (23.0753, 70.1337),
    "dehgam": (23.1667, 72.8167),
    # Specific Ahmedabad landmarks/localities recognized with confidence —
    # kept separate from the city-level "ahmedabad" entry (not added above)
    # because most Ahmedabad camera names in this catalogue are streets/
    # circles too specific and numerous to hardcode reliably; these three
    # are well-known enough to be a safe exception.
    "paldi": (23.0169, 72.5645),
    "visat": (23.0754, 72.5514),
    "chiman bhai bridge": (23.0326, 72.5764),
}


def infer_coords(name: str | None) -> tuple[float | None, float | None]:
    if not name:
        return None, None
    lowered = name.lower()
    for keyword, coords in AREA_COORDS.items():
        if keyword in lowered:
            return coords
    return None, None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--dry-run", action="store_true", help="print the inferred mapping, don't call the API")
    args = parser.parse_args()

    admin_key = os.environ.get("SENTINEL_ADMIN_API_KEY")
    if not args.dry_run and not admin_key:
        print("SENTINEL_ADMIN_API_KEY is required unless --dry-run is set (see /auth/api-keys)", file=sys.stderr)
        sys.exit(1)

    catalogue = CatalogueClient()
    cameras = catalogue.refresh()
    if not cameras:
        print("catalogue is empty — check SENTINEL_ACCESS_TOKEN is set and the sandbox is reachable", file=sys.stderr)
        sys.exit(1)

    payload = []
    unassigned = []
    no_coords = []
    for cam_id, cam in cameras.items():
        source_name = cam.raw.get("name") or cam.location
        department = infer_department(source_name)
        lat, lon = infer_coords(source_name)
        if department is None:
            unassigned.append(cam_id)
        if lat is None:
            no_coords.append(cam_id)
        payload.append({
            "id": cam_id, "department": department, "location_name": cam.location,
            "latitude": lat, "longitude": lon,
        })

    print(f"{len(payload)} cameras found; {len(unassigned)} could not be classified by keyword: {unassigned}")
    print(f"{len(no_coords)} have no area-centroid match (left un-plotted, not guessed): {no_coords}")
    if args.dry_run:
        for entry in payload:
            coord_str = f"{entry['latitude']:.3f},{entry['longitude']:.3f}" if entry["latitude"] else "no-coords"
            print(f"  {entry['id']}: {entry['department'] or 'UNASSIGNED'} ({entry['location_name']}) [{coord_str}]")
        return

    resp = requests.post(
        f"{args.api_base}/cameras/bulk",
        json=payload,
        headers={"X-Sentinel-API-Key": admin_key},
        timeout=30,
    )
    resp.raise_for_status()
    print(resp.json())
    print(
        "\nReview /cameras/gap-analysis for 'missing_department' entries and "
        "correct them manually via POST /cameras — this script's department "
        "guesses are a starting point, not verified ground truth."
    )


if __name__ == "__main__":
    main()
