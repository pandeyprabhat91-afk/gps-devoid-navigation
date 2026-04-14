# GPS-Denied UAV Navigation — 2nd Iteration Brainstorming

**Project:** MTech Final Year Project, IIT Madras
**Date:** 2026-03-27
**Status:** Brainstorming — direction not yet finalized
**Session type:** Research gap refinement + direction exploration

---

## 1. Why the 1st Iteration Was Rejected

The 1st iteration proposed:
> *"Learning a Statistically Calibrated Measurement Likelihood p(z|x) for Monocular-Satellite Fused Particle Filter Navigation on GPS-Denied UAVs"*

**Problem:** The core algorithm — `p(z|x) ∝ exp(s/tau)` with scene-adaptive learned temperature — is structurally identical to **BEV-Patch-PF (arXiv 2512.15111, 2025)**, which already does:
> `p(z|x) ∝ exp(α_σ · cos_sim / τ_s)` with learned uncertainty-modulated temperature for a ground vehicle particle filter.

The differentiation in the 1st iteration relied purely on domain transfer (ground vehicle → UAV nadir, depth → monocular). That is not sufficient novelty for ICRA/IROS/RA-L.

---

## 2. Literature Confirmed Saturated (Do Not Pursue)

Verified via web search as of 2026-03-27:

| Direction | Why closed |
|---|---|
| DINOv2 + cross-view UAV matching | Multiple IEEE RA-L 2025 papers (AirGeoNet, AGEN, DINO-MSRA) |
| Hyperbolic embeddings + geo-localization | HierLoc (arXiv 2601.23064), HypeVPR (CVPR 2026) |
| Diffusion/score model + localization | LocDiff (2025), DiffPF (arXiv 2507.15716) |
| NeRF + particle filter localization | Loc-NeRF (existing), HAL-NeRF (2025) |
| Learned p(z\|x) + temperature + PF | BEV-Patch-PF (arXiv 2512.15111, 2025) |

---

## 3. Directions Explored This Session

### 3A — Active Geo-Localization via Terrain Informativeness Maps
**Idea:** Build offline Terrain Fisher Information Map (TFIM); when particle filter entropy exceeds threshold, inject waypoints toward high-TFIM regions.
**Rejected by user:** Path selection IS the problem being solved. The drone must follow its mission; deviating to gather information defeats the purpose.

### 3B — Temporal Geo-Localization Memory via Mamba SSM
**Idea:** Replace i.i.d. measurement updates with sequential SSM over drone embedding stream. `p(z_{t-k:t} | x_t)` instead of `p(z_t | x_t)`.
**Status:** Not rejected, but not selected. Medium novelty. Feasibility risk on RDK X5 latency.

### 3C — Domain-Adaptive Observation Model (Appearance Shift)
**Idea:** Online domain-shift estimator δ_t; `p(z|x, δ_t)` conditioned on appearance gap (season, lighting).
**Status:** Moderately novel, high feasibility. Not selected as primary.

### 3D — Semantic OSM Matching (No Satellite Tiles)
**Idea:** Segment drone nadir view semantically; match to OpenStreetMap vector labels instead of satellite imagery.
**Problem for India:** OSM coverage in Indian semi-urban areas is poor and unreliable. Informal settlements, construction zones not mapped.

### 3E — Conformal Prediction for Navigation Uncertainty Bounds
**Idea:** Distribution-free guaranteed coverage intervals using split conformal prediction on PF output. `P(||x_true - x̂|| ≤ r) ≥ 1−α`.
**Status:** Mathematically novel, but is a meta-algorithm on top of a base localization system — not a standalone contribution.

### 3F — Cross-Spectral Navigation (Sentinel-2 Multispectral)
**Idea:** Bridge RGB drone to free Sentinel-2 multispectral tiles (NIR/SWIR). More seasonal robustness, globally free data.
**Problem:** 10m/px Sentinel-2 resolution may be insufficient for sub-10m navigation accuracy.

### 3G — Mixture-of-Terrain-Experts Observation Model
**Idea:** Gated MoE with specialist observation models per terrain type (urban/forest/agricultural/water).
**Status:** Feasible, medium novelty. Strong ablation story. Not selected as primary.

### 3H — Score-Driven Particle Flow (no weight/resample)
**Idea:** Train score network `s_θ(x, z) ≈ ∇_x log p(x|z_drone)`; particles flow via Langevin dynamics instead of weight/resample.
**Status:** Highest mathematical novelty, but high risk. DiffPF (2025) partially occupies this space for generic state estimation.

### 3I — Structure-Disentangled Geo-Localization (India-Specific)
**Idea:** Train cross-view encoder that explicitly disentangles structural features (roads, water body outlines, building footprints) from appearance features (vegetation color, soil tone). Use only structural embedding for particle filter. Targets Indian seasonal variation (monsoon vs. dry: massive NDVI change). Includes first Indian UAV geo-localization dataset (IIT Madras campus, seasonal variation, RTK GPS).
**Status:** Strong for Indian context. Not selected — user wants to return to original research statement.

---

## 4. Return to Original Research Statement

The user clarified the original thesis focus:

> *"Consistent state estimation in GPS-denied navigation, focusing on analysing estimation error evolution in visual-inertial systems under realistic sensing imperfections. The work will study the effects of bias, model assumptions, and temporal correlations on long-term consistency."*

This is an **analytical/theoretical** paper, not a systems paper. The 1st iteration had become a systems paper.

---

## 5. Hardware Constraint

**IMU:** WIT HWT905-485 (~₹8,600, budget < ₹30,000)
- Chip: MPU-9250 (consumer MEMS class)
- Gyro bias instability: ~3–10 deg/hr
- Outputs: AHRS-filtered estimates (not raw IMU) via onboard Kalman filter

**Long-flight accuracy verdict:**
- 5km flight with any IMU under ₹30,000 + monocular VIO: **50–300m position error** (physics-limited, not algorithm-limited)
- Satellite geo-localization is therefore **necessary** for practical 5km navigation accuracy

---

## 6. Strongest Candidate Direction (End of Session)

**Not yet approved by user. Under consideration.**

### Primary: VIO Consistency Analysis under Nested Filter Problem

The WIT HWT905 outputs AHRS-fused data (not raw IMU). Most budget IMUs do. This creates a nested filter problem:

```
raw_IMU → onboard Kalman filter → "IMU" output → VIO navigation filter
                 ↑
         introduces temporal correlations,
         unknown/hidden noise covariance,
         hidden bias dynamics
```

Standard VIO frameworks (VINS-Mono, OpenVINS) assume white-noise raw IMU. When fed AHRS-filtered output, the outer filter's covariance is wrong by construction: noise is colored (shaped by inner filter bandwidth), bias dynamics are hidden.

**Confirmed gap:** No paper has formally analyzed consistency of VIO when using AHRS-filtered IMU output vs. raw IMU.

**Research question:**
> *"How does using AHRS-filtered IMU output degrade VIO filter consistency (NEES), and how does this hidden temporal correlation drive long-term position drift — with validated characterization on WIT HWT905 + RDK X5 hardware?"*

**Also open:**
- Effect of CNN-based VO temporal correlation (SelfAttentionVO outputs correlated across frames) on filter NEES — no paper studied this

### Secondary: Satellite Geo-Localization as Consistency Restoration

When consistency degradation model predicts NEES breach:
- Trigger satellite geo-localization correction (particle filter from iteration 1, simplified)
- Correction rate derived analytically from degradation model, not hand-tuned

---

## 7. Open Questions / Not Yet Resolved

1. **User has not approved direction** — session ended before final selection
2. Is the nested-filter consistency analysis sufficient depth for ICRA/IROS, or is it more of an RA-L / journal contribution?
3. Can the satellite geo-localization secondary component be scoped minimally (simple NCC-based correction rather than full learned likelihood)?
4. IIT Madras campus flights for validation — need to confirm RTK GPS availability for ground truth
5. Dataset: Does collecting an India-specific VIO consistency dataset add publishability, or is the analysis alone sufficient?

---

## 8. Next Steps (Pending User Decision)

- [ ] User to confirm final research direction
- [ ] If VIO consistency analysis confirmed: design analytical framework in detail
- [ ] Decide how much of iteration 1's satellite matching to keep
- [ ] Run Allan variance characterization on WIT HWT905 hardware
- [ ] Identify comparison baselines for NEES analysis

---

*Document generated: 2026-03-27 | Version: 2nd Iteration Brainstorming | Status: Direction not finalized*
