# ArduPilot Log Assessment — VIO & Map-Matching Feasibility

**Date:** 2026-08-10
**Source:** 3 .bin files found in project root (2 unique flights, 1 duplicate)
**Purpose:** practical, realistic, no-assumptions test of the pipeline against
real Indian-terrain flight data.

---

## The logs

| Flight | Location (India) | Flown distance | Max radius | Altitude | Duration |
|---|---|---|---|---|---|
| `00000061.BIN` / `Logsdrone.BIN` (duplicates) | Jhansi, UP (25.19N, 78.36E) | 15.3 km | 5.5 km | 296–808 m | 1580 s |
| `2026-06-29 17-05-31.bin` | Bhopal, MP (23.79N, 78.80E) | **43.0 km** | 20.1 km | 533–835 m | 3160 s |

Both: 100% GPS status-4 (3D fix), HDop 0.50–0.56 (≈1–2 m accuracy), 25 Hz IMU
logging, baro, mag, EKF state (XKF1/XKQ), vibration.

**Confirmed ArduPilot DataFlash logs** (magic `a3 95 80`, FMT messages).

---

## Findings

### 1. GPS ground truth quality — EXCELLENT

- HDop 0.50 median → **1–2 m truth**, far better than UAV-VisLoc's ~10 m GPS.
- The ArduPilot EKF tracks GPS to **1.4 m mean (Bhopal), 4.4 m (Jhansi)**.
- Verdict: these logs are a valid ground-truth source for testing position
  accuracy at the level this thesis needs.

### 2. Camera-less IMU integration is NOT a VIO test — measured, not assumed

| Attempt | Result |
|---|---|
| Pure double integration (gyro attitude) | quadratic divergence (km-scale) |
| + stationary bias compensation | still diverges (~0.5 m/s² residual) |
| + ArduPilot calibration chain (INS_ACCOFFS/SCAL + AHRS_TRIM) | residual 3–4 m/s² in cruise |
| Mahony (gyro + gravity-gated accel) | still diverges (yaw initialization) |
| Convention verification (Wahba + XKQ) | physics verified correct to ~5° |

**The verified physics:** attitude convention (body↔world, R.T), gravity model
(NED +9.81), accel calibration chain, Mahony structure — all confirmed
correct. The residual error is a **time-varying attitude/accel mismatch**
(~5° from the logged calibration chain) plus vibration of 24–34 m/s² RMS.

**Why this is the correct and expected result:** a camera-less IMU has no
constraint on attitude drift or velocity bias. The whole point of VIO is that
the **camera provides exactly this constraint** (visual features fix attitude
and scale). These logs have NO camera — so the quadratic divergence is the
honest measurement of "IMU-only", which is the reason VIO exists, not a
pipeline bug.

### 3. What the logs ARE good for

1. **GPS truth** (1–2 m) — better than any dataset the project has used.
2. **IMU bias statistics** — real accelerometer bias measured: 0.11–0.48 m/s²
   (Jhansi), demonstrating why bias estimation is mandatory.
3. **Calibration chain** — the logs self-document INS_ACCOFFS/SCAL, AHRS_TRIM
   (pitch −2.84°, roll −3.37°), INS_ACC_BODYFIX — exactly the "drone is
   tilted for forward flight and wind compensation" physics.
4. **Terrain matchability** — Bhopal corridor tiles pulled and probed:
   **edge=125.8 (flat-class), furrow=28.9 (low alias), self-similarity 0.001
   (distinct tiles)** → predicted R03-class map-match behavior (~85% match
   potential) on real Indian terrain.

---

## Honest verdict

- **VIO accuracy on these logs: cannot be measured without a camera.** The
  realistic VIO number must come from the RDK X5 with camera+IMU fused —
  which is exactly the system this thesis builds. Attempting to extract a
  "VIO number" from IMU-only logs would be fabrication.
- **Map matching: the Bhopal corridor is matchable terrain.** The tiles are
  on disk; the GPS track (1–2 m truth) is the ground-truth the ratio gate and
  position recovery can be validated against **if/when drone images over the
  corridor exist** (the logs' own camera was not connected).
- The next honest step remains: **first RDK X5 flight** (camera + IMU), where
  VIO + map matching can be measured together against GPS truth.

---

*All scripts committed: `scripts/vio_log_test.py`, `assess_ardupilot_logs.py`,
8 debug scripts, tile downloader + matchability probe. Data:
`datasets/india_proxy/tiles_bhopal_flight.sqlite` (960 tiles).*
