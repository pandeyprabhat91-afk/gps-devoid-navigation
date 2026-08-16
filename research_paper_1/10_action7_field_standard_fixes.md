# Action 7 — Field-Standard Fixes, Measured (PnP+DSM, GNC, Robust Smoother)

**Date:** 2026-08-16
**Purpose:** implement the three published remedies this project had cited
but never measured, on populations the earlier gates did not cover.
**Papers:** AnyVisLoc (arXiv:2503.10692), OrthoLoC (arXiv:2509.18350),
OrthoTrack (arXiv:2606.25245) — PnP against DSM; Yang et al. RA-L 2020 —
GNC; GTSAM/Kimera-RPGO/TACO class — robust-kernel smoothing (survey S4).
**Rule honoured:** none of these re-runs a closed gate. gate_pnp_dem.py
(9th iter) covered flat R03/R04 only; the ceiling regions it never touched
are the population tested here, with DEM grids rebuilt at 90 m sampling
for R05/R10. GNC and the robust smoother were never implemented before.

## 7.1 PnP against the DSM on the ceiling class — KILLED (correspondence-limited)

`gate_pnp_ceiling.py`: GT-tile pooled correspondences, three arms
(production homography / PnP-flat / PnP-DEM, IPPE planar / EPNP relief,
solvePnPRansac 8 px). Kill criterion pre-registered: ≥10 pts solve-rate
gain or ≥5 m median gain AND ≥2 m 2.5D credit over PnP-flat, on some
ceiling region. n=40 per region.

| Region        | frames | homog solved | PnPflat | PnPDEM | homog med | PnPDEM med |
| ------------- | ------ | ------------ | ------- | ------ | --------- | ---------- |
| R01           | 32     | 4            | 2       | 3      | 11.6 m    | 104.3 m    |
| R02           | 30     | 5            | 2       | 3      | 12.3 m    | 116.0 m    |
| R05           | 40     | 1            | 1       | 1      | 37.6 m    | 262.4 m    |
| R07           | 14     | 0            | 0       | 0      | —         | —          |
| R08           | 33     | 3            | 1       | 2      | 19.3 m    | 337.6 m    |
| R09           | 26     | 4            | 2       | 1      | 31.5 m    | 34.0 m     |
| R10           | 39     | 0            | 0       | 0      | —         | —          |
| R03 (control) | 40     | **32**       | 27      | 12     | 15.6 m    | 108.9 m    |

PnP solves fewer frames than the homography everywhere — including the
healthy control — and where it solves it is worse (34–338 m). The ceiling
class is **correspondence-limited, not model-limited**: the 16–57 pooled
correspondences that survive descriptor matching do not agree under ANY
geometric model, so the field-standard geometry swap buys nothing on this
data. Mechanism recorded, gate KILLED.

## 7.2 GNC graduated robust frame alignment — KILLED (empty inlier set)

GNC-GM (Yang 2020) over the constant-offset (prior→estimate) model, the
same formulation as Action 2's frame alignment, μ-graduated with GM
weights, on all Action-2 pools and the three variant-matcher pools.

Kept-fix fractions: R03 3–5%, R04 0–5%, R06 6–10%, pooled 0–2% — no cell
passes the adoption bar under any matcher at any drift. The graduated
loss converges to an **empty inlier set**: the prior↔estimate offsets
have no constant mode (Finding U's scatter; aliases make it worse). GNC
is the sixth rejection family measured, and the sharpest: it is the only
method that keeps essentially nothing rather than discriminating
backwards — a measured endorsement of the paper's gauge-symmetry
argument from the graduated-robustness direction.

## 7.3 Robust fixed-lag smoother (survey S4) — KILLED with mechanism

GTSAM/TACO-class factor graph over each per-region fix stream:
map-fix factors wrapped in a GM kernel (σ=30 m), motion factors from
prior deltas TRUSTED (Gaussian σ=40 m), IRLS Gauss-Newton.

**Implementation validity (synthetic, pre-registered):** 12-fix chain,
one isolated 199 m outlier: smoothed to 8.9 m (moved 195 m), good fixes
retained. The implementation can down-weight isolated wrong fixes.

**Real streams (Action-2 + variant pools):**

| cell     | raw → smooth median | fatal raw → smooth |
| -------- | ------------------- | ------------------ |
| R03 d150 | 13.4 → 21.1 m       | 0 → 4              |
| R04 d150 | 33.7 → 27.5 m       | 7 → 8              |
| R06 d150 | 24.0 → 43.4 m       | 8 → 12             |
| R03 d300 | 13.9 → 54.5 m       | 0 → 18             |
| R04 d300 | 30.9 → 142.4 m      | 7 → 26             |
| R06 d300 | 23.3 → 97.8 m       | 7 → 16             |

No cell heals; d300/d600 degrade sharply. Mechanism, two parts. (a) The
trusted motion chain is built from prior deltas, and at 7 s frame spacing
the drift random walk dominates those deltas — trusting them drags the
states away from correct map fixes, which the GM kernel then down-weights.
The survey's own caveat ("at 7-second spacing the odometry cannot be
primary") is what kills the design. (b) Where motion is decent (d150),
R06 whole-tile aliases ARE moved (367 m median) but land wrong — alias
chains follow the aircraft, so the trusted chain contains them (Finding U
extended to whole-tile). A robust back-end cannot fix what the trusted
motion already encodes.

**Verdict:** the robust back-end alternative (S4) requires trusted
odometry that this dataset's spacing does not provide — the back-end half
of the paper's "odometry regime" conclusion, now measured rather than
assumed.

## Artifacts

- `results/pnp_ceiling.json` — §7.1
- `results/gnc_and_smoother.json` — §7.2/7.3
- Scripts: `gate_pnp_ceiling.py`, `gnc_and_smoother.py` (synthetic
  validity check in `smooth_synthetic.py`, temp)
- DEM grids rebuilt for R05/R10 at 90 m sampling (`dem_cache.json`)
