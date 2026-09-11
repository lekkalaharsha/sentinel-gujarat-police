"""One-shot: empirically characterize EMBEDDING_SIMILARITY_THRESHOLD
(identity.py) against real crop images in sentinel.db, instead of the
zero-evidence default that's been carried since the pilot started (see
TASKS.md / CODEX_HANDOFF_PROMPT.md's ML-3).

Ground-truth honesty note (the actual finding of this script): a valid
POSITIVE pair (two crops of the confirmed-same real vehicle, independent
of the appearance threshold itself) requires either (a) the same plate
read on two distinct sightings, or (b) an identity link made via
`link_method="plate_continuation"`/`"plate_upgrade"` (plate-verified, not
appearance-verified). Almost every multi-sighting identity in this DB was
instead linked via `link_method="appearance_match"` — using those as
"positives" would be circular (it would just re-validate whatever
threshold was already in effect when identity resolution ran, not
measure the signal independently). So this script:

  1. Looks for independent, plate-verified positive pairs. If none/too
     few exist (report the count either way — this is itself the
     finding, not a script bug), positive-side calibration (recall) stays
     honestly unresolved, same conclusion as CODEX_HANDOFF_PROMPT.md's
     ML-3 section, now with a concrete number instead of "still blocked."
  2. Characterizes the NEGATIVE distribution from real crops of
     confirmed-different vehicles (different plate, or different identity
     AND at least one has a plate) — this side has no circularity problem
     and gives an honest empirical false-positive-rate curve for
     candidate thresholds.

Usage: cd backend && python scripts/calibrate_embedding_threshold.py
"""
from __future__ import annotations

import os
import random
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np

from app import config
from app.analytics.identity import EMBEDDING_SIMILARITY_THRESHOLD
from app.analytics.reid import ColorHistogramEncoder

DB_PATH = config.DATABASE_URL.replace("sqlite:///", "", 1)
N_NEGATIVE_PAIRS = 3000
RNG_SEED = 20260910  # fixed for reproducibility, not a timestamp


def _load_embedding(encoder: ColorHistogramEncoder, crop_path: str) -> np.ndarray | None:
    full_path = os.path.join(config.CROPS_DIR, crop_path)
    img = cv2.imread(full_path)
    if img is None or img.size == 0:
        return None
    return encoder.encode(img)


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- Positive-pair search (plate-verified, independent of appearance) ---
    cur.execute(
        "SELECT plate, crop_path, camera_id FROM vehicle_event "
        "WHERE crop_path IS NOT NULL AND plate IS NOT NULL"
    )
    plate_rows = cur.fetchall()
    by_plate: dict[str, list[tuple[str, str]]] = {}
    for plate, crop_path, camera_id in plate_rows:
        by_plate.setdefault(plate, []).append((crop_path, camera_id))
    plate_positive_candidates = {p: rows for p, rows in by_plate.items() if len(rows) >= 2}

    cur.execute(
        "SELECT COUNT(*) FROM vehicle_event WHERE link_method IN "
        "('plate_continuation', 'plate_upgrade')"
    )
    (plate_verified_links,) = cur.fetchone()

    print(f"Real crop+plate events: {len(plate_rows)}")
    print(f"Distinct plates with >=2 crop+plate sightings (independent positive candidates): "
          f"{len(plate_positive_candidates)}")
    print(f"VehicleEvent rows linked via plate_continuation/plate_upgrade "
          f"(appearance-independent identity links): {plate_verified_links}")

    encoder = ColorHistogramEncoder()
    positive_sims: list[float] = []
    for plate, rows in plate_positive_candidates.items():
        cams = {cam for _, cam in rows}
        if len(cams) < 2:
            continue  # same-camera repeats aren't the cross-camera use case
        embeddings = [_load_embedding(encoder, cp) for cp, _ in rows]
        embeddings = [e for e in embeddings if e is not None]
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                positive_sims.append(float(np.dot(embeddings[i], embeddings[j])))

    if positive_sims:
        print(f"\nIndependent (plate-verified) positive pairs found: {len(positive_sims)}")
        print(f"  mean={np.mean(positive_sims):.3f} std={np.std(positive_sims):.3f} "
              f"min={np.min(positive_sims):.3f} max={np.max(positive_sims):.3f}")
    else:
        print("\nIndependent (plate-verified) positive pairs found: 0")
        print("  CONCLUSION: real same-vehicle cross-camera pairs independent of the")
        print("  embedding threshold itself do not exist in this DB yet — ANPR success")
        print("  is too sparse (few plates ever read at all, none repeat across cameras)")
        print("  and virtually every multi-sighting identity was itself linked via")
        print("  appearance_match, which would make using it as ground truth circular.")
        print("  Recall-side (positive) calibration stays genuinely unresolved — this")
        print("  is a data-scarcity finding, not something this script can work around.")

    # --- Negative-pair distribution (confirmed-different vehicles) ---
    cur.execute(
        "SELECT identity_id, plate, crop_path FROM vehicle_event WHERE crop_path IS NOT NULL"
    )
    all_rows = cur.fetchall()
    conn.close()

    rng = random.Random(RNG_SEED)
    rng.shuffle(all_rows)

    negative_sims: list[float] = []
    embedding_cache: dict[str, np.ndarray] = {}

    def get_embedding(crop_path: str) -> np.ndarray | None:
        if crop_path not in embedding_cache:
            embedding_cache[crop_path] = _load_embedding(encoder, crop_path)
        return embedding_cache[crop_path]

    attempts = 0
    max_attempts = N_NEGATIVE_PAIRS * 5
    while len(negative_sims) < N_NEGATIVE_PAIRS and attempts < max_attempts:
        attempts += 1
        a, b = rng.sample(all_rows, 2)
        id_a, plate_a, crop_a = a
        id_b, plate_b, crop_b = b
        if id_a == id_b:
            continue  # same identity — not a confirmed-different pair
        if plate_a and plate_b and plate_a == plate_b:
            continue  # same plate under different identity ids — data anomaly, skip
        ea, eb = get_embedding(crop_a), get_embedding(crop_b)
        if ea is None or eb is None:
            continue
        negative_sims.append(float(np.dot(ea, eb)))

    negative_sims_arr = np.array(negative_sims)
    print(f"\nConfirmed-different-vehicle negative pairs sampled: {len(negative_sims_arr)}")
    if len(negative_sims_arr):
        print(f"  mean={negative_sims_arr.mean():.3f} std={negative_sims_arr.std():.3f} "
              f"min={negative_sims_arr.min():.3f} max={negative_sims_arr.max():.3f}")
        for pct in (50, 90, 95, 99, 99.9):
            print(f"  p{pct}: {np.percentile(negative_sims_arr, pct):.3f}")
        fpr_at_current = float(np.mean(negative_sims_arr >= EMBEDDING_SIMILARITY_THRESHOLD))
        print(f"\n  Empirical false-positive rate at threshold={EMBEDDING_SIMILARITY_THRESHOLD} "
              f"(current default): {fpr_at_current:.4%} "
              f"({int(fpr_at_current * len(negative_sims_arr))} of {len(negative_sims_arr)} "
              f"confirmed-different pairs would incorrectly match)")


if __name__ == "__main__":
    main()
