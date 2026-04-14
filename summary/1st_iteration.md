# GPS-Denied UAV Navigation — 1st Iteration Design Document

**Project:** MTech Final Year Project, IIT Madras
**Date:** 2026-03-27
**Status:** Brainstorming / Pre-implementation

---

## 1. Project Overview

The goal is to design and implement a GPS-denied navigation stack for drones, with two parallel deliverables:

1. **Research Paper** — Novel algorithmic contribution publishable at ICRA / IROS / RA-L level
2. **Hardware Prototype** — Working navigation stack on an RDK X5 class embedded board

The research paper and prototype are coupled: the prototype's real flight data serves as the paper's experimental validation platform.

---

## 2. Sensor Suite

| Sensor | Role | Rate |
|--------|------|------|
| Monocular Camera | Visual odometry + geo-localization | 25–30 Hz |
| IMU (6-axis) | Angular velocity + linear acceleration | 100–200 Hz |
| Barometer | Altitude estimation | 25–50 Hz |
| Magnetometer | Heading prior | 10–25 Hz |
| RDK X5 BPU | Neural network inference (decision deferred) | — |

Hardware baseline: **Pixhawk flight controller** (IMU + baro + mag) paired with **RDK X5** companion computer.

---

## 3. Research Contribution — Precisely Stated

> **"Learning a Statistically Calibrated Measurement Likelihood p(z|x) for Monocular-Satellite Fused Particle Filter Navigation on GPS-Denied UAVs"**

### 3.1 The Core Problem

All existing geo-localization papers treat satellite image matching as a retrieval problem:

```
x_hat = argmax_x  sim(f_drone(I_drone), f_sat(I_sat(x)))
```

This gives a **single point estimate** with no uncertainty. A navigation filter requires:

```
p(z | x)  — the full likelihood of observing drone embedding z
             given true 2D position x on the satellite map
```

**No existing paper formulates, trains, or validates this function for nadir UAV + satellite imagery.** This is the confirmed research gap.

### 3.2 Confirmed Gap — Literature Evidence

| Paper | Venue | UAV nadir | p(z\|x) | Particle Filter | NEES validated | Embedded |
|-------|-------|-----------|---------|-----------------|----------------|----------|
| Jurevicius et al. 2020 | MVA | Yes | Heuristic (logistic fn) | Yes | No | Partial |
| BEV-Patch-PF 2025 | arXiv | No (ground vehicle) | Yes (learned) | Yes | No | No (Tesla T4) |
| Fervers et al. 2023 | CVPR | No (ground vehicle) | Partial | Kalman only | No | No |
| SWA-PF 2025 | arXiv | Yes | No (geometric score) | Yes | No | Partial |
| Bianchi & Barfoot 2021 | RA-L | Yes | Partial (covariance) | No | No | Yes |
| **This thesis** | ICRA/IROS target | **Yes** | **Yes (learned + calibrated)** | **Yes** | **Yes** | **Yes (RDK X5)** |

**The confirmed gap (7 criteria, no prior paper satisfies all):**
1. Nadir monocular UAV camera (no depth, no LiDAR)
2. Satellite imagery as reference (not DEM/heightmap)
3. Learned + statistically calibrated likelihood p(z|x) on SE(2)
4. Particle filter integration with this likelihood
5. Monocular VIO as the motion model
6. Filter consistency validation (NEES / chi-squared)
7. Deployment on a resource-constrained board

---

## 4. System Architecture

### 4.1 State Decomposition

The full navigation state is:

```
X = (R, P, V) in SE_2(3) = SO(3) x R^3 x R^3
```

Decomposed into two coupled estimators:

```
HIGH-RATE  (100 Hz): UKF on S^3 x R^3 x R^3
  -> Quaternion-based UKF (QNUKF, following 2412.02768)
  -> Fuses: IMU preintegration + barometer + monocular VO
  -> Output: full 9-DoF pose + covariance Sigma_UKF

LOW-RATE (0.5-2 Hz): Particle Filter on SE(2)
  -> State: x_2D = (px, py, psi) — horizontal position + heading
  -> Motion model: VO delta pose from UKF
  -> Measurement: satellite image likelihood p(z_sat | x_2D)
  -> Output: corrected 2D position, fed back to UKF
```

### 4.2 Block Diagram

```
IMU (100 Hz) ──► Preintegration ──────────────────────► QNUKF
Barometer    ──► Altitude obs.  ──────────────────────►  on S^3 x R^3 x R^3
Monocular VO ──► SelfAttentionVO ─► delta_P (relative) ─► motion model
Magnetometer ──► Heading prior  ──────────────────────► for Particle Filter

Satellite tiles (cached offline) ──┐
                                   ├──► L_theta(z_drone, x_2D) ──► Particle weights
Drone image   (0.5–2 Hz) ─────────┘       (measurement likelihood)
                                                    │
                                                    ▼
                                        SE(2) position estimate
                                        (drift-corrected global position)
```

---

## 5. The Likelihood Network L_theta — Core Algorithm

### 5.1 Architecture

```
Input:   I_drone  (drone camera frame, 224x224 RGB)
         I_sat(x) (satellite tile crop at candidate position x)

Step 1:  z_drone = f_enc(I_drone)      # shared CNN encoder (cross-view trained)
         z_sat   = f_enc(I_sat(x))     # same encoder

Step 2:  s = cosine_similarity(z_drone, z_sat)   # in [-1, 1]

Step 3:  tau = g_theta(z_drone)        # scene-adaptive temperature MLP
                                       # high tau -> flat distribution (ambiguous)
                                       # low tau  -> sharp distribution (distinctive)

Step 4:  p(z | x) ∝ exp(s / tau)      # particle weight update
```

### 5.2 Training Loss

```
L_total = L_InfoNCE + lambda_1 * L_calibration + lambda_2 * L_NEES

L_InfoNCE    = -log [ exp(s_pos/tau) / sum_j exp(s_j/tau) ]
               (standard contrastive: correct tile vs. mined negatives)

L_calibration = ECE(predicted_likelihood, empirical_match_rate)
               (Expected Calibration Error — forces statistical validity)

L_NEES       = E[ ||x_true - x_hat_PF||^2_{Sigma^{-1}} ]  ≈ dim(x) = 3
               (Normalized Estimation Error Squared — filter consistency)
               (back-propagated through particle filter)
```

The **L_NEES term is the key novelty**: it ties the learned likelihood directly to navigation filter consistency, which no prior paper does.

### 5.3 Why This Is Novel

| Component | Prior art | This work |
|-----------|-----------|-----------|
| Retrieval backbone | InfoNCE / contrastive | Same, but with calibration loss |
| Uncertainty output | None / fixed sigma | Scene-adaptive tau (learned MLP) |
| Filter consistency | Not addressed | L_NEES in training loss |
| Domain | Ground vehicle / stereo | Nadir UAV monocular |
| Validation | Recall@K only | NEES + ATE + RTE |

---

## 6. Mathematical Formulation

### 6.1 Particle Filter State

```
Particles: {(x_i, w_i)}_{i=1}^N,   x_i = (px_i, py_i, psi_i) in SE(2)

Motion update (from VIO):
  x_i^t = x_i^{t-1} + f(delta_P_VO, delta_psi_VO) + epsilon_i
  epsilon_i ~ N(0, Sigma_VO)   (Sigma_VO from UKF output — NOT hand-tuned)

Measurement update (from satellite matching at rate 0.5-2 Hz):
  w_i^t  ∝  w_i^{t-1} * p(z_sat | x_i^t)
  w_i^t  =  w_i^{t-1} * exp( cos_sim(z_drone, z_sat(x_i)) / tau(z_drone) )

Normalization:  w_i = w_i / sum_j w_j

Resampling: Systematic resampling when N_eff = 1/sum(w_i^2) < N/2
```

### 6.2 Filter Consistency (NEES)

The filter is consistent if, for each time step t:

```
NEES_t = (x_true - x_hat)^T * P_t^{-1} * (x_true - x_hat) ~ chi^2(dim_x)

Expected value: E[NEES_t] = dim(x) = 3
Acceptable range (95% confidence): [chi^2_{0.025}(3), chi^2_{0.975}(3)] = [0.216, 9.35]
```

If NEES >> 3: filter is overconfident (likelihood too sharp, tau too low)
If NEES << 3: filter is underconfident (likelihood too flat, tau too high)

Training L_NEES pushes NEES toward 3, producing a calibrated, consistent filter.

---

## 7. Datasets and Evaluation

### 7.1 Training Datasets
- **University-1652 / UniV** — drone-view + satellite pairs, 1652 locations
- **SUES-200** — UAV geo-localization, multiple altitudes (54m–162m)
- **IIT Madras campus** — self-collected flights (ground truth from RTK GPS)

### 7.2 Evaluation Metrics

| Metric | Measures | Target |
|--------|----------|--------|
| Recall@1, @5, @10 | Retrieval accuracy of geo-localization module | > 85% R@1 |
| ATE (m) | Absolute Trajectory Error over full flight | < 10 m (campus) |
| RTE (m) | Relative Trajectory Error per 100 m | < 5% of distance |
| NEES | Filter consistency | 2.5–3.5 (chi^2(3) range) |
| ECE | Expected Calibration Error of likelihood | < 0.05 |
| Inference latency | Per-frame on RDK X5 | < 100 ms |

### 7.3 Ablation Studies
1. Heuristic likelihood (logistic fn, Jurevicius baseline) vs. learned p(z|x)
2. Fixed temperature tau vs. scene-adaptive tau
3. Without L_NEES loss vs. with L_NEES loss
4. VO-only (no satellite correction) vs. full system
5. PF particle count: N=100 vs. N=500 vs. N=1000 (latency vs. accuracy)

---

## 8. Hardware Stack

| Layer | Component | Role |
|-------|-----------|------|
| Flight controller | Pixhawk (PX4) | IMU, baro, mag, motor control |
| Companion computer | RDK X5 | All navigation computation |
| Camera | 1080p global shutter monocular | VO + geo-localization |
| BPU decision | TBD after profiling | CNN encoder may run on BPU |
| Satellite tiles | Cached on SD card (offline) | ~5 km x 5 km at 0.3 m/px |
| Communication | MAVLink (Pixhawk ↔ RDK X5) | Sensor data + control |

---

## 9. Implementation Roadmap

### Phase 1 — Literature & Gap Finalization (Weeks 1–4)
- Read 10–15 additional papers from citation chains of key papers
- Build final gap matrix
- Finalize research question and title

### Phase 2 — Algorithm Prototyping (Weeks 5–10)
- Implement baseline: SelfAttentionVO for monocular VO
- Implement particle filter on SE(2) with heuristic likelihood (replicate Jurevicius)
- Train cross-view encoder on University-1652 / SUES-200
- Implement scene-adaptive temperature network g_theta
- Add L_calibration + L_NEES to training pipeline

### Phase 3 — Hardware Integration (Weeks 8–14)
- Set up RDK X5 + Pixhawk + camera
- Port encoder and particle filter to RDK X5
- Collect IIT Madras campus flight data with RTK GPS ground truth
- Run full system evaluation

### Phase 4 — Paper Writing (Weeks 12–16)
- Ablation experiments (Section 7.3)
- NEES and calibration plots
- Compare against all 5 baselines in gap table
- Submit to ICRA 2027 (deadline typically September 2026)

---

## 10. Key References

### In-hand Papers (PDF available)
1. 2307.11758 — VIN comprehensive intro (factor graphs, IMU dynamics)
2. 2104.09920 — SE_2(3) nonlinear stochastic observer (formal guarantees)
3. 2412.02768 — QNUKF on S^3 x R^3 x R^3 (UKF baseline for fusion)
4. 2404.17745 — SelfAttentionVO (VO module baseline)
5. 2109.04861 — RNN GPS-denied (pure inertial baseline)
6. 2211.11988 — Vision-based localization survey
7. 2510.01348 — SPRIN-D winner (heightmap + particle filter, closest system)
8. 2411.13610 — Video2BEV (geo-localization with BEV transformation)
9. 1804.08366 — VLocNet++ (multitask VO + global pose)
10. 1906.03289 — Aerial VIO survey (Scaramuzza)

### Web-Sourced Key Papers (Must Obtain)
11. Jurevicius 2020 (arXiv 1910.12121) — UAV+satellite+PF with heuristic likelihood **[direct baseline]**
12. BEV-Patch-PF 2025 (arXiv 2512.15111) — p(z|x) for ground vehicle PF **[closest technical analogue]**
13. Fervers CVPR 2023 (arXiv 2211.12145) — probabilistic cross-view, ground vehicle **[closest probabilistic baseline]**
14. Bianchi RA-L 2021 (arXiv 2102.05692) — UAV + autoencoded satellite + covariance
15. SWA-PF 2025 (arXiv 2509.13795) — UAV semantic PF **[direct competitor]**
16. Chen IROS 2021 (arXiv 2108.03344) — satellite+topography, real UAV validation

---

## 11. Open Questions / Decisions Pending

1. **BPU vs CPU for encoder:** Profile CNN encoder (ResNet18/EfficientNet) on RDK X5 BPU vs CPU. If BPU gives >3x speedup, quantize and deploy there; else CPU.
2. **Satellite tile resolution:** 0.3 m/px (Google Earth level) vs. 0.5 m/px (OpenStreetMap). Higher resolution = larger tiles = more memory. Decide after profiling.
3. **VO scale recovery:** Monocular VO has scale ambiguity. Options: (a) use barometric altitude as metric scale anchor; (b) use known drone body size as scale reference; (c) accept relative scale and rely on satellite matching for metric correction.
4. **Particle count N:** Trade-off between accuracy and latency on RDK X5. Target: real-time at 2 Hz update rate.
5. **Training dataset for IIT Madras domain:** Public datasets (University-1652, SUES-200) are mostly Western university campuses. Domain gap to IIT Madras campus may require fine-tuning. Explore sim-to-real via Google Earth rendering.

---

*Document generated: 2026-03-27 | Version: 1st Iteration | Next: Literature gap matrix + spec doc*
