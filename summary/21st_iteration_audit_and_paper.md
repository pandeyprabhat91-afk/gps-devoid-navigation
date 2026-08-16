# 21st Iteration — Full-Stack Audit, Fix Pass, and Paper Direction Verification

**Date:** 2026-08-15
**Scope:** One autonomous session covering four workstreams: (1) full code audit of both implementations and the research pipeline with fixes, (2) per-region accuracy re-derivation across all 20 prior iterations, (3) deployability verdict, (4) online novelty verification of the paper idea. Also a config change: all opencode agent routing moved to deepseek-v4-pro.

---

## Headline

| Item                       | Result                                                                 |
| -------------------------- | ---------------------------------------------------------------------- |
| Python pipeline bugs fixed | 5 (121/121 tests pass)                                                 |
| C++ estimator bugs fixed   | 10 (55/63 tests; 8 failures proven pre-existing flakiness)             |
| Iteration coverage         | All 20 prior iterations read; 11-20 code claims verified against code  |
| Realistic accuracy         | 10-15 m absolute on matchable terrain; VIO drift 1%/distance elsewhere |
| Deployability              | Estimator yes; full flight system not yet (one X5 flight away)         |
| Paper novelty              | Survives with reframing; C3/C6 claims must be narrowed (OrthoTrack)    |
| Model routing              | Everything → deepseek-v4-pro                                           |

---

## Part 1 — Code Audit (full stack)

Audit method: two parallel deep-exploration passes (C++ estimator tree, Python
pipeline + benchmarks), then manual verification of every reported bug against
the source before fixing. Build-and-test after each side.

### 1.1 Python fixes (research pipeline)

| #   | File                                     | Bug                                                                                                                                                                                                                                                                                                                                               | Fix                                                                                                                  |
| --- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| P1  | `kp_vio/backend/eskf.py`                 | Gravity term subtracted from preintegrated specific force → `v += R·Δv − g·dt`. Under the project's reaction convention (gravity_align, test_eskf, e2e generator: at rest acc reads +g along NED-down) the correct update is `v += g·dt − R·Δv`. The old code was wrong under BOTH conventions. F-matrix and bias-Jacobian signs flipped to match | Rewrote nominal update + F blocks + bias Jacobians                                                                   |
| P2  | `kp_vio/map_matching/feature_matcher.py` | Cached AKAZE/SIFT path used the descriptor matrix (N×61 / N×128) as keypoint xy coordinates → fed straight into `findHomography`. Latent since the 5th iteration; reachable in any cache+multi_feature path                                                                                                                                       | Cached branch removed; fresh detection always (cache holds only ORB kp_xy)                                           |
| P3  | `kp_vio/map_matching/map_matcher.py`     | `pos_ned.z = −pred_alt_m` correct only when origin_alt = 0 (which every script uses — latent, not active)                                                                                                                                                                                                                                         | `−(pred_alt_m − origin_alt)`                                                                                         |
| P4  | `kp_vio/map_matching/map_matcher.py`     | Per-terrain NCC verify was a `pass` stub with a comment claiming it existed (documented as "remaining work" since 5th iter; the comment was misleading)                                                                                                                                                                                           | `region_id` param added to `match()`; `ncc_verify_per_terrain` dict actually consulted; gate uses resolved threshold |
| P5  | `scripts/bench_latency.py`               | "MF+cached" and "MF+cold" branches were byte-identical (`feature_cache=None` both) → the LOOP-4 latency claim was unreproducible                                                                                                                                                                                                                  | Cache path passed when file exists; honest note that multi_feature currently does not consume the cache              |

Also fixed: AGENTS.md production config. `select_by="inliers"` was the legacy_5th
cell the 6th iteration replaced; every R06-lineage script and all 10th/11th
iteration numbers used `select_by="ncc"`. Docs now read `select_by="ncc"`.

### 1.2 C++ fixes (RDK X5 estimator)

| #   | File                                                          | Bug                                                                                                                                                                                                                                        | Fix                                                         |
| --- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| C1  | `src/drivers/imu_driver.cpp`                                  | IMU timestamps from `system_clock` epoch (~1.7e15 µs) vs camera `CLOCK_MONOTONIC_RAW` → `sensor_sync` rejected every frame → main fusion loop never processed anything                                                                     | `steady_clock` timestamps (CLOCK_MONOTONIC domain)          |
| C2  | `src/estimator/measurement_model.cpp`                         | `H_yaw` used the roll denominator `b = 1−2(x²+y²)` and missed the `−4q_z` terms; yaw Jacobian wrong for the covariance update                                                                                                              | Correct yaw denominator `1−2(y²+z²)` with all four partials |
| C3  | `src/estimator/ekf_core.cpp`                                  | `update_yaw` covariance evaluated `H_yaw` at the POST-update quaternion (wrong linearization point); `last_innovation_norm` stored sqrt(maha²) but compared against a χ² threshold (wrong scale, made INNOVATION_REJECT unreachable)       | Pre-update H; squared Mahalanobis stored                    |
| C4  | `src/constraints/motion_constraint.cpp`                       | `apply_rp_constraint` called `apply_zero_vel_z` as a "proxy" — a zero-vertical-velocity pseudo-measurement that corrected nothing and hammered Vz→0 during banking. Superseded by the LOOP-8 gravity-gated attitude update already in main | No-op with explanatory comment                              |
| C5  | `src/main.cpp`                                                | Smoothness constraint passed `ekf.state()` as `prev_state` → `delta_v = 0` always, constraint dead                                                                                                                                         | `prev_state` captured at frame start                        |
| C6  | `src/main.cpp`                                                | `skip_flow` set by `apply_all` AFTER the flow fusion → the IMU-consistency veto was dead code                                                                                                                                              | Constraints moved before flow fusion                        |
| C7  | `src/main.cpp`                                                | Flow velocity mapped pixel displacement directly to v_ned with hardcoded negation, ignoring yaw; `FeatureTracker::compute_flow_velocity` (which rotates body→NED) existed but was never called                                             | Use `compute_flow_velocity` with R_bn from state            |
| C8  | `src/main.cpp`                                                | Baro altitude fused with `origin_alt_msl_m = 0` placeholder → measurement ≈ −MSL altitude → permanently gated                                                                                                                              | First baro sample captured as launch-site MSL               |
| C9  | `src/main.cpp` + `src/mavlink/ap_monitor.{h,cpp}` + `types.h` | `GPS_RAW_INT` never parsed; `GpsMonitor` constructed but never fed; GPS health stuck LOST                                                                                                                                                  | Handler added, state fields added, main-loop wiring         |
| C10 | `src/mavlink/ap_monitor.cpp`                                  | `ekf_healthy = (flags & EKF_POS_HORIZ_ABS)` — a GPS-availability bit → AP EKF reads "unhealthy" exactly when GPS is denied (the system's operating point)                                                                                  | Any-position-source flag set (ABS\|REL\|PRED)               |
| C11 | `src/imu/imu_integrator.cpp`                                  | `AngleAxis(0, NaN)` when gyro exactly zero → NaN propagation                                                                                                                                                                               | Zero-norm guard                                             |
| C12 | `src/map/map_matcher.cpp`                                     | Phase-corr refinement ADDED the offset; per cv::phaseCorrelate doc semantics (`src2(x) = src1(x+shift)`) the query position is `kf_pos − shift·gsd`. Comment said the same thing while the code did the opposite                           | Subtract corr from kf_position and delta_pos                |
| C13 | `config/ekf_params.yaml`                                      | `Q_accel_bias: 1e-7` — the 13th iteration's measured fix (1e-5, header default) never reached the config the binary loads                                                                                                                  | `1e-5`                                                      |

### 1.3 A regression caught by tests, then fixed properly

Added a Mahalanobis gate to `update_yaw` (3σ). Log-replay tests immediately
diverged to NaN at t=1312 s on the 43 km Bhopal flight. Bisection (gate off /
on, clean-tree baseline via `git stash`) showed: the gate rejects ALL yaw
measurements once P_att shrinks, because the AP yaw convention carries a
constant offset — the EKF then loses yaw tracking entirely. **Gate dropped**,
H_yaw fix and pre-update linearization kept. Lesson recorded in-code: yaw
gating needs convention-aware offset handling first; R_map_att is the only
yaw quality lever until then.

### 1.4 Test status and honesty

- Python: **121/121 pass** after all fixes.
- C++: vcpkg + MSVC host build (`build_fixcheck/`), **55/63 pass**. The 8
  failures (LogRotation + LogReplay variants) fail only in full-suite runs and
  pass individually. Stash-clean-tree rebuild proves the same 8 fail on the
  pre-session baseline → **pre-existing test-isolation flakiness** (shared
  temp dirs; LogRotation maintenance deletes files other tests still need),
  not a regression from this session.
- The flight binary (`kp_vio` exe) is Linux-only in CMake; `main.cpp` edits
  are compile-verified through the library on MSVC but the full binary has
  never been built anywhere. Root `CMakeLists.txt` is a stale duplicate of the
  real one under `final_cpp_implementation/`.

---

## Part 2 — Accuracy Re-Derivation (all 20 iterations)

Every iteration doc read (1-20). Iterations 11-20 code claims spot-verified
against source: prior-ratio gate (Python + C++ sat_matcher), NCC tiebreak,
VINS F-matrix blocks, midpoint `propagate_sample`, replay VIO parameter,
coop_uav tests — all present and consistent with the docs. Two items the docs
correctly mark as unbuilt: `YoloBpuBuildingDetector` (iter 16 plan) and the
iter-15 architecture changes (Huber-on-map-fix, frame-alignment layer).

### 2.1 Matcher per region (10th+11th iteration state, n=40, drift 300 m, DEM on)

| Region | Type               | Matched | Median err | Fatal | Status                                                             |
| ------ | ------------------ | ------- | ---------- | ----- | ------------------------------------------------------------------ |
| R01    | riverside          | 1/40    | 4.5 m      | 0     | ceiling 10% — reference imagery problem                            |
| R03    | farmland           | 34/40   | 13.9 m     | 0     | only reliable region; ~14 m ≈ dataset GPS noise floor (hypothesis) |
| R04    | repetitive furrows | 34/40   | 30.9 m     | 7     | sub-tile aliasing; unfixable per-frame (Findings T/U/V)            |
| R06    | mountain/forest    | 21/40   | 23.3 m     | 7→0   | whole-tile aliases solved by prior-ratio gate (11th)               |
| R08    | non-planar         | 2/40    | 20 m       | 0     | ceiling 7.5%                                                       |
| R09    | suburban           | 1/40    | 21.7 m     | 0     | ceiling 15.4%; ncc 0.30 over-rejects                               |

### 2.2 Full system (VIO + map fixes, real flights)

| Condition                      | Error                                                      | Source                                                           |
| ------------------------------ | ---------------------------------------------------------- | ---------------------------------------------------------------- |
| VIO-only, real camera+IMU      | 2.26 m / 318 s circle; 5.35 m / 512 s fig-8 (~1%/distance) | coop_uav RTK (20th)                                              |
| + 1 Hz fixes, RTK-quality      | 0.34 m p50                                                 | coop_uav — NOT representative (real fixes are satellite matches) |
| + 1 Hz fixes, 15 m fix quality | ~13-15 m                                                   | Bhopal 43 km replay (18th)                                       |
| IMU-only, no camera            | 53 m mean, km-scale spikes                                 | Bhopal log (13th) — pathological case                            |

**Bottom line: absolute accuracy ceiling = satellite fix quality (10-15 m),
not the estimator.** 0.34 m is achievable only with RTK-class fixes, which the
deployment does not have.

---

## Part 3 — Deployability Verdict

| Component        | Verdict                                                                                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C++ ESKF         | Deployment-grade. VINS-class on real data (p50 5.1 m / 43 km with 1 Hz fixes; 2.26 m drift / 318 s real camera+IMU; vs VINS-Mono 0.28 m on same flight) |
| Alias handling   | R06 whole-tile gated (fatal 0%); R04 sub-tile covariance-absorbed                                                                                       |
| Flight binary    | Never built on Linux/RDK; this session's fixes (clock, baro, flow, GPS) make it buildable-correct but untested on hardware                              |
| Matcher latency  | 0.5-7.4 s/frame → loop-closure only (0.5-2 Hz), never primary nav                                                                                       |
| Terrain coverage | 6 of 9 UAV-VisLoc regions at ceilings; deployed over unsolvable terrain = pure VIO drift                                                                |
| BPU              | Unused; YOLO detector unbuilt                                                                                                                           |

**Verdict: estimator yes, full system not yet.** One X5 flight closes the gap
for demo-grade on farmland-type terrain; production flight-grade requires the
coverage + latency work. Largest risk: integration bugs in the never-run
flight path — exactly the class this session found 6 of.

## Part 4 — Paper Novelty Verification

Two passes. First pass (C1-C7 grading, 2-paper plan) ran on a `general`
subagent that was silently routed to glm-5.2 by the pre-session config — a
config bug this session exposed and fixed. Second pass re-verified the
load-bearing facts independently (UAV-VisLoc paper body: no drone/GPS
hardware spec; satellite maps 2021-2024 vs drone images 2016-2023 = up to 6
years vintage gap; AnyVisLoc pipeline = retrieval → matching → PnP).

### 4.1 Deep novelty check grades (OpenAlex + Crossref + dblp + arXiv APIs)

| Claim                                            | Grade                         | Consequence                                                                                                                   |
| ------------------------------------------------ | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| C1 temporally-coherent constant-offset aliases   | NOVEL (narrowly)              | Closest: Lajoie et al. RA-L 2019 (coherent outliers, indoor SLAM); Vineyard SLAM 2026 trio (row-level aliasing, ground LiDAR) |
| C2 consistency filtering discriminates backwards | NOVEL as measurement          | TACO 2026 foreshadows mis-inclusion; no backwards RATE anywhere                                                               |
| C3 homography inlier saturation ~15              | CONTRADICTED as general claim | OrthoTrack 2026: PnP-RANSAC+DSM sub-meter, no saturation. Scope to feature-based homography on repetitive terrain             |
| C4 wrong lock = appearance optimum               | NOVEL as curve                | Intuition known (Mitra CVPR 2008); 16/16 monotone-wrong measurement is new                                                    |
| C5 per-region zero-solvable zones                | CLEANEST NOT-FOUND            | Strongest standalone claim                                                                                                    |
| C6 vintage-mismatch impact                       | FALSIFIED as general claim    | OrthoTrack MovingDrone = 14-yr map-age benchmark. Narrow to farmland + specific 6-yr distribution                             |

### 4.2 Reframed paper

**"Coherent-offset aliasing: a UAV-vs-satellite failure class invisible to
consistency-based rejection"** = C1 + C2-backwards-rate + C5, with C3/C4 as
region-scoped supporting evidence, C6 as one ablation table. Must cite and
differentiate against: OrthoTrack/OrthoLoC/MovingDrone (same task SOTA),
Lajoie DC-GM (theoretical coherent outliers), Kinnari et al. (pipeline
ancestor), Vineyard SLAM 2026 (phenomenon converging from LiDAR side).

Secondary paper (unchanged): edge estimator vs VINS-Mono validation, iter
13-20 material. Benchmark-hygiene paper deferred pending RTK audit.

---

## Part 5 — Session Config Change

All opencode routing (driver, build/plan/general/explore/title/summary/
compaction agents, small_model, five agent/command frontmatter files) moved to
`deepseek-v4-pro`. glm-5.2 documented as manual escalation only; config is
static, no automatic fallback exists.

## Honest Limits

- `main.cpp` edits not exercised by the flight binary (Linux-only build).
- The 8 full-suite C++ test failures remain (isolation flakiness); fixed by
  test-suite hygiene, not by this session's scope.
- Literature checks pass 1 ran on glm-5.2; pass 2 re-verified the decisive
  anchors independently but did not re-run every query.
- No benchmark was re-run; all matcher numbers are carried forward from the
  10th/11th iteration measurements. The Python fixes (P1-P5) do not change
  matcher benchmarks (P1 affects only fused ESKF paths; P2-P5 affect latent
  or unreached paths) — the AGENTS.md config correction is documentation-only.
- Yaw gate regression (Section 1.3) is a negative result: a plausible
  improvement measured against real data and withdrawn.

---

_Document written 2026-08-15. Code changes uncommitted (per project practice).
Build artifacts in `E:\kp_vio\build_fixcheck\` (vcpkg-configured, reusable).
This iteration's scripts/artifacts: none new — all changes are source edits
listed in Sections 1.1-1.2 plus `~/.config/opencode/opencode.jsonc`._

---

# Part 6 — Draft v3 Session (2026-08-15 → 16): Reviewer-Weakness Fixes, Ceiling-Class Forensics, Field-Standard Fixes

**Date:** 2026-08-16 (appended)
**Scope:** close the three structural reviewer risks identified against paper
draft v2 (one matcher / one region / negative-result core), then — on user
challenge — verify the ceiling-class audit and implement the field's standard
remedies that had been cited but never measured. All experiments in `E:\kp_vio`
with the repo venv; kill criteria pre-registered in each gate's docstring.

## 6.1 Headline

| Item                            | Result                                                                                               |
| ------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Draft v3 written                | `research_paper_1/06_paper_draft_v3.md` — all v2 corrections retained                                |
| One matcher → closed            | signature + rate structure reproduced under ORB-only, SIFT-only, SuperPoint+LightGlue                |
| One region → bounded            | boundary map exhaustive 11/11; split-half internal replication; attitude/vintage confounds ruled out |
| Negative-result core → reframed | constructive Sec 5.1 (deploy now / quantified design targets)                                        |
| Ceiling-class cause found       | geometry failure (planar homography vs relief/buildings), not texture/scale/camera                   |
| Audit verification (4 attacks)  | all negative — audit stands; side-finding: loose thresholds turn no-fix into wrong-fix               |
| PnP+DSM (field standard)        | KILLED on ceiling class — correspondence-limited, not model-limited                                  |
| GNC (Yang 2020)                 | KILLED — converges to empty inlier set (0–7% kept)                                                   |
| Robust smoother (S4)            | KILLED with mechanism — trusted motion carries drift + coherent aliases                              |
| DEM grids                       | R02/R10 (500 m), R05/R10 (90 m), R07 (500 m) built via OpenTopoData                                  |

## 6.2 Matcher independence (Sec 4.7 v3)

`gt_tile_matcher_variants.py` (GT-tile contiguous, protocol identical to
Action 1/3, only the correspondence source varies) + `bench_rejectors_variant.py`
(monkeypatched `match_pooled_multi` inside `map_matcher`; pools never mixed with
Action-2 pools).

- Signature reproduces under every matcher family: axis within 3° (167.2±3°),
  hole-at-zero 0.18–0.22, alias lag-1 coherence 1.57–2.55× below null, good at
  null. Solve rates 83% (pooled) / 67% (ORB) / 64% (SIFT) / 51% (LightGlue);
  alias fraction stable 15–17% of solved.
- Rate structure matcher-stable on R04 d300: seq-consistency backwards
  (0.78–0.91), prior-ratio oracle blind to sub-tile (0.89–0.93), PCM/frame-
  alignment forward only via coverage destruction (19–32% good kept).
- LightGlue rate cells underpowered (2 fatal frames; yield collapse 9/40 on
  R03 control) — signature-level evidence only; its one nominal bar pass
  declined under the small-cell rule.
- Implementation note: kornia 0.8.2 ships LightGlue but NOT SuperPoint; the
  repo's `superpoint_lightglue_match` falls back to a KeyNet path that returns
  ZERO cross-modal correspondences. Use the standalone `lightglue` package
  (SuperPoint.extract + LightGlue). This is why the first LightGlue variant run
  came back 0/40 — an artifact, since corrected.

## 6.3 Boundary map + confounds (Sec 4.1 Result 6, Sec 4.5 v3)

- Split-half internal replication of pooled n=610: both halves show the
  signature on the same axis (~167°) with coherent alias tails (1.16×/3.16×).
- **Attitude ruled out:** CSV carries Omega=pitch, Kappa=roll (Phi1/Phi2=yaw —
  NOT tilt, despite their names). R04 stream effectively nadir: 608/610 frames
  ≤10° tilt; excluding the 2 tilted frames leaves the signature unchanged.
  The 7th-iteration nadir-correction kill (1.6 m vs 2 m bar, Finding L) is now
  quoted as the ruling-out evidence.
- **Imagery vintage ruled out for the alias class:** R03 (2018-10-23) and R04
  (2018-10-24) are consecutive-day flights in the same district — identical
  satellite vintage, opposite outcomes. Dataset does not publish satellite
  capture dates, so vintage remains untestable for the ceiling class.

## 6.4 Ceiling-class forensics (Sec 4.5 v3, action doc 09 §6.5)

`probe_regions_forensic.py` (n=40, DEM-corrected AGL, records tile existence,
per-detector correspondence counts, inliers, GSD ratio) + `fx_sweep.py`.

| Region        | Solved (GT tile) | corr med → inlier med (conv%) | Cause                             |
| ------------- | ---------------- | ----------------------------- | --------------------------------- |
| R01           | 1/40             | 38 → 5 (13%)                  | non-planar (buildings/water)      |
| R02           | 3/40             | 42 → 5 (12%)                  | non-planar                        |
| R03 (control) | 27/40            | 84 → 33 (39%)                 | —                                 |
| R05           | 0/40             | 24 → 5 (21%)                  | ~400 m relief                     |
| R07           | 0/30             | 5 → 4 (80%)                   | 30-frame flight only              |
| R08           | 3/40             | 57 → 5 (9%)                   | non-planar + water                |
| R09           | 3/40             | 54 → 6 (10%)                  | non-planar; 14/40 GT tiles absent |
| R10           | 0/40             | 16 → 5 (30%)                  | relief + canopy                   |

Rules-out measured: satellite maps uniform 0.27–0.38 m/px across all 11
regions; fx sweep 500–1200 flat (3000×2000 sensor regions use a different
camera, but focal is not the limiter); tilt uncorrelated with inliers
(+0.02…+0.15); AGL corrected — R02/R07/R10 raw heights were 2.7–4.6× off AGL
pre-DEM, so earlier "unsolvable" verdicts for them were partially AGL artifacts
(they stay unsolvable after correction, but the pre-DEM numbers are void).
R07 CSV holds only 30 frames (the action-doc "0/100" was "0/30").

**Correction to Part 2.1's framing:** the ceiling class is not primarily a
"reference imagery problem" — it is a geometry failure. Features exist
(16–57 correspondences); the homography's planar assumption cannot convert
them. And the class is doubly specific: sub-tile aliasing needs _planar_
repetitive terrain, which is why R04 is the only instance.

## 6.5 Audit verification — four independent attacks, all negative (action doc 09 §6.6)

User challenged "the images are good enough". Re-tested with independent
methods:

1. **Direct photometric alignment** (template NCC, yaw×scale grid + ECC affine
   refine): no signal on ANY region, including working R03/R04 (best global NCC
   0.17–0.54; errors 100–460 m everywhere).
2. **NCC at the known-true alignment** with the dataset's own yaw (Phi columns)
   - fine scale sweep: **0.06** on an R03 frame the feature pipeline solves at
     24.5 m / 22 inliers. Bulk pixels do not correspond cross-season/cross-sensor
     at 1 m/px; the task rides on sparse stable keypoints. Intensity-based
     "better similarity measures" are structurally unsuited without a near-exact
     transform.
3. **Yaw-metadata pre-rotation + feature match:** no change (rotation-invariant
   descriptors don't need it; interpolation adds noise).
4. **RANSAC/ratio relaxation** (ratio 0.85, threshold 10–15 px): solve counts
   rise (R02 0→5/15, R08 0→5/15, R09 1→4/12) — **but the new solves are wrong
   locks** at 107–467 m median error. R03 control stays clean at every setting.

**Side-finding (in the paper):** the no-fix/wrong-fix boundary is a threshold
choice; the strict side is the safe one. A loosely tuned matcher converts the
ceiling class from a safe no-fix failure into a confident wrong-fix failure.

## 6.6 Field-standard fixes, implemented and measured (Sec 4.8 v3, action doc 10)

Only untested populations were run; nothing from a closed gate was redone.

**PnP+DSM (AnyVisLoc/OrthoLoC/OrthoTrack geometry) on the 7 ceiling regions —
KILLED.** `gate_pnp_ceiling.py`: DEM grids rebuilt at 90 m for R05/R10; IPPE
(planar) / EPNP (relief) per frame; solvePnPRansac 8 px. PnP solves fewer
frames than the homography everywhere (healthy control R03: 12 vs 32/40) and
worse where it solves (34–338 m). Ceiling class is correspondence-limited, not
model-limited — the field's standard geometry swap buys nothing on this data.

**GNC (Yang 2020) graduated robust frame alignment — KILLED.**
`gnc_and_smoother.py` over all Action-2 pools and the three variant pools:
keeps 0–7% of fixes in every cell, every matcher, every drift — the graduation
converges to an empty inlier set (the prior↔estimate offset has no constant
mode; Finding U's scatter). Sixth rejection family measured; cleanest
confirmation of the gauge argument.

**Robust fixed-lag smoother (survey S4, GTSAM/TACO-class) — KILLED with
mechanism.** GM-kernel map-fix factors + trusted prior-delta motion factors,
IRLS Gauss-Newton. Implementation validity pre-checked on synthetic data (an
isolated 199 m wrong fix is pulled to 8.9 m — the two earlier implementation
bugs found this way: (a) robust kernels on BOTH factor types decouple wrong
fixes entirely instead of healing them, so the faithful design trusts motion
and only robustifies map factors; (b) a motion-gradient sign error that blew
the solve up). On real streams: d150 moves R06 whole-tile aliases a median
367 m but lands them wrong — alias chains follow the aircraft, so the trusted
motion chain encodes them (Finding U extended to whole-tile). d300/d600
degrade sharply (R03 13.9→54.5 m median; R04 30.9→142.4 m): at 7 s spacing the
drift random walk dominates prior deltas, so trusting motion drags correct
fixes away and the robust kernel down-weights the wrong side. **Robust
back-ends need trusted odometry this dataset does not provide** — the back-end
half of the "odometry regime" conclusion, measured rather than assumed.

**Net:** none of the field's standard remedies rescues the ceiling or alias
classes on this data. The boundary map is a property of the reference imagery
and the frame spacing, not of the estimator choices.

## 6.7 What changed in the paper

- `06_paper_draft_v3.md` written: Sec 4.1 Result 5/6 (split-half, attitude,
  vintage), Sec 4.5 rewritten (per-region cause table + 4-way verification +
  wrong-lock side-finding), Sec 4.7 (matcher independence, 2 tables), Sec 4.8
  (field-standard fixes), Sec 5.1 item 5 (ceiling class = geometry; coverage
  checks), limitations rewritten, claim-evidence map +10 rows, references +4
  (Lowe, Rublee, DeTone, Sarlin).
- Action docs: `09_action6_second_matcher_boundary.md`, `10_action7_field_standard_fixes.md`; `00_PLAN.md` status log updated.
- New artifacts in `research_paper_1/artifacts/`: `gt_variant_{orb,sift,lightglue}_R04.json`, `action2v_*`, `boundary_coherence_R0709.json`, `v3_matcher_analysis.txt`, `forensic_probe.json`, `pnp_ceiling.json`, `gnc_and_smoother.json`, `pairs/` (drone-vs-GT-tile visual composites for R02/R05/R10).
- New scripts in `E:\kp_vio\kp_vio_py\scripts\`: `gt_tile_matcher_variants.py`, `bench_rejectors_variant.py`, `analyze_v3_matchers.py`, `probe_regions_forensic.py`, `fx_sweep.py`, `gate_pnp_ceiling.py`, `gnc_and_smoother.py`.

## 6.8 What remains (as of 2026-08-16)

1. **LaTeX sync** — `latex/paper.tex` still v2; v3 is authoritative md. New
   sections, tables, and 4 references need TeX.
2. **Figures for the new sections** — matcher-independence signature panel,
   boundary map, smoother/GNC results; `make_paper_figs.py` covers v2 figs only.
3. **Adversarial review pass** on v3 per the research-paper-writing skill's
   `paper-review.md` checklist.
4. **Per-terrain `ncc_verify`** — the P4 fix (21st iteration) made the config
   key real; the R09 2.5%→7.5% at ncc≤0.10 measurement exists; the benchmark
   that adopts a per-region threshold has still never run.
5. **ViLD replication** — access request pending (Zenodo 19223815, email-gated);
   protocol ready in `07_replication_protocol.md`.
6. **GT audit / RTK** — only path to test the R03 ~13 m noise-floor hypothesis.
7. **Video-rate capture** — hardware item; needed for the odometry half of the
   robust-smoother conclusion.

## 6.9 Honest limits

- PnP arm uses the pooled matcher's correspondences only; a dense matcher
  (RoMa/DKM — the pairing AnyVisLoc/OrthoLoC actually use) was not installed,
  so "PnP+DSM killed" is measured for the project's matcher. The gate's
  conclusion (correspondence-limited) makes a dense-matcher rescue unlikely
  but not excluded; Sec 4.8 says what it says.
- GNC/smoother run on the step-sampled fix pools (n≈16–35 per cell); the
  smoother's d600 cells are n=16–25.
- ASTER 30 m is a bare-earth DEM — it cannot represent buildings (R01/R08/R09)
  or tree canopy (R10), so the PnP-DEM arm is the strongest available test for
  terrain relief (R05/R10) and merely the field's own reference class for the
  built regions.
- All Action-2 numbers carried forward unchanged; this session only added
  cells, it did not re-measure pooled production rates.

---

_Part 6 appended 2026-08-16. Companion docs: `research_paper_1/06_paper_draft_v3.md`
(authoritative), `09_action6_second_matcher_boundary.md`, `10_action7_field_standard_fixes.md`,
`00_PLAN.md` status log. All new measurements this session were run with
pre-registered kill criteria and are reported with denominators inline._
