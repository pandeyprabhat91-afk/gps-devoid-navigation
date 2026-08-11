# HANDOVER 2 — Audit of Iterations 1–10 + Hardware Deployment Guide

**Date:** 2026-08-10
**Scope:** full read of `summary/1st_iteration.md` … `summary/10th_iteration.md`
(5,493 lines) plus two code claims verified directly against `E:\kp_vio`.
**Supersedes nothing.** `HANDOVER.md` (2026-08-08) remains the state-of-the-repo
document; this one is the critique and the deployment plan.

**Target platform assumed throughout:** D-Robotics RDK X5, IMU, monocular
global-shutter camera, barometer + magnetometer from the flight controller.
No GPU, no LiDAR, no RTK, no rangefinder, no stereo.

---

## PART 1 — AUDIT: WHAT THE ITERATIONS GOT WRONG

**One-line thesis of this audit:** the gate-before-sweep discipline was applied
rigorously to *hypotheses* and never once to the *measuring apparatus*. Items
1, 2 and 5 below are three faces of the same failure.

---

### 1. Finding W is invalid — the DSM/PnP direction is NOT closed

**Claim under audit:** `10th_iteration.md` §5.2, Finding W — *"RANSAC already
selects a coplanar subset, so relief never biased the homography."* Used to
close the PnP / 2.5D direction, which `9th_iteration_survey.md` §1 had called
the largest untested structural difference between this project and published
work.

**What the code actually does:**

- `scripts/build_dem_cache.py:151` → `--spacing-m` default is **500.0**
- Verified in `datasets/uav_visloc/dem_cache.json`: **all six regions carry
  `spacing_m: 500.0`**, `dataset: aster30m`

So 30 m ASTER source data was resampled onto **500 m posts**. Frame footprints
are 538–941 m (10th §5.2 Attempt 2 table). That is **1–2 DEM posts per
footprint**, bilinear-interpolated by `kp_vio/map_matching/dem.py`.

**Why that invalidates the test.** Per-correspondence height `h` inside a
single frame is therefore a near-linear ramp, not a relief field. Push a linear
ramp through the correction used in
`scripts/gate_relief_corrected_homography.py`:

```
P' = C + (P - C) * H / (H - h)
```

and the resulting displacement field is itself near-affine. A homography has
8 DoF and absorbs affine displacement **exactly**. The measured 0.0 m gain on
R06 is the guaranteed output of the test as built, independent of whether
terrain relief actually matters.

**Knock-on damage:**

- **Attempt 2's bound table is unreliable.** "Median relief within one
  footprint" measured off 500 m posts cannot see intra-footprint relief. R03's
  8.8 m and R04's 3.5 m are floor artifacts of the grid, not terrain facts.
  (R06's 28.6 m survives only because Qinba terrain varies at kilometre scale.)
- **Attempt 1's PnP degeneracy has the same root cause.** Points lifted off a
  500 m grid are coplanar *by construction*, so `SOLVEPNP_EPNP` degenerated and
  `SOLVEPNP_IPPE` rejected the set. PnP was never validly tested either.

Both attempts died of one cache defect. Finding W was inferred from the pair.

**Fix.** Rebuild at native resolution: `--spacing-m 30`, or pull Copernicus
GLO-30 tiles directly. Over a 3 km box that is ~10k points / ~100 OpenTopoData
calls — minutes, not hours. Then re-run `gate_pnp_dem.py` and
`gate_relief_corrected_homography.py`. Restate or withdraw Finding W on the
result.

---

### 2. Most kills are underpowered, not refuted

Pattern across iterations 7–10: state a kill criterion, run at n=8–16, declare
the direction closed.

| Gate | n | Measured | Bar | Honest read |
|---|---|---|---|---|
| Gate 3 robust smoother (10th §4.3) | cliques of 2–5 | 1.33–1.80× | 2× | no power to reject 2× |
| Relief-corrected homography (10th §5.2) | 14 / 8 frames | +1.0 / −0.0 m | ≥5 m | also structurally invalid (§1) |
| GIM precision (8th §2) | 15 | +2.6 m, one frame drives it | ≥5 m | plausible kill |
| Nadir correction (7th §4.1) | 10 | 1.6 m | 2 m | coin-flip against the bar |
| Finding T error direction (10th §2) | 16 | axial R=0.62 | — | correctly labelled direction-finding |
| Gate 1 sub-tile snap (10th §4.1) | 16 | 2.39× vs null | — | survives, but same n |

`6th_iteration.md` §8 Finding G identified exactly this failure and wrote the
rule (*"n ≥ 40 must apply to MATCHED frames, not attempted frames"*).
Iterations 7, 8 and 10 then broke it repeatedly. The project is currently
generating negative results faster than its sample sizes can support.

**Fix, cheap and high-leverage.** GT-tile probes need no retrieval and no drift
model — they are fast, and UAV-VisLoc holds far more frames than the n=40
step-sample uses. Re-run Gate 1, Gate 3, Step 2 and the georef-bias analysis at
**n ≥ 150**. Add a power statement to every future kill criterion: *"at this n,
effect sizes below X are undetectable."*

---

### 3. The 10× cross-script inlier disagreement was never diagnosed

`9th_iteration_survey.md` §9.3 records R03 mean inliers, same region, same ORB
pool, from three scripts:

| script | R03 mean inliers |
|---|---|
| `smoke_agl_inlier_floor.py` | 9.6 |
| `smoke_detector_free.py` (7th §6.1) | 54.8 |
| `diag_gim_probe.py` | 128.3 |

Waved off as *"three different frame samples … that variance is pre-existing,
not introduced here."*

**10× is not frame sampling.** Candidate causes: different `QUERY_SCALE`,
different tile zoom level, different ratio-test value, different patch radius,
different rescale path. Until this is diagnosed, **no cross-script comparison
in iterations 7–10 is safe**, and several findings lean on exactly that.

**Fix.** One afternoon: run all three scripts over the *same* 8 frame indices
and diff the intermediate array shapes and parameters.

---

### 4. RoMa / DKM orphaned by a dependency that later died

`9th_iteration_survey.md` §2 established that this project tested the **weakest
matchers** on the AnyVisLoc ranking:

| matcher | A@5m | tested here? |
|---|---|---|
| RoMa | 70.1 % | **no** |
| DKM | 65.6 % | **no** |
| LoFTR | 59.5 % | yes — crippled at 640×480 |
| SP+LG+GIM | 57.0 % | yes — all GIM conclusions rest on this |

Gate D3 was written as *"only meaningful after D1 shows PnP helps."* D1 then
died — invalidly (§1) — so **D3 was never run**.

Findings I and P are about correspondence *count* on regions that already
match. They say nothing about R01/R08/R09, which sit at a 3–7 inlier floor. The
coverage ceilings reported in 10th §5.1 (R01 10 %, R08 7.5 %, R09 15.4 %) were
**measured with the ORB pool** — they are matcher-specific numbers being
reported as data limits.

The four-family convergence argument behind Finding N already broke once: the
9th iteration retracted R06 on a scale defect. Of the remaining families, one
was crippled by resolution and one is the weakest learned option in the
published ranking.

**Fix.** One full-resolution RoMa probe on R01/R08 ground-truth tiles before
those regions are called data-limited. *Note this is a diagnostic run on a
workstation, not a deployment candidate — see Part 2.*

---

### 5. Single seed, single drift realization

`DriftModel` uses `seed=1992` everywhere, deliberately, for reproducibility.
Consequence: every conclusion in iterations 3–10 is conditioned on **one**
random-walk realization. Seed sensitivity has never been tested. Given that
per-region decisions rest on 2–16 accepted fixes, seed variance plausibly
exceeds several of the measured effects.

**Fix.** 5 seeds through the existing `comprehensive_scene_test.py` — one
overnight run, and it retroactively puts error bars on everything.

---

### 6. The GT-accuracy hypothesis IS testable without RTK

`10th_iteration.md` §5.3 names dataset GPS error as the leading explanation for
R03's ~13.9 m floor, then states testing it needs RTK ground truth or an
OrthoLoC-style audit against a high-precision DOP/DSM — *"neither available
here."*

**That is not correct. Drone-to-drone matching isolates it, using data already
on disk.**

Consecutive UAV-VisLoc frames are 7 s apart with ~800 m footprints — large
overlap, same sensor, same season, same modality. Relative displacement between
them is recoverable to sub-metre. Compare against the GPS-reported deltas:

- If dataset GPS carries ~10 m independent per-frame noise, drone-drone
  displacement will disagree with GPS deltas by ~14 m RMS **while remaining
  internally self-consistent along the chain**.
- If instead the matching is at fault, the drone-drone chain will be noisy too.

**Follow-on.** Bundle-adjust the GPS track against the drone-drone relative
constraints, then re-score the pipeline against the smoothed track. If R03's
median collapses, the floor is the dataset — and **the oracle ceilings in
8th-iteration Finding R are measuring GPS noise, not the system.**

This determines whether the thesis's headline ceiling numbers mean anything. It
is cheap and decisive and should have been Step 1 of the 10th iteration.

---

### 7. Repeatedly documented, never done

| Item | First flagged | Status |
|---|---|---|
| Per-terrain `ncc_verify` (R09 2.5 % → 7.5 % at ≤0.10) | 5th §7.3 | recommended 3×, never applied |
| AKAZE/SIFT tile feature cache (4–20 s/frame → sub-second) | 5th §6.4, "one-day infra" | not done |
| RDK X5 latency measurement | 1st iteration, Phase 3 | **zero embedded numbers in ten iterations** |
| ECC as candidate *scorer* (S1) | 9th §10.5 | not run |
| DBoW3 vocabulary on own tiles (S3) | 9th §10.4 | not run |
| Nested-filter / AHRS-consistency paper | 2nd iteration | *"continues in parallel"* ×8 iterations, zero work |
| Allan variance on WIT HWT905 | 2nd iteration | not run |

The AHRS research track should be formally killed or actually started. Eight
iterations of "unaffected, continues in parallel" is a fiction in the documents.

---

### 8. The missing constructive answer — calibrated uncertainty

Findings T, U and V establish that alias fixes **cannot be rejected** by
anything in the pipeline. The system nonetheless emits a bare point fix with no
covariance, so a 40 m-wrong fix enters the ESKF with the same weight as a 4 m
one.

The 1st and 2nd iterations were *about* calibrated likelihoods and NEES
consistency; the engineering track dropped that entirely. Finding V is exactly
the condition under which calibrated uncertainty stops being optional: if you
cannot filter the tail, report it honestly and let the back-end absorb it.

NGPS (`9th` §3.1) obtained an 11 % RMSE reduction from adaptive measurement
covariance built from RANSAC inlier ratio + reprojection error + match
confidence — **all three already computed by this pipeline**.

This is the single move that converts three negative findings into a
contribution, and it reconnects the abandoned research track. Nothing has been
built.

---

### 9. Audit action list, ranked

| # | Action | Cost | Why |
|---|---|---|---|
| 1 | Rebuild DEM cache at 30 m; re-run PnP + relief gates | hours | Finding W invalid; reopens the largest untested direction |
| 2 | Drone-to-drone relative matching vs GPS deltas | hours | decides whether the ceilings are the system or the dataset |
| 3 | Re-run E2E with AGL + adaptive search window + lost mode | 1 day | only path back to a navigation result |
| 4 | Raise all GT-tile probes to n ≥ 150; add power statements | 1 day | half the kills are currently unpowered |
| 5 | Diagnose the 10× cross-script inlier disagreement | afternoon | undermines cross-script findings in 7th–10th |
| 6 | Adaptive covariance from existing signals | 1–2 days | the constructive answer to Finding V |
| 7 | Per-terrain `ncc_verify`; AKAZE/SIFT cache; X5 timing | 2 days | free points + the hardware deliverable |
| 8 | RoMa full-res on R01/R08 GT tiles | 1 day | those ceilings are ORB-pool numbers, not data limits |

---

## PART 2 — DEPLOYMENT GUIDE FOR RDK X5

Sensor stack: **IMU + monocular global-shutter camera + barometer +
magnetometer**. Compute: **RDK X5** (8× Cortex-A55, BPU, no CUDA).

---

### 2.1 What works — keep it

| Piece | Why it survives on this board |
|---|---|
| **ORB + AKAZE + SIFT pooled → single MAGSAC homography** | Pure OpenCV, CPU only, no weights, no GPU. Took forest 0 % → 10 % and non-planar suburban 0 % → 7.5 %. Immune to the ground→aerial domain gap that killed every learned matcher. |
| **`min_inliers = 10`** | Sits exactly at the geometry saturation knee (8th Finding P). Four independent attempts to move it failed. Do not touch. |
| **Patch NCC verify ≈ 0.30** | Cheap. The only in-pipeline signal that ever caught a wrong tile. |
| **AGL = barometer − DEM(estimated position)** | Largest measured win in the project: R06 4/40 → 21/40 matched, 3 → 14 good fixes. **Requires no new sensor.** A 30 m DEM over a 5×5 km operating box is a few hundred KB. |
| **`H_inv` position recovery** | Saturated and exact — two architecturally unrelated matchers agree to 0.17 m. The estimator is not the problem. |

Best-case terrain number, farmland: **85 % match, ~13 m median, zero fatal
fixes.** That is a genuine GPS-denied position source.

---

### 2.2 What does not work — do not spend time

| Dead direction | Reason |
|---|---|
| SuperPoint+LightGlue, GIM, LoFTR, RoMa, DKM, MASt3R | Need CUDA. LightGlue alone is 318 ms of a 386 ms pipeline **on a Jetson Orin NX**. X5 has no comparable GPU. Most are also ground-trained → aerial domain gap. |
| DINOv2 / CosPlace global retrieval | Ground-trained. 5.4 % and 4.2 % match rates. |
| All six rejection gates (inlier count, reprojection RMSE, inlier margin, NCC veto, NCC ranking, NCC non-adjacency margin) | Every one failed or washed out across iterations 3–6. |
| Sequential / N-frame consistency, PCM, GNC, trajectory clustering, multi-frame voting | Finding U: aliases translate *with* the aircraft, so a wrong fix is corroborated exactly as well as a right one. One 55-fix experiment killed all four. |
| Sub-tile alias correction by appearance | Gate 2: NCC picks the wrong offset **16/16**. The wrong lock *is* the appearance optimum. |
| Gradient-template matching (Werner / SPRIN-D style) | Needs LiDAR heightmaps. Not on this airframe. |
| Further parameter tuning | Exhausted three separate times. |

---

### 2.3 The reframe — your hardware is not this dataset

**This is what ten iterations never accounted for.**

| | UAV-VisLoc dataset | Your drone |
|---|---|---|
| Frame spacing | **7 seconds** | 20–30 Hz camera |
| VIO between fixes | dead by frame 2 (0–14 tracked features) | tracks normally |
| Ground truth | consumer GPS, ~10 m noise, never audited | your own (also non-RTK) |
| Heading | unused | **compass from FC** |
| Altitude | absolute CSV column | **live barometer** |

Three of the project's biggest negatives are **explicitly conditional on the
7-second spacing**:

1. **Gate 3 (robust smoother)** — 10th §4.3 says so in its own text: *"Recorded
   as killed for this platform, not as a statement about robust smoothing in
   general."*
2. **The E2E cascade failure** (5th §10.4) — depends on VIO being useless
   between fixes.
3. **Finding U's practical bite** — a 40 m alias is invisible against a
   trajectory that is already drifting hundreds of metres per frame.

At 20–30 Hz all three change:

- VIO becomes the primary position source; map matching drops to true loop
  closure at 0.5–2 Hz — the architecture the 4th iteration mandated but never
  got to run.
- Drift between fixes is metres, not hundreds of metres. The prior stays inside
  one tile, so the candidate set shrinks from 49 tiles to 1–9.
- A 40 m alias becomes **visible as a residual** against a good short-horizon
  trajectory — precisely the condition Gate 3 said was missing.

**These three results do not transfer to the airframe and must be re-tested
there.** Do not inherit them.

---

### 2.4 What compass + barometer buy that the project never used

Today the homography solves all 8 DoF from scratch every frame. You know more:

- **Barometer + DEM → AGL → scale is known** (already adopted, 10th Step 1).
- **Compass → yaw is known** to a few degrees.

Rotation and scale are therefore **sensor-locked**. The only remaining unknown
is **2-DoF translation**.

That changes which algorithms are available. Pre-rotate and pre-scale the drone
frame using compass + AGL, then slide it over the tile — a template-matching
problem. Cheap on CPU, and it uses *all* pixels rather than ~10 keypoints.

**Why this specifically matters here.** 8th-iteration Finding P ("position
saturates above ~15 correspondences") is a statement about **correspondence-based**
estimation. Direct alignment — OpenCV `findTransformECC` — is not
correspondence-based, so the ceiling does not apply. `9th` §10.5 flagged this
as the one algorithm class the project's own findings cannot constrain, and it
was never run. With rotation and scale sensor-locked it is both cheaper and
more applicable on your platform than it was on the dataset.

*Caveat carried forward:* ECC as **post-hoc refinement** of an already-chosen
tile is the same family as the phase-correlation refinement killed hard in the
4th and 5th iterations. The untested form is ECC as the **candidate scorer /
primary estimator**.

---

### 2.5 Terrain warning — read before flying

Works well: flat farmland, strong texture.
Works badly: riverside, mixed suburban, dense canopy.

**IIT Madras campus is buildings + roads + heavy tree cover — closest to R08
and R09, the two weakest regions in the entire study (ceilings 7.5 % and
15.4 %).** Do not expect the 85 % farmland number there.

Mitigations, in order:

1. Fly first sorties over open/agricultural ground outside campus, to validate
   the stack where it is known to work.
2. Drop `ncc_verify` to **0.10** on sparse-texture terrain — recommended three
   separate times across iterations, never applied. Free coverage on R09-like
   scenes.
3. **Your satellite tiles will be fresh and same-season.** Half the failures on
   R01/R08 are attributed to stale or seasonally divergent reference imagery.
   You control that. Pull current tiles for the operating box.

---

### 2.6 Real bottleneck on the board: latency, not accuracy

Multi-feature matching measured at **4–20 s/frame on a laptop** (5th §6.4).
Cortex-A55 cores are far slower. At that rate there is no system.

Two fixes, both already scoped, neither done:

1. **Extend `TileFeatureCache` to hold AKAZE and SIFT descriptors**, not only
   ORB — the cache schema needs 3 descriptor blocks per tile instead of 1.
   Scoped as one day in the 5th iteration. Removes per-tile re-extraction.
2. **Shrink the candidate set.** With a live VIO prior at 30 Hz, 1–9 tiles
   suffice, not 49.

Together that is roughly the 20× required. **No iteration has measured a single
number on actual X5 hardware.** That gap must close before any deployment claim
in the thesis.

---

### 2.7 Honest expectations

| Condition | Expect |
|---|---|
| Farmland / open terrain | Works now. ~13 m median fix, ~1 fix per 1–2 s, no fatal fixes. Enough to bound VIO drift indefinitely. |
| Campus / built-up | ~1 fix per 10–15 frames, ~20 m when it lands, and **~1 in 6 of those wrong by >50 m**. |
| Sub-5 m accuracy | Not reachable against public satellite tiles with this geometry. The oracle bound says so. |

The built-up tail **cannot be filtered out** — that is Finding V and it is well
evidenced. It must be made *survivable*: feed each fix into the ESKF with an
honest covariance behind a chi-square gate, never as a hard reset.

---

### 2.8 Build order for the platform

1. **AKAZE/SIFT tile cache + prior-shrunk candidate set** → then measure real
   latency on the X5. Nothing else matters until this passes.
2. **Barometer → DEM → AGL wired live**, replacing the CSV `height` path.
3. **Compass-locked yaw + AGL-locked scale → 2-DoF search**; trial ECC as the
   candidate scorer.
4. **Per-terrain `ncc_verify`** (0.10 sparse-texture, 0.30 default).
5. **Adaptive covariance out of the matcher** (inlier ratio, reprojection
   error, NCC score) + chi-square gate in the ESKF.
6. **Re-run the end-to-end loop at real frame rate.** Re-test the robust
   smoother — that kill was conditional on 7 s spacing and does not bind you.

---

## PART 3 — PROCESS RULES TO ADD

Carried forward from iterations 3–10, plus four new ones from this audit:

- **Validate the instrument before the hypothesis.** Items 1, 2 and 5 of Part 1
  are all the same failure: gate-before-sweep was applied to ideas and never to
  the measuring apparatus. Before a gate runs, state what result the setup is
  *capable* of producing if the hypothesis were true.
- **Pair every kill with a power statement.** *"At this n, effect sizes below X
  are undetectable."* A negative at n=8 against a 5 m bar is not a kill.
- **A finding does not generalize past the region it was measured on.** Four
  retractions across iterations 6–10 (Finding N for R06, Finding M, Finding K,
  Finding R's strength) share this single cause.
- **Cross-script numbers are not comparable until proven comparable.** The 10×
  R03 inlier disagreement stood unexamined through three iterations.

---

*Document written 2026-08-10. Part 1 §1 verified directly against
`scripts/build_dem_cache.py:151` and `datasets/uav_visloc/dem_cache.json`
(all six regions `spacing_m: 500.0`). All other numbers cited from
`summary/*.md` as attributed. Nothing in this document was re-measured;
it is an audit and a plan, not an experiment report.*
