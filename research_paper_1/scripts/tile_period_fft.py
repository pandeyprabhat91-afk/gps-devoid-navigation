#!/usr/bin/env python3
"""
Action 4a (research_paper_1): estimate the furrow period and axis per frame
from the satellite tile itself, and test whether it explains the alias offset
directions.

Rationale. The 10th iteration's measure_furrow_axis.py ran one FFT over a
whole radius-1 composite patch (~750 m) and was inconclusive: fields at
different orientations mix inside a patch that large. This script estimates
the dominant periodicity LOCALLY around each frame's locked position: crop
the patch around est, autocorrelate, take the strongest peak in the 8-80 m
band. If the alias is a furrow lock, the alias offset direction should align
with the local periodicity direction (folded to 180 deg).

Input: results/action3_coherence.json (R04 contiguous frames with est/gt).
Output: results/action4_period.json (per-frame period, bearing, peak strength).
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from kp_vio.map_matching.tile_database import TileDatabase
from kp_vio.map_matching.geo_utils import (
    latlon_to_tile,
    tile_to_latlon,
    tile_ground_resolution,
)
from comprehensive_scene_test import DATA_ROOT, TILE_DB, ZOOM, TILE_SIZE

MIN_PERIOD_M = 8.0
MAX_PERIOD_M = 80.0
CROP_PX = 500


def latlon_to_patch_px(lat, lon, tx, ty, radius=1):
    """Pixel coords in a radius-r patch centred on tile (tx, ty)."""
    lat_nw, lon_nw = tile_to_latlon(tx - radius, ty - radius, ZOOM)
    lat_se, lon_se = tile_to_latlon(tx + radius + 1, ty + radius + 1, ZOOM)
    side = (2 * radius + 1) * TILE_SIZE
    px = (lon - lon_nw) / (lon_se - lon_nw) * side
    py = (lat - lat_nw) / (lat_se - lat_nw) * side
    return px, py


def autocorr_peak(gray_crop):
    """Detrended autocorrelation; strongest LOCAL maximum in the period band."""
    x = gray_crop.astype(np.float64)
    x = x - cv2.GaussianBlur(gray_crop, (0, 0), sigmaX=25.0)
    x -= x.mean()
    f = np.fft.fft2(x)
    a = np.fft.ifft2(f * np.conj(f)).real
    a = np.fft.fftshift(a)
    a /= max(a[a.shape[0] // 2, a.shape[1] // 2], 1e-12)
    h, w = a.shape
    cy, cx = h // 2, w // 2
    r_min, r_max = 8, 80  # px: ~9.5-95 m at 1.19 m/px
    # Strongest local maximum (non-maximum suppressed) at r in [r_min, r_max].
    best = None
    max_r = min(h // 2, w // 2) - 2
    for dy in range(-max_r, max_r + 1):
        for dx in range(-max_r, max_r + 1):
            r = math.hypot(dx, dy)
            if not (r_min <= r <= r_max):
                continue
            v = a[cy + dy, cx + dx]
            local = True
            for oy in (-1, 0, 1):
                for ox in (-1, 0, 1):
                    if oy == 0 and ox == 0:
                        continue
                    if a[cy + dy + oy, cx + dx + ox] >= v:
                        local = False
                        break
                if not local:
                    break
            if local and (best is None or v > best[0]):
                best = (v, dx, dy)
    return best


def main() -> int:
    data = json.loads((ROOT / "results" / "action3_coherence.json").read_text())
    frames = data["04"]

    out = []
    with TileDatabase(TILE_DB, zoom=ZOOM) as db:
        for i, fr in enumerate(frames):
            lat, lon = fr["est_lat"], fr["est_lon"]
            tx, ty = latlon_to_tile(lat, lon, ZOOM)
            patch = db.get_patch(ZOOM, tx, ty, radius=1)
            if patch is None:
                continue
            gsd = tile_ground_resolution(lat, ZOOM, TILE_SIZE)
            px, py = latlon_to_patch_px(lat, lon, tx, ty)
            x0, y0 = int(round(px - CROP_PX / 2)), int(round(py - CROP_PX / 2))
            crop = patch[max(0, y0) : y0 + CROP_PX, max(0, x0) : x0 + CROP_PX]
            if crop.shape[0] < 100 or crop.shape[1] < 100:
                continue
            g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            v, dx, dy = autocorr_peak(g)
            if v is None:
                continue
            period = math.hypot(dx, dy) * gsd
            # Bearing in NED: dx is east, -dy is north.
            brg = math.degrees(math.atan2(dx, -dy)) % 180.0
            err_brg = math.degrees(math.atan2(fr["e"], fr["n"])) % 180.0
            d_ang = abs(((brg - err_brg + 90) % 180.0) - 90.0)
            band = period >= MIN_PERIOD_M and period <= MAX_PERIOD_M and v >= 0.25
            out.append(
                {
                    "idx": fr["idx"],
                    "err_m": fr["err"],
                    "period_m": period,
                    "bearing_deg": brg,
                    "err_bearing_deg": err_brg,
                    "d_angle_deg": d_ang,
                    "peak_strength": float(v),
                    "in_band": bool(band),
                }
            )
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(frames)}", flush=True)

    if not out:
        print("no frames")
        return 1

    def med(a):
        a = sorted(a)
        return a[len(a) // 2]

    groups = {
        "good": [f for f in out if f["err_m"] < 20],
        "mid": [f for f in out if 20 <= f["err_m"] < 50],
        "alias": [f for f in out if f["err_m"] >= 50],
    }
    print(f"\nper-group alignment of local periodicity vs error bearing:")
    print(
        f"{'group':>7} {'n':>5} {'in_band%':>9} {'median period':>14} "
        f"{'median |d_ang|':>15} {'peak str':>9}"
    )
    for g, fs in groups.items():
        band = [f for f in fs if f["in_band"]]
        if not fs:
            continue
        print(
            f"{g:>7} {len(fs):>5} {100.0 * len(band) / len(fs):>8.0f}% "
            f"{med([f['period_m'] for f in band]) if band else float('nan'):>13.1f} "
            f"{med([f['d_angle_deg'] for f in fs]):>14.1f} "
            f"{med([f['peak_strength'] for f in fs]):>9.3f}"
        )

    (ROOT / "results" / "action4_period.json").write_text(json.dumps(out, indent=2))
    print(f"wrote results/action4_period.json ({len(out)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
