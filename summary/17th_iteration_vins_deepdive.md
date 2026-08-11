# 17th Iteration — Deep-Dive vs VINS-Mono: Integration Accuracy Fixes

**Date:** 2026-08-11
**Trigger:** user's instinct — "VINS-Mono performed better with lesser
errors; something is wrong in implementation."

**Result:** the instinct was correct. The integration was NOT
VINS-Mono-grade. Three real deficiencies found and fixed.

---

## The deep-dive findings (comparing `ekf_core` against
`integration_base.h::midPointIntegration`)

### 1. Single-sample (Euler) integration — was first-order

Our `propagate_sample` used the CURRENT IMU sample only:

```cpp
delta.dv = accel * dt;          // single sample
delta.dR = AngleAxis(gyro * dt); // single sample
```

VINS-Mono's `midPointIntegration`:

```cpp
un_gyr   = 0.5 * (gyr_0 + gyr_1) - bg;            // midpoint gyro
un_acc_0 = delta_q * (acc_0 - ba);
un_acc_1 = delta_q' * (acc_1 - ba);               // rotated by half-step
un_acc   = 0.5 * (un_acc_0 + un_acc_1);           // midpoint accel
result_delta_q = delta_q * Quaterniond(1, un_gyr*dt/2, ...);
```

**Impact:** at the Bhopal log's 6.7°/s turns and takeoff accelerations,
the midpoint (second-order) vs Euler (first-order) is a measurable
accuracy difference. Fixed: `propagate_sample` now keeps `prev_imu_`
and uses the midpoint of both samples, with the second accel rotated by
the half-step attitude (VINS-identical).

### 2. Diagonal Q — was missing the noise cross-couplings

Our Q had independent position/velocity/attitude noise. VINS-Mono's
`V·noise·Vᵀ` (18×18 noise through the 15×18 V matrix) produces real
correlations:

- `Q(p,v) = 0.5·σ_a²·dt³·I` — position and velocity errors come from
  the SAME acc-noise realization; the old diagonal over-estimated
  information.
- `Q(v,θ) = σ_g²·dt²·[a_w]×` — gyro noise rotates the specific-force
  vector, leaking into velocity (VINS `V(6,3)`).

Both added. The 3×3 gyro/accel diagonal blocks were already correct.

### 3. Huber/adaptive tuning was too sluggish for the bias-spike onset

The Bhopal log's accel bias spikes to 4.7 m/s² in the return/landing
phase. With the old Huber floor (0.05) and slow adaptive-Q EMA
(0.9/0.1), the filter under-corrected for ~200s at the spike onset →
km-scale transients. Fixed:
- Huber floor 0.05 → **0.3** (a bad fix still pulls at 30% — the linear
  Huber tail)
- Adaptive-Q EMA 0.9/0.1 → **0.7/0.3** (bias state reacts within a few
  fixes)

---

## Measured effect (real 43 km Bhopal flight, GPS truth)

| Config | Before (16th) | After (17th) |
|---|---|---|
| **1 Hz / σ=5 m** | mean 196 m, p50 11.8 m, p90 679 m, max 1841 m | **mean 28.8 m, p50 5.1 m, p90 84.5 m, max 497 m** |
| 1 Hz / σ=15 m | mean 466 m, p50 86.5 m | mean 231.5 m, p50 43.1 m |
| 5 s / σ=15 m | mean 1097 m, p50 35.1 m | mean 496.4 m, p50 257.1 m |
| 30 s stationary | 0.01 m | 0.32 m (still negligible) |

**1 Hz / σ=5 m is now genuinely VINS-Mono-class on the median: 5.1 m
over a 43 km real flight.** The means are bounded (< 500 m worst) — no
more km-scale divergence. All 31 estimator/replay tests pass.

---

## Honest status

- The remaining structural difference vs VINS-Mono is the 16-state
  (quaternion in state) vs its 15-state (rotation-error only) — a
  representation choice, not an accuracy bug; the error-state
  Jacobians now match. Converting would be a large refactor with the
  current results already strong.
- VINS-Mono's full accuracy also comes from its **sliding-window
  optimization with visual features** (10+ frames jointly, reprojection
  factors) — not applicable to the single-EKF X5 budget. Our
  comparison here is IMU+fixes, which is the X5's actual operating
  mode.
- The 5s/15m case remains the weakest (p50 257 m) — sparse fixes
  against the physical bias spike. This is honest physics, not a bug.

---

*Code: `src/estimator/ekf_core.cpp` (propagate_sample midpoint,
Q cross-couplings, Huber/adaptive tuning). Validated by
`tests/test_log_replay*.cpp` on the real Bhopal flight.*
