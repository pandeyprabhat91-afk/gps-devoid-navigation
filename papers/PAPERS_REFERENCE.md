# GPS-Denied Navigation — Paper Reference Index

> MTech Project, IIT Madras | Last updated: 2026-03-27

---

## Core Survey & Tutorial Papers

### 1. A Comprehensive Introduction of Visual-Inertial Navigation (2023)
- **File:** `2307.11758.pdf`
- **ArXiv:** https://arxiv.org/abs/2307.11758
- **Method:** Unified treatment of VIN using factor graphs, filter-based and optimization-based estimation
- **Key Contribution:** End-to-end pedagogical resource covering IMU dynamics, camera measurements, and a brief survey of learning-based VIN. Best starting point for understanding the full VIN stack.
- **Relevance:** Foundational theory reference for any VIO/VIN implementation

---

### 2. Visual-Inertial Odometry of Aerial Robots (2019)
- **File:** `1906.03289.pdf`
- **ArXiv:** https://arxiv.org/abs/1906.03289
- **Authors:** Scaramuzza & Zhang
- **Method:** Survey of camera + IMU fusion for aerial robot pose/velocity estimation
- **Key Contribution:** Concise, authoritative reference on state-of-the-art aerial VIO — covers core methods and sensor fusion principles for GPS/LiDAR-denied environments.
- **Relevance:** Baseline reference for drone VIO, strong citation for literature review

---

### 3. Vision-based Localization Methods under GPS-denied Conditions (2022)
- **File:** `2211.11988.pdf`
- **ArXiv:** https://arxiv.org/abs/2211.11988
- **Method:** Comparative survey — optical flow, visual odometry, VSLAM (EKF + optimization), map-matching, lane detection
- **Key Contribution:** Structured categorization of relative vs. absolute localization methods with trade-off analysis and open research directions.
- **Relevance:** Essential for literature review; identifies research gaps

---

## Classical State Estimation / Filtering

### 4. GPS-denied Navigation: Attitude, Position, Linear Velocity & Gravity Estimation with Nonlinear Stochastic Observer (2021)
- **File:** `2104.09920.pdf`
- **ArXiv:** https://arxiv.org/abs/2104.09920
- **Method:** Geometric nonlinear continuous stochastic observers on SE(3) Lie group
- **Key Contribution:** Full 6-DoF navigation fusing IMU + landmark measurements with formal ASUUB stability guarantees. Validated on real quadrotor dataset. Quaternion-based discrete formulation included.
- **Relevance:** Strong theoretical baseline; useful for formal guarantees in research paper

---

### 5. Quaternion-based Unscented Kalman Filter for 6-DoF Vision-based Inertial Navigation in GPS-denied Regions (2024)
- **File:** `2412.02768.pdf`
- **ArXiv:** https://arxiv.org/abs/2412.02768
- **Method:** QNUKF — UKF fusing visual feature tracking (stereo/mono) with 6-axis IMU
- **Key Contribution:** Quaternion-consistent UKF formulation for full 6-DoF state estimation on UAVs. Validated on real drone data against established filtering methods.
- **Relevance:** Direct competitor/baseline for any filter-based VIO approach

---

## Deep Learning Approaches

### 6. An Attention-Based Deep Learning Architecture for Real-Time Monocular Visual Odometry (2024)
- **File:** `2404.17745.pdf`
- **ArXiv:** https://arxiv.org/abs/2404.17745
- **Method:** CNN + LSTM with multi-head attention for monocular ego-motion estimation
- **Key Contribution:** 48% faster convergence, 22% reduction in mean translational drift, 12% improvement in ATE vs. RNN baseline. Demonstrates attention mechanisms improve real-time visual odometry for drones.
- **Relevance:** Strong baseline for learning-based VO; good architecture to benchmark against

---

### 7. GPS-Denied Navigation Using Low-Cost Inertial Sensors and Recurrent Neural Networks (2021)
- **File:** `2109.04861.pdf`
- **ArXiv:** https://arxiv.org/abs/2109.04861
- **Method:** RNN trained on IMU + barometer + magnetometer data (no camera)
- **Key Contribution:** Trained on 465 real Pixhawk flight logs; median 35m position error (best ~2.7m) over 5-min flights. Practical real-time dead-reckoning without GPS or camera.
- **Relevance:** Pure inertial deep learning baseline; useful if camera fails / occluded

---

### 8. VLocNet++: Deep Multitask Learning for Semantic Visual Localization and Odometry (2018)
- **File:** `1804.08366v6.pdf`
- **ArXiv:** https://arxiv.org/abs/1804.08366
- **Method:** Multitask DNN — semantic segmentation + 6-DoF global pose regression + visual odometry from monocular images
- **Key Contribution:** Adaptive weighted fusion + self-supervised warping; introduces DeepLoc outdoor urban dataset. Outperforms traditional feature-based localization.
- **Relevance:** Multitask learning reference; shows how to combine VO with absolute localization

---

## Map-Matching / Geo-Localization

### 9. Kilometer-Scale GNSS-Denied UAV Navigation via Heightmap Gradients (2025)
- **File:** `2510.01348v1.pdf`
- **ArXiv:** https://arxiv.org/abs/2510.01348
- **Method:** LiDAR heightmap generation + gradient-template matching against reference geodata, fused via particle filter. Runs on CPU only.
- **Key Contribution:** Competition-proven (SPRIN-D Challenge winner) full autonomous UAV nav stack over km-scale distances in urban/forest/open terrain below 25m altitude. Significant drift reduction without loop closures.
- **Relevance:** State-of-the-art practical system; strong motivation for map-matching approaches

---

### 10. Video2BEV: Transforming Drone Videos to BEVs for Video-based Geo-localization (2024)
- **File:** `2411.13610v4.pdf`
- **ArXiv:** https://arxiv.org/abs/2411.13610
- **Method:** Gaussian Splatting for 3D scene → BEV; diffusion-based hard negative generation for metric learning
- **Key Contribution:** Drone video → BEV conversion enables robust cross-platform geo-localization especially at low altitudes with occlusion. Introduces UniV dataset (extends University-1652).
- **Relevance:** Novel geo-localization pipeline; BEV representation is a strong research direction

---

## Map Matching Sub-folder Papers

### 11. Map Matching — ACM GIS (camera-ready)
- **File:** `map matching/map-matching-ACM-GIS-camera-ready.pdf`
- **Relevance:** Classical map-matching algorithm reference

### 12. Map Matching — Pattern Recognition (2024)
- **File:** `map matching/1-s2.0-S0031320324001146-main.pdf`
- **Journal:** Pattern Recognition (Elsevier, 2024)
- **Relevance:** Recent pattern recognition approach to map matching

---

## Quick Research Gap Summary

| Approach | Maturity | Compute | Research Gap |
|---|---|---|---|
| Classical VIO (filter/optimization) | High | Low–Med | Limited robustness in featureless/dynamic environments |
| Learning-based VO (CNN+LSTM) | Med | Med–High | Generalization across environments, real-time on edge |
| Pure inertial RNN | Med | Low | Drift accumulation over long flights |
| Map-matching (LiDAR/heightmap) | Emerging | Med | Requires prior map; works km-scale |
| BEV geo-localization | Novel | High | Low-altitude occlusion, real-time feasibility |
| Multitask (VO + semantic) | Med | High | Edge deployment on boards like RDK X5 |

---

---

## Web-Sourced Papers — Gap Analysis References (2020–2025)

> These are key papers found via web research to validate and precisely locate the research gap.

### Cross-View Geo-Localization — Retrieval (No Likelihood, No Filter)

| Paper | Venue | [A] p(z\|x) | [B] Filter | [C] Calibrated | [D] Embedded |
|---|---|---|---|---|---|
| VIGOR (Zhu et al.) | CVPR 2021 | No | No | No | No |
| HighlyAccurate (Shi et al.) | CVPR 2022 | No | No | No | No |
| Fine-grained Correlation-Aware (Zhu et al.) | NeurIPS 2023 | No | No | No | No |
| PFED-CVGL (Sun et al.) | arXiv 2025 | No (entropy for training only) | No | No | Yes (AGX Orin) |
| CAEVL Self-Supervised (Amadei et al.) | arXiv 2025 | No | No | No | Yes (1.42 GFLOPs) |

### Particle Filter + Satellite Matching for UAV — Key Prior Works

#### Jurevicius et al. (2020) — *Closest UAV baseline*
- **Venue:** Machine Vision and Applications (Springer) | arXiv: 1910.12121
- **Method:** Downward-facing monocular camera matched to georeferenced aerial map. NCC score → particle weight via **hand-crafted logistic/rectifying function**. VO provides motion model.
- **Gap:** Likelihood is heuristic (not learned, not calibrated). No NEES/filter consistency. No deep features. No VIO coupling.
- **[A]** Heuristic only | **[B]** Yes | **[C]** No | **[D]** Partially

#### SWA-PF (Yuan et al., 2025)
- **Venue:** arXiv 2509.13795
- **Method:** Semantic segmentation of UAV + satellite → Semantic-Weighted Distance Map (SWDM) → particle weights. 4-DoF, <10 m error.
- **Gap:** SWDM is geometric proximity score, not probabilistic likelihood. No calibration. Fails in feature-scarce terrain.
- **[A]** No | **[B]** Yes | **[C]** No | **[D]** Partially

#### BEV-Patch-PF (Lee et al., 2025) — *Closest technical analogue*
- **Venue:** arXiv 2512.15111
- **Method:** Ground vehicle BEV from RGB+depth → aerial feature map patch matching → **`p(z|x) ∝ exp(α_σ · cos_sim / τ_s)`** with learned uncertainty σ_t modulating temperature. 9.7× lower ATE vs baselines.
- **Gap:** Ground vehicle + depth camera only. Uncertainty learned but not independently calibrated (NEES not reported). No monocular UAV domain.
- **[A]** Yes (closest) | **[B]** Yes | **[C]** Partial | **[D]** No (Tesla T4)

### Probabilistic Cross-View Matching — Ground Vehicle

#### Fervers et al. (CVPR 2023) — *Closest probabilistic baseline*
- **Venue:** CVPR 2023 | arXiv: 2211.12145
- **Method:** End-to-end differentiable model outputting **3-DoF pose probability distribution** from ground-camera + aerial image pair. Fused with IMU in a Kalman filter. 0.78 m mean error on KITTI-360.
- **Gap:** Forward-facing camera, ground vehicles ONLY. Distribution not formally calibrated as p(z|x). No particle filter (uses Kalman). No filter consistency (NEES) reported.
- **[A]** Partial | **[B]** Kalman (ground only) | **[C]** Partial | **[D]** No

### VIO + Satellite Fusion Frameworks

#### Bianchi & Barfoot (RA-L 2021) — arXiv: 2102.05692
- **Method:** Autoencoder on satellite tiles → kernel-based inner product matching → mean + covariance output. RMSE < 3m, designed for UAV.
- **Gap:** Autoencoder not trained for cross-view domain gap. Covariance empirical (not calibrated). No sequential filter. No VO coupling.
- **[A]** Partial | **[B]** No | **[C]** No | **[D]** Yes

#### Chen et al. (IROS 2021) — arXiv: 2108.03344
- **Method:** Satellite + topography → synthetic rendered database → retrieval on real UAV. Validated on real hardware.
- **Gap:** Pure retrieval, no p(z|x), no filter, requires topographic map.
- **[A]** No | **[B]** No | **[C]** No | **[D]** Yes

#### OPsCV (Xavier et al., JATM 2026)
- **Method:** Deep Inertial Odometry + cross-view geo-localization via ESKF. Dynamic GNSS/vision switching.
- **Gap:** Measurement noise covariance from geo-localization is not calibrated — fed raw without principled uncertainty.
- **[A]** No | **[B]** ESKF only | **[C]** No | **[D]** No

---

## THE CONFIRMED RESEARCH GAP (citable)

**No paper combines all of:**
1. Nadir monocular UAV camera (no depth, no LiDAR)
2. Satellite imagery as reference (not DEM/heightmap)
3. Learned + statistically calibrated likelihood p(z|x) on SE(2)
4. Particle filter integration with this likelihood
5. Monocular VIO as the motion model
6. Filter consistency validation (NEES / chi-squared)
7. Deployment on a resource-constrained board

The closest papers each satisfy 2–3 of these criteria but none satisfies all 7.

---

*Papers collected for MTech final year project — GPS-Denied Navigation Stack for Drones, IIT Madras*
