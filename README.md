# GPS-Denied Navigation for UAVs

**MTech Final Year Project — IIT Madras**
**Student:** Prabhat Pandey | **Last updated:** 2026-04-14

---

## Overview

This project investigates **consistent state estimation for GPS-denied UAV navigation**, with a focus on analyzing how estimation error evolves in visual-inertial systems under realistic sensing imperfections.

The core research question is:

> *How does using AHRS-filtered IMU output degrade VIO filter consistency (NEES), and how does this hidden temporal correlation drive long-term position drift — with validated characterization on WIT HWT905 + RDK X5 hardware?*

The work targets a **dual deliverable**: a research paper (ICRA/IROS/RA-L level) and a working navigation prototype validated on IIT Madras campus flights.

---

## Research Gap

No prior paper has formally analyzed all of the following simultaneously:

| Criterion | This Work | Prior SOTA |
|-----------|-----------|------------|
| Nadir monocular UAV camera (no depth, no LiDAR) | ✓ | Partial |
| Satellite imagery as reference (not DEM/heightmap) | ✓ | Partial |
| Learned + statistically calibrated likelihood `p(z\|x)` on SE(2) | ✓ | Heuristic only |
| Particle filter integration with learned likelihood | ✓ | Partial |
| Monocular VIO as motion model | ✓ | Partial |
| Filter consistency validation (NEES / chi-squared) | ✓ | Not reported |
| Deployment on resource-constrained board (RDK X5) | ✓ | Not attempted |

The closest prior works each satisfy only 2–3 of these 7 criteria. See [`papers/PAPERS_REFERENCE.md`](papers/PAPERS_REFERENCE.md) for the full gap matrix.

---

## System Architecture

The navigation stack uses two coupled estimators running at different rates:

```
HIGH-RATE  (100 Hz): Quaternion-based UKF (QNUKF) on S³ × ℝ³ × ℝ³
  └─ Fuses: IMU preintegration + barometer + monocular VO
  └─ Output: full 9-DoF pose + covariance Σ_UKF

LOW-RATE (0.5–2 Hz): Particle Filter on SE(2)
  └─ State: x₂D = (pₓ, pᵧ, ψ) — horizontal position + heading
  └─ Motion model: VO delta pose from UKF
  └─ Measurement: satellite image likelihood p(z_sat | x₂D)
  └─ Output: drift-corrected global 2D position
```

### Data Flow

```
IMU (100 Hz) ──► Preintegration ─────────────────────────► QNUKF
Barometer    ──► Altitude obs.  ─────────────────────────►  on S³×ℝ³×ℝ³
Monocular VO ──► SelfAttentionVO ─► δP (relative) ──► motion model ──► PF
Magnetometer ──► Heading prior  ─────────────────────────►

Satellite tiles (offline cache) ──┐
                                  ├──► L_θ(z_drone, x₂D) ──► Particle weights
Drone image   (0.5–2 Hz) ────────┘
```

---

## The Core Algorithm — Likelihood Network `L_θ`

The key novelty is a **learned, statistically calibrated measurement likelihood** for the particle filter:

```
p(z | x) ∝ exp( cosine_sim(z_drone, z_sat(x)) / τ(z_drone) )
```

Where `τ` is a **scene-adaptive temperature** output by a learned MLP — high `τ` when the scene is ambiguous (flat distribution), low `τ` when the scene is distinctive (sharp distribution).

### Training Loss

```
L_total = L_InfoNCE + λ₁·L_calibration + λ₂·L_NEES

L_InfoNCE    = standard contrastive loss (correct tile vs. mined negatives)
L_calibration = ECE(predicted likelihood, empirical match rate)
L_NEES       = E[‖x_true − x̂_PF‖²_{Σ⁻¹}] ≈ dim(x) = 3   ← KEY NOVELTY
```

The `L_NEES` term back-propagates through the particle filter, directly tying the learned likelihood to navigation filter consistency. No prior paper does this.

### Filter Consistency (NEES)

A filter is consistent when:

```
NEES_t = (x_true − x̂)ᵀ · P_t⁻¹ · (x_true − x̂) ~ χ²(3)
Acceptable range (95% CI): [0.216, 9.35]
```

If `NEES >> 3`: filter is overconfident (τ too low)
If `NEES << 3`: filter is underconfident (τ too high)

---

## Hardware

| Component | Specification | Role |
|-----------|---------------|------|
| Flight controller | Pixhawk (PX4) | IMU, barometer, magnetometer, motor control |
| Companion computer | RDK X5 | All navigation computation |
| IMU | WIT HWT905-485 (MPU-9250) | Angular velocity + linear acceleration |
| Camera | 1080p global shutter monocular | VO + geo-localization |
| Satellite tiles | Cached on SD card (~5 km × 5 km at 0.3 m/px) | Offline reference map |
| Communication | MAVLink (Pixhawk ↔ RDK X5) | Sensor data + control |

**Hardware note:** The WIT HWT905-485 outputs AHRS-filtered estimates (not raw IMU). This creates a **nested filter problem**: the onboard Kalman filter introduces temporal correlations and hidden bias dynamics that invalidate the white-noise IMU assumption of standard VIO frameworks (VINS-Mono, OpenVINS). Characterizing this degradation is the primary analytical contribution of this project.

---

## Datasets

| Dataset | Purpose |
|---------|---------|
| University-1652 / UniV | Drone-view + satellite pairs, 1652 locations |
| SUES-200 | UAV geo-localization at multiple altitudes (54m–162m) |
| IIT Madras campus (self-collected) | Flight data with RTK GPS ground truth; India-specific domain validation |

---

## Evaluation Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Recall@1, @5, @10 | Retrieval accuracy of geo-localization module | > 85% R@1 |
| ATE (m) | Absolute Trajectory Error over full flight | < 10 m (campus) |
| RTE (m) | Relative Trajectory Error per 100 m | < 5% of distance |
| NEES | Filter consistency (should be ~3 for SE(2) state) | 2.5–3.5 |
| ECE | Expected Calibration Error of likelihood | < 0.05 |
| Inference latency | Per-frame on RDK X5 | < 100 ms |

---

## Key Literature

### Core Survey Papers

| Paper | File | Summary |
|-------|------|---------|
| Visual-Inertial Navigation (2023) | `2307.11758.pdf` | End-to-end VIN via factor graphs; foundational reference |
| Aerial VIO Survey — Scaramuzza (2019) | `1906.03289.pdf` | Authoritative survey of camera+IMU fusion for aerial robots |
| Vision-based Localization under GPS-denial (2022) | `2211.11988.pdf` | Comparative survey: optical flow, VO, VSLAM, map-matching |

### State Estimation / Filtering

| Paper | File | Summary |
|-------|------|---------|
| SE(2,3) Nonlinear Stochastic Observer (2021) | `2104.09920.pdf` | Formal 6-DoF navigation with ASUUB stability guarantees |
| QNUKF — Quaternion UKF (2024) | `2412.02768.pdf` | Full 6-DoF state estimation on UAVs; direct filter baseline |

### Deep Learning VO

| Paper | File | Summary |
|-------|------|---------|
| SelfAttentionVO — CNN+LSTM+Attention (2024) | `2404.17745.pdf` | 22% drift reduction; VO module for this project |
| RNN GPS-Denied Navigation (2021) | `2109.04861.pdf` | Pure-inertial deep learning baseline (no camera) |
| VLocNet++ (2018) | `1804.08366v6.pdf` | Multitask VO + global pose regression |

### Map Matching / Geo-Localization

| Paper | File | Summary |
|-------|------|---------|
| SPRIN-D Winner — Heightmap Gradients (2025) | `2510.01348v1.pdf` | Competition-proven km-scale UAV nav via particle filter |
| Video2BEV (2024) | `2411.13610v4.pdf` | Drone video → BEV → cross-platform geo-localization |

Full annotated reference list: [`papers/PAPERS_REFERENCE.md`](papers/PAPERS_REFERENCE.md)

---

## Ablation Studies (Planned)

1. Heuristic likelihood (Jurevicius 2020 logistic baseline) vs. learned `p(z|x)`
2. Fixed temperature `τ` vs. scene-adaptive `τ`
3. Training without `L_NEES` vs. with `L_NEES`
4. VO-only (no satellite correction) vs. full system
5. Particle count `N` = 100 vs. 500 vs. 1000 (latency vs. accuracy trade-off)
6. Raw IMU vs. AHRS-filtered output — NEES degradation characterization

---

## Implementation Roadmap

### Phase 1 — Literature & Gap Finalization (Weeks 1–4)
- Build final gap matrix from citation chain of key papers
- Finalize research question and paper title

### Phase 2 — Algorithm Prototyping (Weeks 5–10)
- SelfAttentionVO baseline implementation
- Particle filter on SE(2) with heuristic likelihood (replicate Jurevicius 2020)
- Cross-view encoder training on University-1652 / SUES-200
- Scene-adaptive temperature network `g_θ`
- `L_calibration` + `L_NEES` integrated training pipeline

### Phase 3 — Hardware Integration (Weeks 8–14)
- RDK X5 + Pixhawk + camera system setup
- Port encoder and particle filter to RDK X5
- IIT Madras campus flight data collection with RTK GPS ground truth
- Full system evaluation; Allan variance characterization on WIT HWT905

### Phase 4 — Paper Writing (Weeks 12–16)
- Ablation experiments
- NEES and ECE plots
- Comparison against 5 baselines
- Target: **ICRA 2027** (deadline ~September 2026)

---

## Open Questions

1. **BPU vs. CPU for CNN encoder:** Profile ResNet18/EfficientNet on RDK X5 BPU. Use BPU if >3× speedup; else CPU.
2. **Satellite tile resolution:** 0.3 m/px (Google Earth) vs. 0.5 m/px (OSM) — memory vs. accuracy trade-off.
3. **Monocular VO scale recovery:** Barometric altitude as metric scale anchor vs. satellite matching for metric correction.
4. **Optimal particle count `N`:** Real-time 2 Hz update rate constraint on RDK X5.
5. **IIT Madras domain gap:** University-1652/SUES-200 are Western campuses — assess need for fine-tuning or sim-to-real via Google Earth rendering.
6. **Nested filter problem scope:** Determine if the AHRS-consistency analysis is sufficient depth for ICRA/IROS, or is it better positioned as an RA-L journal paper.

---

## Repository Structure

```
gps-devoid-navigation/
├── papers/
│   ├── PAPERS_REFERENCE.md     # Annotated paper index with gap matrix
│   ├── ALL_PAPERS_EXTRACTED.md # Full text extractions
│   ├── map matching/           # Classical map-matching literature
│   └── *.pdf                   # Downloaded paper PDFs
└── summary/
    ├── 1st_iteration.md        # System architecture design (Iteration 1)
    └── 2nd_iteration.md        # Research direction refinement (Iteration 2)
```

---

## Target Venue

**ICRA 2027** (International Conference on Robotics and Automation)
Submission deadline: ~September 2026

Fallback: **IROS 2027** or **IEEE RA-L**

---

*MTech Project — GPS-Denied Navigation Stack for Drones | IIT Madras | 2026*
