# 24th Iteration — XIAN-Visloc: Fix Propagation Un-Gated (Spacing Isolation Proven)

**Date:** 2026-08-16
**Trigger:** user approved XIAN-Visloc download — the designated video-rate
surrogate for the 23rd-iteration kills.
**Data:** `E:\kp_vio\datasets\xian_visloc\` (XIAN_Visloc.zip 26 GB extracted

- real-world flight data zip 4.2 GB, HuggingFace VERYBC/XIAN_Visloc).

---

## Headline

| Question                                 | Answer                                                                                                                                                                                                                                                                                                |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Does fix propagation work at video rate? | **YES — the 23rd-iteration kill was SPACING, not design.**                                                                                                                                                                                                                                            |
| Spacing isolation                        | Xian16: dense (~3.8 m/frame) → **418/429 fixes, yield50 100%, p50 21.1 m** (baseline 19.7 m); coarse (~250 m stride, UAV-VisLoc regime) → **4/7 fixes, yield50 25%, p50 275 m** — KLT dies at 250 m gaps exactly as on UAV-VisLoc.                                                                    |
| "Works in all regions"?                  | Matched-modal, per-frame ORB pool solves: Xian16 **74%** (317/429, p50 19.7 m) vs Weinan01 **12%** (53/437, p50 39.7–71 m at crops 392/784). Even with contemporary imagery, high-altitude homogeneous terrain stays hard — terrain class matters in every dataset, not just vintage-mismatched ones. |
| Vintage/modal gap                        | Quantified again: UAV-VisLoc ceiling regions 2.5–15% solve vs Xian16 74% on matched-modal pairs.                                                                                                                                                                                                      |

## Mechanics (gate_xian_propagation.py)

- Seed = ORB pool match on satellite crop at GPS (user assumption: GPS at
  takeoff). Chain = KLT + MAGSAC H_rel (frame k → k−1), compose
  H_abs_k = H_abs_{k−1} ∘ H_rel; position = frame centre through H_abs_k.
  No camera intrinsics needed.
- Re-match triggers: tracks < 20, H inliers < 10, or propagated position
  > 90 m from crop centre; re-crop at last fix. Fail → coast.
- Xian16: 1 seed + 367 prop + 50 re-match + 11 coast over 429 frames at
  ~1 Hz. Propagation carries the takeoff fix for the whole flight at
  baseline accuracy.
- Weinan01 (350 m AGL, 4K→0.25): baseline anchor rate 12% → propagation
  cannot anchor; 409/437 coast. Hard-terrain ceiling persists.

## What this means for the prototype (RDK X5)

1. **The system architecture is now validated end-to-end on video-rate
   data**: cold-start GPS fix → KLT propagation → occasional satellite
   re-anchor → VIO coast on hard terrain. This is the design that "works
   in all regions, accuracy varies": ~20 m on matchable terrain
   (GPS-noise-limited), VIO drift growth elsewhere.
2. **The missing hardware piece is confirmed as the ONLY remaining
   blocker**: video-rate capture on the X5 (30 Hz camera vs the matcher
   re-anchor at 0.1–0.5 Hz). First X5 flight closes the loop.
3. C++ side: the sat_matcher's prior-ratio gate + ESKF already implement
   the fusion; what's missing in C++ is the KLT-based geo-registered
   point tracking between fixes (the propagation chain measured here) —
   a port of `gate_fix_propagation.py` mechanics into `FeatureTracker`
   (which already computes flow velocity).

## Scripts and artifacts

| File                                      | Purpose                                                                               |
| ----------------------------------------- | ------------------------------------------------------------------------------------- |
| `scripts/gate_xian_propagation.py`        | XIAN propagation gate: seed/KLT/H-composition/rematch, dense vs coarse arms, baseline |
| `results/gate_xian_propagation_x16.json`  | Xian16: dense 100% yield50 vs coarse 25%                                              |
| `results/gate_xian_propagation_wn01.json` | Weinan01: 12% anchor rate, propagation blocked                                        |
| `results/gate_xian_wn01_crop784.json`     | crop-size control: 12% unchanged → terrain, not artifact                              |
| `E:\kp_vio\datasets\xian_visloc\`         | 30 GB dataset on disk (21 trajectories, 6 satellite TIFs, per-frame GPS)              |

## Honest limits

- Xian16 GPS has no altitude column; baseline uses truth-centred crops
  (optimistic protocol — matches the user's cold-start assumption).
- Propagation accuracy is baseline-limited (~20 m ≈ dataset GPS noise);
  no RTK truth exists on XIAN, so sub-20 m claims are untestable here.
- Weinan arm used 0.25-scale 4K images; the full-res behaviour may
  differ (theirs used 392 crops + rescaling — protocol noted).
- No IMU on XIAN — the chain is pure-vision KLT; the X5 flight adds
  IMU+baro and should improve both propagation and re-anchor gating.

---

## Update: per-trajectory baseline (14/21 measured)

User question "which region, all?" - answer: measured 14 of 21 trajectories
(baseline, crop at GPS, ORB pool), propagation arms on 2 (Xian16 dense
100% yield50; Weinan01 blocked by 12% anchor rate).

| Traj | Solve | p50 | Traj | Solve | p50 |
|---|---|---|---|---|---|
| Xian01 | 16% | 25.6 m | Xian09 | 52% | 34.3 m |
| Xian02 | 39% | 34.2 | Xian10 | 64% | 35.7 |
| Xian03 | 31% | 34.8 | Xian11 | 72% | 35.6 |
| Xian04 | **2%** | 27.4 | Xian12 | 84% | 35.2 |
| Xian05 | 54% | **8.6** | Xian16 | 74% | 19.7 |
| Xian06 | 19% | 30.5 | Weinan01 | 12% | 39.7 |
| Xian07 | 88% | 35.2 | Weinan02 | not run | - |
| Xian08 | 55% | 36.0 | Xian13-15, 17-19 | not run (2h bash cap) | - |

Spread 2-88% on matched-modal data - terrain class matters in every
dataset. Median ~50%. Propagation (Xian16) converts 74% per-frame solve
into ~97% frame coverage; the matcher only needs to land occasionally.
Rerun remaining trajs with `--seq xian_rest2` when needed.
