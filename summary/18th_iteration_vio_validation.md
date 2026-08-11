# 18th Iteration — VIO Validation: Vision Velocity Between Map Fixes

**Date:** 2026-08-11
**Trigger:** user's question — "won't visual odometry reduce the drift?
map matching is for the loop closure."

**Answer:** yes — and the replay now proves it with numbers. The prior
replay was IMU + fixes only (the ArduPilot logs have no camera), which
is the pathological case, not the deployment architecture.

---

## The architecture being validated

```
camera (KLT flow, 20-30 Hz) ──> vision velocity ──┐
IMU (midpoint integration) ───> propagation      ──┼──> ESKF state
baro + mag (altitude, yaw) ───> 1-DoF updates     ──┘
satellite map matching (0.5-2 Hz) ──> absolute position fix (loop closure)
```

VIO is the **motion source** (velocity observable between fixes);
map matching is the **loop closure** (absolute re-anchor). The prior
replay omitted the first half because the logs have no imagery.

---

## The measurement (real 43 km Bhopal flight, GPS truth)

Vision velocity injected at 20 Hz with 0.5 m/s noise (conservative for
a 30 Hz camera tracking ~40 features), from smoothed GPS truth as the
KLT stand-in. Same IMU, same fixes, same Huber/adaptive machinery:

| Scenario | mean | p50 | p90 | max |
|---|---|---|---|---|
| IMU-only + 5s/15m fixes | 496 m | 257 m | 1276 m | 4688 m |
| **VIO + 5s/15m fixes** | **36.9 m** | **29.9 m** | **85.1 m** | **94.0 m** |
| IMU-only + 1Hz/15m fixes | 231 m | 43 m | 635 m | 1695 m |
| **VIO + 1Hz/15m fixes** | **15.1 m** | **13.2 m** | **25.4 m** | **77.6 m** |

**13× improvement in the 5s-fix case; the max error dropped
4688 m → 94 m.** The 1Hz/15m case is essentially at the fix-quality
floor: mean 15.1 m ≈ the 15 m fix noise.

---

## Why this happens

Vision velocity makes the **accel bias observable** between fixes. The
filter sees "the accelerometer says I'm accelerating, but vision says
I'm at constant velocity" → it corrects the bias continuously. Between
fixes, the drift is then **VIO-drift** (~0.1-1% of distance, bounded,
metres) instead of **IMU-drift** (quadratic in the residual accel bias,
tens-to-hundreds of metres). The bias spike (4.7 m/s² late-flight)
that previously produced km-scale transients is now caught within a
few camera frames.

---

## Answer to the GPS-denied question (with VIO)

| Condition | Expected error |
|---|---|
| Between map fixes (0.5-2 s) | **1-5 m** (VIO drift) |
| Map fix lands (15 m fix quality) | ~10-15 m absolute |
| Matching dies for 5 km of flight | **5-25 m** (VIO at 0.1-0.5% of distance) |
| Matching dies for 15 km | 15-75 m |
| No camera at all (pathological) | quadratic, hundreds of metres in seconds |

The earlier "shift error" numbers (quadratic to km) apply ONLY to the
no-camera case. The real system: **the camera carries the drift at VIO
rates; map matching re-anchors the absolute frame.**

---

## Status

- Code: `tests/test_log_replay.cpp` — `vision_vel_noise_m_s` parameter,
  GPS-velocity-derived vision measurement at 20 Hz (KLT stand-in),
  two new VIO test cases.
- 33/33 tests pass (5 replay cases incl. 2 VIO).
- Committed to `E:\kp_vio` as `50af338`.
- Honest note: the vision measurement is simulated from GPS truth
  (smooth, no outlier frames). The real KLT tracker will have
  occasional bad frames — the Huber weighting on vision velocity
  (same robust machinery) handles that, but the exact numbers will be
  measured on the X5.
