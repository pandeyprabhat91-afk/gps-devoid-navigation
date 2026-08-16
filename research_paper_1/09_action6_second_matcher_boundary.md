# Action 6 — Second-Matcher Replication + Exhaustive Boundary Map

**Date:** 2026-08-15 (draft-v3 session)
**Purpose:** close the two solvable v2 reviewer weaknesses — (W1) core class
measured on one region with unprobed regions left dangling, (W2) all rates
measured with one matcher.
**Harnesses:** `scripts/gt_tile_matcher_variants.py` (new),
`scripts/bench_rejectors_variant.py` (new), `scripts/analyze_v3_matchers.py`
(new), `scripts/coherence_curve.py` (R07/R09 probes), `scripts/build_dem_cache.py`
(R07 grid, 500 m). All run with the repo venv. Protocol identical to
Actions 1–3 (CLAHE, DEM/AGL GSD rescale, GT tile radius=1, MIN_INLIERS=15,
MAGSAC, H_inv image-centre); only the correspondence source varies.
Cross-quote rule honoured: per-matcher streams analysed separately, never
pooled with Action-2 pools.

## 6.1 Second-matcher signature (GT-tile contiguous, R04, 738 rows)

| Matcher        | Solved    | good/mid/alias | axial R | axis   | hole@0 | aniso | med err | lag-1 alias  | lag-1 good     |
| -------------- | --------- | -------------- | ------- | ------ | ------ | ----- | ------- | ------------ | -------------- |
| pooled (paper) | 610 (83%) | 143/374/93     | 0.31    | 167.2° | 0.18   | 1.83  | 31.1 m  | 2.55× (n=25) | at null (0.93) |
| ORB-only       | 497 (67%) | 121/310/66     | 0.28    | 169.3° | 0.19   | 1.78  | 31.1 m  | 2.09× (n=14) | 0.77 (mild)    |
| SIFT-only      | 469 (64%) | 118/290/61     | 0.28    | 166.5° | 0.19   | 1.77  | 30.0 m  | 2.24× (n=10) | 0.95 (null)    |
| SP+LightGlue   | 377 (51%) | 95/218/64      | 0.23    | 167.4° | 0.22   | 1.68  | 30.2 m  | 1.57× (n=24) | 1.05 (null)    |

**Verdict — signature reproduces under every matcher family** (binary
corner, gradient-blob, learned detector+matcher): same axis within 3°,
same hole-at-zero, alias group coherent at lag 1 (1.57–2.55× below null),
good group at null. The class is a property of the terrain, not of the
ORB+AKAZE+SIFT pool. LightGlue solves fewer frames (51%) but produces a
proportionally similar alias tail (17% of solved vs 15% pooled).

## 6.2 Second-matcher rejection rates (R04, d300, n=40, seed 1992)

| Rejector (tol/τ=100) | pooled (27g/7f) | ORB (22g/7f)      | SIFT (23g/8f)     | LightGlue (18g/2f) |
| -------------------- | --------------- | ----------------- | ----------------- | ------------------ |
| seq-consistency      | 85/100 (0.85)   | 91/100 (**0.91**) | 78/100 (**0.78**) | 83/50 (1.67)       |
| 3-consecutive        | 30/57 (0.52)    | 27/43 (0.64)      | 26/25 (1.04)      | 22/0               |
| PCM max-clique       | 19/14 (1.30)    | 23/14 (1.59)      | 22/12 (1.74)      | 22/0               |
| frame-align          | 26/14 (1.81)    | 32/14 (2.23)      | 30/12 (2.43)      | 22/0               |
| prior-ratio (oracle) | 93/100 (0.93)   | 91/100 (0.91)     | 91/100 (0.91)     | 89/100 (0.89)      |

**Verdict — the rate structure is matcher-stable.** Under every classical
matcher: sequential consistency discriminates backwards (0.78–0.91),
PCM/frame-alignment go forward only by keeping 19–32% of good fixes, and
the sub-tile class stays invisible to the prior-ratio gate (0.89–0.93)
while remaining fully separable on whole-tile R06 (Action 2). LightGlue's
rate cells are underpowered (2 fatal frames — the learned matcher plus NCC
0.30 acceptance collapses yield: R03 control 9/40 vs pooled 34/40) and are
reported as such; its evidence is at the signature level (6.1). The one
nominal adoption-bar pass (LightGlue seq-consistency, 81% good / 50% fatal)
rests on n=2 fatal and cannot carry a decision per the small-cell rule.

## 6.3 Boundary map completion (11/11 regions) — superseded by forensic probe

Contiguous GT-tile probes on the last unprobed regions (R07 grid DEM built
this session, 500 m spacing, 467–559 m elevation): R07 0/30 solved, R09
12/100 (7 good, 4 mid, 1 alias). **Superseded** by the instrumented probe
below — R02/R07/R10 were probed pre-DEM (2.7–4.6× scale error) and the
R07 CSV holds only 30 frames, so the earlier "0/100" was "0/30".

## 6.4 Split-half internal replication (pooled n=610)

| Half   | n   | groups g/m/a | axis   | hole@0 | aniso | lag-1 alias  | lag-1 good   |
| ------ | --- | ------------ | ------ | ------ | ----- | ------------ | ------------ |
| first  | 305 | 85/179/41    | 168.1° | 0.22   | 1.69  | 1.16× (n=13) | 1.09× (null) |
| second | 305 | 58/195/52    | 166.6° | 0.14   | 2.02  | 3.16× (n=12) | 1.06× (null) |

Both halves independently show the signature on the same axis with
coherent alias tails; the weaker first-half coherence (1.16×) is consistent
with the per-field axis revision (Sec. 4.1 v2) — a half-flight still spans
multiple fields.

## 6.5 Forensic probe — why the ceiling class fails (per region)

`probe_regions_forensic.py` (n=40 step-sampled, DEM-corrected AGL, ≥15
MAGSAC inliers; records tile existence, correspondence counts per
detector, inliers, AGL, GSD ratio; `--fx` override). DEM grids built for
R02/R10 (500 m) and R05 (250 m, replaces 500 m grid). `fx_sweep.py` tests
focal hypotheses 500–1200 px on R05/R07/R10 (3000×2000 sensor regions).

| Region | Solved | corr med → inlier med (conv%) | Cause                             |
| ------ | ------ | ----------------------------- | --------------------------------- |
| R01    | 1/40   | 38 → 5 (13%)                  | non-planar (buildings/water)      |
| R02    | 3/40   | 42 → 5 (12%)                  | non-planar                        |
| R03    | 27/40  | 84 → 33 (39%)                 | control (works)                   |
| R05    | 0/40   | 24 → 5 (21%)                  | ~400 m relief                     |
| R07    | 0/30   | 5 → 4 (80%)                   | 30-frame flight; few matches      |
| R08    | 3/40   | 57 → 5 (9%)                   | non-planar + water                |
| R09    | 3/40   | 54 → 6 (10%)                  | non-planar; 14/40 GT tiles absent |
| R10    | 0/40   | 16 → 5 (30%)                  | relief + canopy                   |

Rules-out measured: satellite maps uniform 0.27–0.38 m/px (R09 tif naming
differs; tiles missing on 14/40 frames); fx sweep flat → camera-model
mismatch not the limiter; |tilt| med 1.4–2.0° with no inlier correlation;
AGL corrected (R07 raw 690 abs vs ~190 AGL; R10 772 vs 295; R05 2310 vs
1889–2303 ground). **Verdict:** the ceiling class is a geometry failure —
the planar-homography assumption against relief/buildings/canopy with
abundant features (user's observation confirmed: images have features;
correspondences exist; the homography cannot convert them). Visual pairs
(drone vs GT tile) saved to `artifacts/pairs/`.

## 6.6 Audit verification (4 independent attacks, all negative)

The §6.5 verdict was challenged and re-tested by four independent methods
(`ncc_verify.py`, `ncc_verify2.py`, one-frame diagnostics, RANSAC sweep):

1. **Direct photometric alignment** (template NCC, yaw×scale grid + ECC
   affine refine): no signal on ANY region — even R03/R04, which the
   feature pipeline solves at 68–83%. Best global NCC 0.17–0.54, errors
   100–460 m everywhere.
2. **NCC at the known-true alignment** with the dataset's own yaw
   (Phi columns, exact candidates) and fine scale sweep: 0.06 on an R03
   frame the feature pipeline solves at 24.5 m with 22 inliers. Bulk
   pixels do not correspond cross-season/cross-sensor at 1 m/px; the task
   rides on sparse stable keypoints. Intensity-based "better measures"
   (NCC/ECC) are structurally unsuited without a near-exact transform.
3. **Yaw-metadata matching** (rotate query by Phi before pooled match):
   no change on R02/R08/R09; slightly worse on R03 (rotation-invariant
   descriptors don't need it; interpolation adds noise).
4. **RANSAC/ratio relaxation** (ratio 0.85, threshold 10–15 px): solve
   counts DO rise (R02 0→5/15, R08 0→5/15, R09 1→4/12) — but the new
   solves are wrong locks: median errors 107/223/393–467 m. The
   correspondences admitted by relaxing are geometrically inconsistent,
   not merely sub-threshold. R03 control stays clean (19–26 m) at every
   setting.

**Two conclusions.** (a) The §6.5 audit is verified: features exist, but
no single-plane geometry explains them — the failure is structural.
(b) Side-finding worth quoting: a loosely-tuned matcher converts the
ceiling class from a _no-fix_ failure into a _wrong-fix_ failure
(confident locks at 107–467 m) — the no-fix/wrong-fix taxonomy boundary
is a threshold choice, and the safe side of it is the strict one.

## Artifacts

- `gt_variant_{orb,sift,lightglue}_R04.json` (per-frame + signature)
- `action2v_pool_{orb,sift,lightglue}_d300.json`, `action2v_rejectors_*.json`
- `boundary_coherence_R0709.json`, `v3_matcher_analysis.txt`
- Scripts: `gt_tile_matcher_variants.py`, `bench_rejectors_variant.py`,
  `analyze_v3_matchers.py` (all in `E:\kp_vio\kp_vio_py\scripts\`)
