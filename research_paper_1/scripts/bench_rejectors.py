#!/usr/bin/env python3
"""
Action 2 (research_paper_1): backwards-rate benchmark of PUBLISHED rejection
methods over the same fix pool.

Question. Finding U (10th iteration, re-measured in Action 1) showed the
sequential-consistency filter keeps fatal fixes at a HIGHER rate than good
fixes on R04/R06 at drift 150-300 m. That is one hand-rolled filter. The paper
claim needs the comparison the field would ask for: run the published rejection
methods -- ORB-SLAM's 3-consecutive-keyframe rule, PCM (Kimera-RPGO), a
VINS-Fusion-style robust frame alignment, and the prior-ratio gate -- over the
SAME accepted-fix pool and report the same metric.

Metric per method and setting: good-kept% / fatal-kept% with denominators
inline; the "discrimination ratio" is good-kept% / fatal-kept%. Ratio > 1
discriminates forward (rejection works); ratio <= 1 discriminates backwards or
neutrally. A method passes the project's adoption bar (10th iteration, Step 3)
only if fatal cut >= 25% AND good kept >= 80%.

Pool. Production MapMatcher (multi_feature, ncc_verify=0.30, DEM/AGL active,
min_inliers=10) over step-sampled frames at the given drift. Every fix stores
estimate, prior, ground truth (for the oracle diagnostic ONLY -- ground truth
never enters any deployed-signal rejector), inliers, and the harness-reported
prior RMS.

Usage:
    python scripts/bench_rejectors.py --collect --drift 300 --regions 03,04,06 --n 40
    python scripts/bench_rejectors.py --analyze --pools d150,d300,d600
"""

from __future__ import annotations

import argparse
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
from kp_vio.map_matching.map_matcher import MapMatcher
from kp_vio.map_matching.dem import DEMGrid
from comprehensive_scene_test import (
    DATA_ROOT,
    TILE_DB,
    RETRIEVAL_INDEX,
    FEATURE_CACHE,
    DEM_CACHE,
    ZOOM,
    QUERY_SCALE,
    TILE_SIZE,
    CAMERA_K,
    haversine_m,
    ned_to_latlon,
    offset_latlon,
    DriftModel,
)

FATAL_M = 50.0
R_EARTH = 6378137.0
RESULTS = ROOT / "results"


def ne_delta(lat1, lon1, lat2, lon2):
    north = math.radians(lat2 - lat1) * R_EARTH
    east = math.radians(lon2 - lon1) * R_EARTH * math.cos(math.radians(lat1))
    return north, east


def collect(region, n, drift_m, seed, ncc, min_inliers):
    with open(DATA_ROOT / region / f"{region}.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    step = max(1, len(rows) // n)
    rows = rows[::step][:n]

    origin_lat, origin_lon = float(rows[0]["lat"]), float(rows[0]["lon"])
    drift = DriftModel(drift_m, seed, len(rows))
    dem = DEMGrid.load(DEM_CACHE, region)

    fixes = []
    with TileDatabase(TILE_DB, zoom=ZOOM) as db:
        m = MapMatcher(
            db=db,
            zoom=ZOOM,
            origin_ll=(origin_lat, origin_lon, 0.0),
            K=CAMERA_K,
            retrieval_index=RETRIEVAL_INDEX,
            tile_size=TILE_SIZE,
            retrieval_k=10,
            min_inliers=min_inliers,
            feature_cache=FEATURE_CACHE,
            multi_feature=True,
            ncc_verify=ncc,
            dem=dem,
        )
        for i, row in enumerate(rows):
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
            gt_lat, gt_lon = float(row["lat"]), float(row["lon"])
            dn, de = drift.advance()
            plat, plon = offset_latlon(gt_lat, gt_lon, dn, de)
            rms = drift.rms_uncertainty()
            res = m.match(img, plat, plon, pred_alt_m=float(row["height"]))
            if not res.success:
                continue
            la, lo = ned_to_latlon(
                res.pos_ned[0], res.pos_ned[1], origin_lat, origin_lon
            )
            fixes.append(
                {
                    "idx": i,
                    "est_lat": la,
                    "est_lon": lo,
                    "prior_lat": plat,
                    "prior_lon": plon,
                    "gt_lat": gt_lat,
                    "gt_lon": gt_lon,
                    "err_m": haversine_m(gt_lat, gt_lon, la, lo),
                    "prior_rms_m": rms,
                    "inliers": int(getattr(res, "n_inliers", 0) or 0),
                }
            )
    return fixes, len(rows)


# --------------------------------------------------------------------------
# Rejectors. Every one takes the per-region fix list and a settings dict and
# returns the kept subset. None of them sees ground truth.
# --------------------------------------------------------------------------


def _consistent(f, g, tol):
    en, ee = ne_delta(f["prior_lat"], f["prior_lon"], g["prior_lat"], g["prior_lon"])
    on, oe = ne_delta(f["est_lat"], f["est_lon"], g["est_lat"], g["est_lon"])
    return math.hypot(on - en, oe - ee) <= tol


def reject_seq(fixes, window, tol, min_support=1):
    """Sequential consistency (10th iteration, Step 3): a fix survives only if
    >= min_support neighbours within +/-window agree within tol, motion
    compensated by priors."""
    kept = []
    for f in fixes:
        support = 0
        for g in fixes:
            if g is f or abs(g["idx"] - f["idx"]) > window:
                continue
            if _consistent(f, g, tol):
                support += 1
        if support >= min_support:
            kept.append(f)
    return kept


def reject_3consecutive(fixes, tol):
    """ORB-SLAM (original) loop-closure rule: candidate accepted only if
    consistent across three consecutive keyframes. Faithful version: both
    neighbouring accepted fixes (idx-1 and idx+1) must exist and agree within
    tol. If a neighbour frame produced no fix, corroboration fails."""
    by_idx = {f["idx"]: f for f in fixes}
    kept = []
    for f in fixes:
        prev, nxt = by_idx.get(f["idx"] - 1), by_idx.get(f["idx"] + 1)
        if prev is None or nxt is None:
            continue
        if _consistent(f, prev, tol) and _consistent(f, nxt, tol):
            kept.append(f)
    return kept


def _greedy_clique(fixes, tol):
    """Pairwise-consistency max clique, greedy (PCM / Kimera-RPGO style)."""
    if not fixes:
        return []
    adj = {
        i: {
            j
            for j in range(len(fixes))
            if j != i and _consistent(fixes[i], fixes[j], tol)
        }
        for i in range(len(fixes))
    }
    best = []
    for seed in sorted(adj, key=lambda i: -len(adj[i])):
        cur = [seed]
        cand = set(adj[seed])
        while cand:
            nxt = max(cand, key=lambda j: len(adj[j] & cand))
            cur.append(nxt)
            cand &= adj[nxt]
        if len(cur) > len(best):
            best = cur
    return [fixes[i] for i in best]


def reject_pcm(fixes, tol):
    """PCM: keep the largest mutually-consistent set."""
    return _greedy_clique(fixes, tol)


def reject_frame_align(fixes, tau):
    """VINS-Fusion-style robust frame alignment: estimate the constant offset
    between the prior stream and the estimate stream with a robust location
    estimator (coordinate-wise median), then reject fixes whose residual from
    the aligned frame exceeds tau. This is the global_fusion architecture
    (TError factors + Huber) reduced to its classification behaviour."""
    dn = np.median(
        [
            ne_delta(f["prior_lat"], f["prior_lon"], f["est_lat"], f["est_lon"])[0]
            for f in fixes
        ]
    )
    de = np.median(
        [
            ne_delta(f["prior_lat"], f["prior_lon"], f["est_lat"], f["est_lon"])[1]
            for f in fixes
        ]
    )
    kept = []
    for f in fixes:
        on, oe = ne_delta(f["prior_lat"], f["prior_lon"], f["est_lat"], f["est_lon"])
        if math.hypot(on - dn, oe - de) <= tau:
            kept.append(f)
    return kept


def reject_prior_ratio(fixes, ratio, oracle_uncertainty=False):
    """Prior-ratio gate (11th iteration): reject when the fix is farther from
    the prior than `ratio` times the prior's own uncertainty. Deployed form
    uses the filter-reported RMS; the oracle form uses the true prior error
    (diagnostic only -- reported separately, never mixed with deployed)."""
    kept = []
    for f in fixes:
        pf = haversine_m(f["prior_lat"], f["prior_lon"], f["est_lat"], f["est_lon"])
        if oracle_uncertainty:
            unc = haversine_m(f["prior_lat"], f["prior_lon"], f["gt_lat"], f["gt_lon"])
        else:
            unc = f["prior_rms_m"]
        if unc <= 0 or pf / unc <= ratio:
            kept.append(f)
    return kept


# --------------------------------------------------------------------------


def metric(fixes, kept):
    base_good = sum(1 for f in fixes if f["err_m"] <= FATAL_M)
    base_fatal = len(fixes) - base_good
    g = sum(1 for f in kept if f["err_m"] <= FATAL_M)
    fa = len(kept) - g
    gk = 100.0 * g / base_good if base_good else float("nan")
    fk = 100.0 * fa / base_fatal if base_fatal else float("nan")
    ratio = (gk / fk) if (fk and fk > 0) else (float("inf") if gk > 0 else float("nan"))
    return {
        "kept": len(kept),
        "good_kept_pct": gk,
        "fatal_kept_pct": fk,
        "ratio": ratio,
        "good": g,
        "fatal": fa,
        "base_good": base_good,
        "base_fatal": base_fatal,
    }


def analyze(pool, label):
    per = pool["per_region"]
    pooled = [f for r in per.values() for f in r]
    rows = []

    def add(name, setting, kept):
        m = metric(pooled, kept)
        rows.append({"method": name, "setting": setting, "label": label, **m})

    per_region_rows = []

    def add_per_region(name, setting, kept_by_region):
        for rname, fr in per.items():
            m = metric(fr, kept_by_region.get(rname, []))
            per_region_rows.append(
                {
                    "method": name,
                    "setting": setting,
                    "label": label,
                    "region": rname,
                    **m,
                }
            )

    for w in (1,):
        for t in (30.0, 60.0, 100.0):
            add(
                "seq-consistency",
                f"w={w} tol={t:.0f}",
                [f for rname, fr in per.items() for f in reject_seq(fr, w, t)],
            )
    for t in (30.0, 60.0, 100.0):
        add(
            "ORB-SLAM 3-consecutive",
            f"tol={t:.0f}",
            [f for rname, fr in per.items() for f in reject_3consecutive(fr, t)],
        )
        add(
            "PCM max-clique",
            f"tol={t:.0f}",
            [f for rname, fr in per.items() for f in reject_pcm(fr, t)],
        )
    for tau in (50.0, 75.0, 100.0):
        add(
            "frame-alignment",
            f"tau={tau:.0f}",
            [f for rname, fr in per.items() for f in reject_frame_align(fr, tau)],
        )
    add(
        "prior-ratio (deployed RMS)",
        "r=1.5",
        [f for rname, fr in per.items() for f in reject_prior_ratio(fr, 1.5)],
    )
    add(
        "prior-ratio (oracle unc.)",
        "r=1.5",
        [
            f
            for rname, fr in per.items()
            for f in reject_prior_ratio(fr, 1.5, oracle_uncertainty=True)
        ],
    )

    # Per-region breakdown for the settings the paper will quote.
    add_per_region(
        "seq-consistency",
        "w=1 tol=100",
        {rname: reject_seq(fr, 1, 100.0) for rname, fr in per.items()},
    )
    add_per_region(
        "ORB-SLAM 3-consecutive",
        "tol=100",
        {rname: reject_3consecutive(fr, 100.0) for rname, fr in per.items()},
    )
    add_per_region(
        "PCM max-clique",
        "tol=100",
        {rname: reject_pcm(fr, 100.0) for rname, fr in per.items()},
    )
    add_per_region(
        "frame-alignment",
        "tau=100",
        {rname: reject_frame_align(fr, 100.0) for rname, fr in per.items()},
    )
    add_per_region(
        "prior-ratio (deployed RMS)",
        "r=1.5",
        {rname: reject_prior_ratio(fr, 1.5) for rname, fr in per.items()},
    )
    add_per_region(
        "prior-ratio (oracle unc.)",
        "r=1.5",
        {
            rname: reject_prior_ratio(fr, 1.5, oracle_uncertainty=True)
            for rname, fr in per.items()
        },
    )
    return rows, per_region_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--drift", type=float, default=300.0)
    ap.add_argument("--regions", default="03,04,06")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1992)
    ap.add_argument("--ncc", type=float, default=0.30)
    ap.add_argument("--min-inliers", type=int, default=10)
    ap.add_argument("--pools", default="d150,d300,d600")
    ap.add_argument("--out", default=str(ROOT / "results" / "action2_rejectors.json"))
    args = ap.parse_args()

    if args.collect:
        regions = [r.strip() for r in args.regions.split(",")]
        per = {}
        for r in regions:
            print(f"collecting R{r} ...", flush=True)
            fixes, attempted = collect(
                r, args.n, args.drift, args.seed, args.ncc, args.min_inliers
            )
            good = sum(1 for f in fixes if f["err_m"] <= FATAL_M)
            print(
                f"  R{r}: {len(fixes)}/{attempted} matched, {good} good, "
                f"{len(fixes) - good} fatal",
                flush=True,
            )
            per[r] = fixes
        out = Path(args.out)
        out.write_text(
            json.dumps(
                {
                    "drift": args.drift,
                    "n": args.n,
                    "seed": args.seed,
                    "per_region": per,
                },
                indent=2,
            )
        )
        print(f"wrote {out}")
        return 0

    if args.analyze:
        rows, per_region_rows = [], []
        for tag in args.pools.split(","):
            tag = tag.strip()
            path = RESULTS / f"action2_pool_{tag}.json"
            if not path.exists():
                print(f"missing pool {path}; run --collect --drift {tag[1:]}")
                continue
            pool = json.loads(path.read_text())
            r, pr = analyze(pool, tag)
            rows += r
            per_region_rows += pr

        print(
            f"\n{'method':<26} {'setting':<16} {'drift':>5} "
            f"{'kept':>5} {'good%':>6} {'fatal%':>7} {'ratio':>7}  verdict"
        )
        print("-" * 88)
        for r in rows:
            ratio = r["ratio"]
            rs = f"{ratio:.2f}" if math.isfinite(ratio) else "inf"
            ok = r["fatal_kept_pct"] <= 75.0 and r["good_kept_pct"] >= 80.0
            warn = "" if r["kept"] >= 20 else f" (n={r['kept']}!)"
            print(
                f"{r['method']:<26} {r['setting']:<16} {r['label']:>5} "
                f"{r['kept']:>5} {r['good_kept_pct']:>5.0f}% "
                f"{r['fatal_kept_pct']:>6.0f}% {rs:>7}  "
                f"{'PASS' if ok else 'fail'}{warn}"
            )

        print(
            f"\nPER-REGION (paper table)\n"
            f"{'method':<26} {'setting':<16} {'drift':>5} {'region':>7} "
            f"{'n':>4} {'good':>5} {'fatal':>6} {'good kept%':>10} "
            f"{'fatal kept%':>11} {'ratio':>7}"
        )
        print("-" * 100)
        for r in per_region_rows:
            ratio = r["ratio"]
            rs = f"{ratio:.2f}" if math.isfinite(ratio) else "inf"
            print(
                f"{r['method']:<26} {r['setting']:<16} {r['label']:>5} "
                f"{r['region']:>7} {r['base_good'] + r['base_fatal']:>4} "
                f"{r['base_good']:>5} {r['base_fatal']:>6} "
                f"{r['good_kept_pct']:>9.0f}% {r['fatal_kept_pct']:>10.0f}% "
                f"{rs:>7}"
            )
        Path(args.out).write_text(
            json.dumps({"pooled": rows, "per_region": per_region_rows}, indent=2)
        )
        print(f"\nwrote {args.out}")
        return 0

    ap.error("give --collect or --analyze")


if __name__ == "__main__":
    raise SystemExit(main())
