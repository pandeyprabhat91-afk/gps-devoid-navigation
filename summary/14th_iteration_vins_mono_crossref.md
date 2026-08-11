# 14th Iteration — VINS-Mono Cross-Reference: IMU Error-State Jacobians

**Date:** 2026-08-11
**Scope:** studied VINS-Mono's VIO implementation (HKUST-Aerial-Robotics,
Ceres-based sliding-window factor graph) and ported its error-state
Jacobian structure into the kp_vio C++ ESKF. Recorded the concrete
improvement and the current open regression.

---

## What VINS-Mono does (studied)

Files pulled and read in full:
- `vins_estimator/src/factor/integration_base.h` — IMU preintegration,
  midpoint integration, 15×15 error-state Jacobian F, 15×18 noise matrix V
- `vins_estimator/src/factor/imu_factor.h` — the IMU factor residual
  (15-DoF: δp, δθ, δv, δba, δbg) with bias re-linearisation
- `vins_estimator/src/initial/initial_aligment.cpp` — gyro-bias init by
  least squares, gravity+scale+velocity linear alignment, gravity
  refinement on a tangent-plane basis
- `vins_estimator/src/parameters.cpp` — ACC_N/GYR_N (measurement noise)
  and ACC_W/GYR_W (bias random walk) as first-class config

Key architectural facts:
1. **15-DoF error state** [δp, δθ, δv, δba, δbg] — the rotation is a
   parameter, never a 4-vector in the state. (kp_vio's 16-state stores
   the quaternion at [6..9]; its Jacobians must therefore use the 3-DoF
   rotation-error map, which the 13th iteration began.)
2. **IMU preintegration in the body frame**, gravity added analytically
   in the residual (`0.5·G·Δt²`), never inside the integration.
3. **Complete first-order F matrix** with the cross-couplings the 13th
   iteration had not yet ported:
   - `∂v/∂θ = -[a_world]×·dt` (attitude error leaks into velocity via
     the REAL world-frame acceleration)
   - `∂p/∂θ = -0.5·[a_world]×·dt²`
   - `∂p/∂ba = -0.5·R·dt²`
   - `∂θ/∂θ = I - [ω_world]×·dt` (the gyro rotation appears in the
     attitude-error transition)
   - `∂θ/∂bg = -R·dt`
4. **Bias re-linearisation**: `repropagate()` re-integrates the IMU
   buffer when the bias estimate moves beyond a threshold
   (BIAS_ACC_THRESHOLD = 0.1, BIAS_GYR_THRESHOLD = 0.1) — the
   first-estimates-Jacobian principle for preintegration.

---

## What was wrong in kp_vio (found by the cross-reference)

The 13th-iteration `propagate()` had two residual Jacobian defects
that the VINS structure exposed:

| Block | kp_vio (13th) | VINS-Mono | Effect |
|---|---|---|---|
| `∂v/∂θ` | `-R_bw·[dv_body]×·dt` (body skew, extra dt) | `-[a_world]×·dt` | velocity over-trusted between fixes |
| `∂p/∂θ` | **missing** | `-0.5·[a_world]×·dt²` | attitude error not propagated into position |
| `∂p/∂ba` | **missing** | `-0.5·R_bw·dt²` | accel-bias error not propagated into position |
| `∂θ/∂θ` | `I` | `I - [ω_world]×·dt` | gyro rotation missing from attitude transition |
| Q position noise | 0 | `0.25·σ_a²·dt⁴` | position process noise absent |

The under-coupling meant the filter believed its velocity more than the
physics allows. Between sparse map fixes, the velocity error grew
unchecked, and the filter could not reconcile the fixes with its
prediction — the observed divergence.

---

## The fix (applied to `ekf_core.cpp::propagate`)

Ported the VINS error-state transition, adapted to the 16-state layout:

```
δṗ  = δv
δv̇  = -[a_w]×·δθ - R_bw·δba
δθ̇  = -[ω_w]×·δθ - R_bw·δbg
δbġ = 0, δbȧ = 0

F(0,3)  = I·dt              p ← v
F(0,6)  = -0.5·[a_w]×·dt²   p ← δθ      (NEW)
F(0,13) = -0.5·R_bw·dt²     p ← ba      (NEW)
F(3,6)  = -[a_w]×·dt        v ← δθ      (CORRECTED)
F(3,13) = -R_bw·dt          v ← ba
F(6,6)  = I - [ω_w]×·dt     δθ ← δθ     (CORRECTED)
F(6,10) = -R_bw·dt          δθ ← bg
```

Q gained the position process noise `0.25·σ_a²·dt⁴·I`.

`a_w` and `ω_w` are recovered from the ImuDelta (body-frame dv and dR),
so the change is confined to `propagate()` — no API change.

---

## Measured effect (real 43 km Bhopal flight, GPS truth)

| Config | Before (13th) | After (VINS structure) |
|---|---|---|
| **5 s / σ=15 m fixes** | mean **20,349 m** (diverged at the 4.7 m/s² bias spike) | mean **54 m**, p50 **16.5 m**, p90 **85 m**, final **9.3 m** |
| 30 s stationary | 0.01 m | 0.01 m (unchanged, physics still correct) |
| 1 Hz / σ=5 m | 53 m | **NaN (regression — open)** |
| 1 Hz / σ=15 m | 500 m | **NaN (regression — open)** |

**The headline improvement:** the sparse-fix case (5 s interval) went
from catastrophic divergence to a working 54 m / p50 16.5 m — exactly
the regime where the 4.7 m/s² late-flight accel-bias spike previously
overwhelmed the filter. The honest Jacobians now let the filter weigh
the fixes correctly.

**The open regression:** at 1 Hz (dense fixes), the state covariance
goes non-positive-definite (NaN). The dense measurement stream
interacts with the new couplings in a way the 13th-iteration P-shrink
heuristics (gravity-attitude and yaw updates) do not tolerate. This is
the next item to fix — likely by replacing the hand-rolled P-shrinks
with a proper 3-DoF error-state update for gravity and yaw, or by
adding a P-symmetry/PSD projection after updates.

---

## Honest status

- Structural improvement: real and measured (5 s case fixed).
- Regression: real, unfixed (1 Hz NaN). The estimator is NOT yet
  production-ready; the dense-fix path must be repaired before the RDK
  X5 flight.
- The VINS gyro-bias init (`solveGyroscopeBias`) and gravity/scale
  linear alignment are documented but NOT yet ported — they require the
  preintegration buffer architecture, which kp_vio's per-sample EKF
  does not use. Recorded as future work, not silently adopted.

---

*All VINS-Mono reference files retained at
`C:\Users\lonew\AppData\Local\Temp\opencode\vins_*.{h,cpp}` for
audit trail. kp_vio changes: `src/estimator/ekf_core.cpp::propagate`.*
