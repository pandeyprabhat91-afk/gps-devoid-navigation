#!/usr/bin/env python3
"""
Action 3 (research_paper_1): temporal coherence curve of the alias offset.

Claim under test (Finding U, 10th iteration). The sub-tile aliases are not
independent per-frame errors: the repetitive structure the matcher locks onto
translates with the aircraft, so the alias offset a_i = est_i - truth_i is
approximately CONSTANT across consecutive frames. That is why consistency-based
rejection discriminates backwards. This script measures the coherence directly.

Measurement 1 (truth-referenced, contiguous frames). GT-tile matching over the
FIRST N CONTIGUOUS frames of the flight (step-sampled n=40 breaks
consecutiveness, which is what a coherence question needs). For frame lag L,
median |a_i - a_{i+L}| within each error group. Groups: good (<20 m),
mid (20-50), alias (>=50 m). Null: offsets shuffled across the group (10
trials). Prediction if Finding U holds: alias-group distances stay small and
flat in L, good-group larger, null largest.

Measurement 2 (deployed view, same contiguity question) on the step-sampled
fix pool: fix-minus-prior vector per frame, lag analysis, R04 sub-tile vs
R06 whole-tile vs R03 control.

Usage:
    python scripts/coherence_curve.py --n 40 --regions 03,04
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
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
    tile_ground_resolution,
)
from kp_vio.map_matching.feature_matcher import match_pooled_multi
from kp_vio.map_matching.dem import DEMGrid
from comprehensive_scene_test import (
    DATA_ROOT,
    TILE_DB,
    DEM_CACHE,
    ZOOM,
    QUERY_SCALE,
    TILE_SIZE,
    CAMERA_K,
    haversine_m,
)
from smoke_gim_precision import solve_position
from diag_gim_probe import _clahe, _gray

R_EARTH = 6378137.0
MIN_INLIERS = 15


def median(a):
    a = sorted(a)
    return a[len(a) // 2] if a else float("nan")


def ne(lat1, lon1, lat2, lon2):
    return (
        math.radians(lat2 - lat1) * R_EARTH,
        math.radians(lon2 - lon1) * R_EARTH * math.cos(math.radians(lat1)),
    )


def collect_contiguous(region, n):
    """GT-tile signed offsets over the first n CONTIGUOUS frames; n<=0 = all."""
    with open(DATA_ROOT / region / f"{region}.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    if n > 0:
        rows = rows[:n]
    dem = DEMGrid.load(DEM_CACHE, region)
    out = []
    with TileDatabase(TILE_DB, zoom=ZOOM) as db:
        for i, row in enumerate(rows):
            gt_lat, gt_lon = float(row["lat"]), float(row["lon"])
            gt_alt = float(row["height"])
            alt = dem.agl(gt_alt, gt_lat, gt_lon) if dem else gt_alt
            p = DATA_ROOT / region / "drone" / row["filename"]
            if not p.exists():
                continue
            img = cv2.imread(str(p))
            if img is None:
                continue
            if QUERY_SCALE != 1.0:
                img = cv2.resize(
                    img,
                    None,
                    fx=QUERY_SCALE,
                    fy=QUERY_SCALE,
                    interpolation=cv2.INTER_AREA,
                )
            tx, ty = latlon_to_tile(gt_lat, gt_lon, ZOOM)
            patch = db.get_patch(ZOOM, tx, ty, radius=1)
            if patch is None:
                continue
            q = _clahe(_gray(img))
            r = _clahe(_gray(patch))
            fx = float(CAMERA_K[0, 0])
            if alt > 0 and fx > 0:
                ratio = (alt / fx) / tile_ground_resolution(gt_lat, ZOOM, TILE_SIZE)
                if ratio < 0.85:
                    q = cv2.resize(
                        q, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA
                    )
                elif ratio > 1.15:
                    inv = 1.0 / ratio
                    r = cv2.resize(
                        r, None, fx=inv, fy=inv, interpolation=cv2.INTER_AREA
                    )
            qp, tp, _ = match_pooled_multi(q, r, ratio_test=0.75)
            sol = solve_position(qp, tp, q.shape, tx, ty)
            if sol is None or sol[2] < MIN_INLIERS:
                continue
            est_lat, est_lon, n_in = sol
            north = math.radians(est_lat - gt_lat) * R_EARTH
            east = (
                math.radians(est_lon - gt_lon)
                * R_EARTH
                * math.cos(math.radians(gt_lat))
            )
            out.append(
                {
                    "idx": i,
                    "filename": row["filename"],
                    "inliers": n_in,
                    "n": north,
                    "e": east,
                    "err": haversine_m(gt_lat, gt_lon, est_lat, est_lon),
                    "est_lat": est_lat,
                    "est_lon": est_lon,
                    "gt_lat": gt_lat,
                    "gt_lon": gt_lon,
                }
            )
    return out


def lag_curve(frames, lags, trials=10, seed=1992):
    rng = random.Random(seed)
    groups = sorted({f["group"] for f in frames})
    out = {}
    for lag in lags:
        out[lag] = {}
        for g in groups:
            gs = [f for f in frames if f["group"] == g]
            by_idx = {}
            for f in gs:
                by_idx.setdefault(f["idx"], []).append(f)
            dists = []
            for f in gs:
                for m_ in by_idx.get(f["idx"] + lag, []):
                    dists.append(math.hypot(f["n"] - m_["n"], f["e"] - m_["e"]))
            nulls = []
            for _ in range(trials):
                offs = [(f["n"], f["e"]) for f in gs]
                rng.shuffle(offs)
                nd = []
                for f, (n2, e2) in zip(gs, offs):
                    for m_ in by_idx.get(f["idx"] + lag, []):
                        nd.append(math.hypot(f["n"] - n2, f["e"] - e2))
                nulls.append(median(nd))
            out[lag][g] = {
                "median": median(dists),
                "null": median(nulls),
                "n_pairs": len(dists),
            }
    return out


def print_curve(title, frames, lags):
    print(f"\n=== {title} ===")
    counts = {
        g: sum(1 for f in frames if f["group"] == g)
        for g in sorted({f["group"] for f in frames})
    }
    print("groups: " + " ".join(f"{g}={counts[g]}" for g in counts))
    curve = lag_curve(frames, lags)
    hdr = f"{'lag':>4} " + " ".join(f"{g + ' med/null':>24}" for g in sorted(counts))
    print(hdr)
    for lag in lags:
        cells = []
        for g in sorted(counts):
            c = curve[lag].get(g, {})
            cells.append(
                f"{c['median']:.1f}/{c['null']:.1f} (n={c['n_pairs']})"
                if c.get("n_pairs")
                else "-"
            )
        print(f"{lag:>4} " + " ".join(f"{c:>24}" for c in cells))
    return curve


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", default="03,04")
    ap.add_argument(
        "--n",
        type=int,
        default=0,
        help="contiguous frames to collect per region; 0 = all",
    )
    ap.add_argument("--lags", default="1,2,3,5,8")
    ap.add_argument("--out", default=str(ROOT / "results" / "action3_coherence.json"))
    args = ap.parse_args()
    lags = [int(x) for x in args.lags.split(",")]

    saved = {}
    for region in args.regions.split(","):
        region = region.strip()
        print(f"collecting contiguous R{region} ...", flush=True)
        frames = collect_contiguous(region, args.n)
        tagged = []
        for f in frames:
            g = "good" if f["err"] < 20 else "mid" if f["err"] < 50 else "alias"
            tagged.append({**f, "group": g})
        saved[region] = frames
        print_curve(f"R{region} truth-referenced (GT tile, contiguous)", tagged, lags)

    # Measurement 2: deployed view on the step-sampled d300 pool.
    pool_path = ROOT / "results" / "action2_pool_d300.json"
    if pool_path.exists():
        pool = json.loads(pool_path.read_text())
        for region in ("03", "04", "06"):
            if region not in pool["per_region"]:
                continue
            frames = []
            for f in pool["per_region"][region]:
                dn, de = ne(f["prior_lat"], f["prior_lon"], f["est_lat"], f["est_lon"])
                frames.append(
                    {
                        "idx": f["idx"],
                        "n": dn,
                        "e": de,
                        "group": ("good" if f["err_m"] <= 50 else "alias"),
                    }
                )
            print_curve(
                f"R{region} deployed view (fix-minus-prior, d300)", frames, lags
            )

    Path(args.out).write_text(json.dumps(saved, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
