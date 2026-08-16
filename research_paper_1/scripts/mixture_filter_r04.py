#!/usr/bin/env python3
"""
Action 4b (research_paper_1): multi-hypothesis (mixture) hedge filter for
sub-tile aliases, and the design curve against prior uncertainty.

Setup. R04 contiguous fix stream (GT-tile matching, action3_coherence.json).
Each fix est_i may be locked k_i furrow periods off the truth along an axis u:
candidate true positions are est_i - k*p*u for k in [-4..4] (p = 20 m,
u = 171 deg, from Gate 1 / Action 1).

Why a mixture and not rejection. Action 2 measured that every consistency-
based rejector discriminates backwards on this stream. Pairwise motion
consistency has a gauge symmetry (a constant offset is invisible to frame
differences -- Finding U), so no rejection rule can separate the modes from
within. The only anchor that breaks the symmetry is the prior. The hedge
filter therefore keeps ALL k hypotheses alive with posterior weights from the
prior likelihood and outputs the posterior MEAN position (soft correction)
instead of committing to a mode.

The experiment. Sweep the prior 1-sigma uncertainty sigma_p in
{300, 100, 50, 20, 10, 5} m (random-walk prior, seed 1992, matching the
deployment's drift model). For each: posterior over k per fix from the prior
likelihood only (appearance is proven uninformative -- Action 1, Gate 2:
NCC picks k=0 on 32/32). Report median error of (a) MAP-k output,
(b) posterior-mean output. Baselines: k=0 (the production behaviour, since
appearance always selects k=0) and the oracle (per-frame best k).

Prediction stated before running. At sigma_p ~300 m (dataset drift) neither
output can move; as sigma_p shrinks below the alias displacement (~40 m),
the posterior mass shifts to the alias k and the mean output approaches the
oracle. KILL unless the posterior-mean output recovers >=30% of the
oracle gap (k0_median - oracle_median) at sigma_p <= 20 m.

Usage:
    python scripts/mixture_filter_r04.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

R_EARTH = 6378137.0
AXIS_DEG = 171.0
PERIOD_M = 20.0
K_MAX = 4
SIGMAS = [300.0, 100.0, 50.0, 20.0, 10.0, 5.0]
SEED = 1992


def median(a):
    a = sorted(a)
    return a[len(a) // 2] if a else float("nan")


def ne(lat1, lon1, lat2, lon2):
    return (
        math.radians(lat2 - lat1) * R_EARTH,
        math.radians(lon2 - lon1) * R_EARTH * math.cos(math.radians(lat1)),
    )


def main() -> int:
    data = json.loads((ROOT / "results" / "action3_coherence.json").read_text())
    frames = data["04"]

    th = math.radians(AXIS_DEG)
    un, ue = math.cos(th), math.sin(th)
    ks = list(range(-K_MAX, K_MAX + 1))

    est_n, est_e, gt_n, gt_e = [], [], [], []
    for f in frames:
        en, ee = ne(f["gt_lat"], f["gt_lon"], f["est_lat"], f["est_lon"])
        est_n.append(en)
        est_e.append(ee)
        gt_n.append(f["gt_lat"])
        gt_e.append(f["gt_lon"])
    n_frames = len(frames)

    def err_ned(cn, ce):
        out = []
        for cni, cei, gtl, glo in zip(cn, ce, gt_n, gt_e):
            cla = gtl + math.degrees(cni / R_EARTH)
            clo = glo + math.degrees(cei / (R_EARTH * math.cos(math.radians(gtl))))
            dn = math.radians(cla - gtl) * R_EARTH
            de = math.radians(clo - glo) * R_EARTH * math.cos(math.radians(gtl))
            out.append(math.hypot(dn, de))
        return out

    # Baseline (production: appearance selects k=0 -> est as-is).
    base_err = err_ned(est_n, est_e)
    base_med = median(base_err)

    # Oracle: per-frame best k.
    orc_err = []
    for i in range(n_frames):
        best = math.hypot(est_n[i], est_e[i])
        for k in ks:
            cn = est_n[i] - k * PERIOD_M * un
            ce = est_e[i] - k * PERIOD_M * ue
            best = min(best, math.hypot(cn, ce))
        orc_err.append(best)
    orc_med = median(orc_err)

    gap = base_med - orc_med
    print(
        f"n={n_frames} fixes; axis {AXIS_DEG:.0f}deg, period {PERIOD_M:.0f}m, "
        f"k in [{-K_MAX},{K_MAX}]"
    )
    print(f"baseline k=0 median: {base_med:.1f} m")
    print(f"oracle median:       {orc_med:.1f} m   (gap {gap:.1f} m)")
    print(
        f"KILL: posterior-mean must recover >=30% of gap "
        f"({0.3 * gap:.1f} m) at sigma_p <= 20 m\n"
    )

    print(
        f"{'sigma_p':>8} {'prior rw step':>13} {'MAP median':>12} "
        f"{'mean median':>13} {'mean vs k=0':>12}  verdict"
    )
    print("-" * 70)

    results = {}
    for sp in SIGMAS:
        # Random-walk prior like the deployment drift model.
        rng = np.random.default_rng(SEED)
        step = sp / math.sqrt(max(1, n_frames))
        d = np.zeros((n_frames, 2))
        for i in range(1, n_frames):
            d[i] = d[i - 1] + rng.normal(0.0, step, size=2)
        pn = [en + d[i, 0] for i, en in enumerate(est_n)]
        pe = [ee + d[i, 1] for i, ee in enumerate(est_e)]

        map_err, mean_err = [], []
        for i in range(n_frames):
            w = []
            for k in ks:
                cn = est_n[i] - k * PERIOD_M * un
                ce = est_e[i] - k * PERIOD_M * ue
                r2 = ((cn - pn[i]) ** 2 + (ce - pe[i]) ** 2) / (2 * sp * sp)
                w.append(math.exp(-r2))
            w = np.array(w)
            w /= w.sum()
            # MAP output.
            k_map = ks[int(np.argmax(w))]
            map_err.append(
                math.hypot(
                    est_n[i] - k_map * PERIOD_M * un, est_e[i] - k_map * PERIOD_M * ue
                )
            )
            # Posterior-mean (hedged) output.
            cn = est_n[i] - PERIOD_M * un * float((w * ks).sum())
            ce = est_e[i] - PERIOD_M * ue * float((w * ks).sum())
            mean_err.append(math.hypot(cn, ce))

        m_med = median(map_err)
        mu_med = median(mean_err)
        gain = base_med - mu_med
        ok = sp <= 20.0 and gain >= 0.3 * gap
        print(
            f"{sp:>8.0f} {step:>13.2f} {m_med:>11.1f}m {mu_med:>12.1f}m "
            f"{gain:>+11.1f}m  {'PASS' if ok else 'fail'}"
        )
        results[sp] = {"map_median": m_med, "mean_median": mu_med, "vs_k0": gain}

    # Supplementary: IID prior (no temporal correlation) -- the video-rate
    # odometry limit, where each fix's prior uncertainty is independent.
    print("\nIID prior (video-rate limit, no temporal correlation):")
    print(
        f"{'sigma_p':>8} {'MAP median':>12} {'mean median':>13} "
        f"{'mean vs k=0':>12}  verdict"
    )
    print("-" * 56)
    iid = {}
    rng = np.random.default_rng(SEED)
    for sp in SIGMAS:
        pn = [en + rng.normal(0.0, sp) for en in est_n]
        pe = [ee + rng.normal(0.0, sp) for ee in est_e]
        map_err, mean_err = [], []
        for i in range(n_frames):
            w = []
            for k in ks:
                cn = est_n[i] - k * PERIOD_M * un
                ce = est_e[i] - k * PERIOD_M * ue
                r2 = ((cn - pn[i]) ** 2 + (ce - pe[i]) ** 2) / (2 * sp * sp)
                w.append(math.exp(-r2))
            w = np.array(w)
            w /= w.sum()
            k_map = ks[int(np.argmax(w))]
            map_err.append(
                math.hypot(
                    est_n[i] - k_map * PERIOD_M * un, est_e[i] - k_map * PERIOD_M * ue
                )
            )
            cn = est_n[i] - PERIOD_M * un * float((w * ks).sum())
            ce = est_e[i] - PERIOD_M * ue * float((w * ks).sum())
            mean_err.append(math.hypot(cn, ce))
        m_med, mu_med = median(map_err), median(mean_err)
        gain = base_med - mu_med
        ok = sp <= 20.0 and gain >= 0.3 * gap
        print(
            f"{sp:>8.0f} {m_med:>11.1f}m {mu_med:>12.1f}m "
            f"{gain:>+11.1f}m  {'PASS' if ok else 'fail'}"
        )
        iid[sp] = {"map_median": m_med, "mean_median": mu_med, "vs_k0": gain}

    out = ROOT / "results" / "action4_mixture.json"
    out.write_text(
        json.dumps(
            {
                "axis_deg": AXIS_DEG,
                "period_m": PERIOD_M,
                "n": n_frames,
                "baseline_median": base_med,
                "oracle_median": orc_med,
                "results": results,
                "iid_prior": iid,
            },
            indent=2,
        )
    )
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
