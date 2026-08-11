# 15th Iteration — VINS-Fusion Cross-Reference: What the "Next Level" Provides

**Date:** 2026-08-11
**Scope:** read VINS-Fusion (HKUST, the VINS-Mono successor) to answer:
what does it add, and what is applicable to kp_vio's architecture (ESKF
+ map matching on RDK X5)?

---

## VINS-Fusion vs VINS-Mono — the three additions

| Module | What it is | kp_vio relevance |
|---|---|---|
| `global_fusion` | **GPS fusion on top of VIO** — a pose-graph optimizer that aligns the VIO trajectory to absolute GPS positions | **Directly the same problem kp_vio solves with map matching** (absolute fixes on top of VIO) |
| `loop_fusion` | **Global pose graph + loop closure** — DBoW2 vocabulary, loop detection, 4-DoF pose-graph optimization | The loop-closure side of kp_vio's map matching (but DBoW2 is a learned/CPU-heavy vocabulary) |
| sensor stack | Mono, stereo, stereo+IMU, GPS+IMU, and **magnetometer/barometer fusion** in newer branches | Matches kp_vio's planned sensor stack |

---

## What global_fusion actually does (read in full)

`globalOpt.cpp` — a **separate thread** running a Ceres pose-graph over
all keyframe poses:

1. **Two factor types** (Factors.h):
   - `RelativeRTError` — the VIO relative motion between consecutive
     keyframes (6-DoF residual, weighted by t_var=0.1, q_var=0.01)
   - `TError` — the GPS absolute-position factor (3-DoF residual,
     normalized by the GPS `posAccuracy` as the per-fix variance)
2. **A Huber loss (1.0)** on the GPS factors — **robust against bad GPS
   fixes** (exactly kp_vio's alias/outlier problem!)
3. **The transform `WGPS_T_WVIO`** — a single rigid transform between
   the VIO local frame and the GPS/global frame, recomputed at the end
   of each optimization from the newest pose. All future VIO poses are
   mapped through it, so **the fusion is a frame alignment, not a
   per-fix injection**.
4. **Runs at ~0.5 Hz on a separate thread** (2s sleep), triggered by
   `newGPS`.

**The key architectural insight for kp_vio:**

VINS-Fusion does NOT feed GPS positions into the VIO EKF as measurements.
It keeps VIO pure (drift-free short-term), and a **separate pose-graph
layer** aligns the whole trajectory to the absolute fixes, recomputing a
rigid transform. This is fundamentally different from kp_vio's current
design (injecting map-match positions directly into `update_map_position`).

Why this matters for kp_vio:
- **Injecting absolute fixes into the EKF couples the estimator's
  covariance to fix quality** — a wrong fix (alias) corrupts the filter
  state, and the 14th-iteration NaN regression is partly this coupling.
- **VINS-Fusion's separate layer isolates the damage**: bad GPS factors
  are down-weighted by Huber, and the VIO trajectory is only aligned,
  never corrupted.
- This is the architectural fix for the R04/R06 alias problem at the
  SYSTEM level: the map matcher becomes a pose-graph factor with Huber
  robustness, not an EKF measurement.

---

## What loop_fusion provides (pose_graph)

- `detectLoop(KeyFrame*, int)` — DBoW2 vocabulary lookup
- `addLoopEdge` — relative pose constraint between the current keyframe
  and the loop candidate (the "map match" in kp_vio terms)
- `optimize4DoF()` — pose-graph optimization in 4-DoF (x, y, z, yaw),
  keeping roll/pitch from VIO (they're well-constrained)
- `addPrior` — absolute prior on the first frame (the GPS origin)

**Applicable idea:** kp_vio's map matching is a loop closure + absolute
fix. The 4-DoF optimization insight (only correct x/y/z/yaw, trust
VIO's roll/pitch) matches kp_vio's satellite-matcher output (which
corrects position, and yaw comes from the magnetometer).

---

## What is NOT applicable (honestly)

- **Ceres + pose-graph over all keyframes**: on RDK X5 (4 GB RAM, no
  GPU, ARM A55), a full Ceres solve per GPS fix at 0.5 Hz is borderline.
  kp_vio's single EKF is the right CPU budget for the X5. The *ideas*
  (Huber robustness, frame alignment, 4-DoF) are portable; the *solver*
  is not.
- **DBoW2 vocabulary**: CPU-heavy, needs training on the map; kp_vio's
  ORB/AKAZE/SIFT pooled matching + NCC is a lighter loop-closure source.
- **Stereo**: the X5 airframe is monocular.

---

## Concrete recommendations for kp_vio (from this read)

1. **Adopt the Huber loss on the map-match fix** — the single most
   transferable idea. kp_vio's `update_map_position` currently uses the
   innovation chi-square gate (hard accept/reject). VINS-Fusion's Huber
   does the same job continuously: a bad fix is down-weighted smoothly
   instead of hard-gated then force-accepted. This directly attacks the
   alias problem (R04/R06) and the 14th-iteration NaN regression.
2. **Adopt the frame-alignment view for the satellite matcher**: treat
   the map-match as aligning the VIO frame to the global frame (a
   slowly-varying transform), not as per-fix state injection. On the X5
   this can be a lightweight running average of the WGPS_T_WVIO-style
   transform instead of a full pose graph.
3. **4-DoF correction**: the satellite matcher already only corrects
   x/y (position); the yaw comes from the magnetometer. This matches
   VINS-Fusion's optimize4DoF philosophy — keep it that way.
4. **The global frame transform**: add a `WGPS_T_WVIO`-style transform
   to kp_vio's EKF so the local VIO frame and the absolute (map/GPS)
   frame are decoupled — fixes update the transform, not the raw state.
   This is the structural fix for the alias-corrupts-EKF problem.

---

## Status

- Read: `global_fusion/src/globalOpt.cpp`, `Factors.h`, loop_fusion
  `pose_graph.h` interface.
- Reference files retained at
  `C:\Users\lonew\AppData\Local\Temp\opencode\vinsfusion_*.{cpp,h}`.
- Not yet implemented in kp_vio; this iteration is analysis. The
  highest-value next step is #1 (Huber loss on map fixes) — cheap, and
  it targets the open NaN regression + alias tail directly.

---

*Noted limitation: this read covers the mainline VINS-Fusion; the
magnetometer/barometer fusion lives in later HKUST branches
(VINS-Fusion's IMU is the same 15-DoF preintegration as VINS-Mono —
no change there).*
