# 26th Iteration — Void-Closure Campaign (2026-09-06)

**Trigger:** audit of iterations 1–25 found 5 load-bearing voids + status unknowns.
**Mode:** autonomous loops, pre-registered bars, one change per iteration. All
artifacts in `E:\kp_vio\kp_vio_py\results\void_*.json`.

## A2 — C++ suite: "flakiness" was a real bug, fixed (63/63 green)

Full suite failed 8/63 identically to the 21st session. Bisection isolated the
poison to the `Logger.*` suite: `Logger::close()` called global
`spdlog::shutdown()`, destroying the process-global registry; every later
spdlog user crashed (SEH) or misbehaved. Fix in
`final_cpp_implementation/src/logging/logger.cpp`: close() now flushes and
releases only its own logger, drops stale `"kp_vio"`/`"events"` names on
reopen, never shuts down the registry. Full suite: **63/63 pass**.
Side measurement: `LogReplay.Bhopal_VIO_1Hz_15m` = mean 12.5 m / p50 9.2 m,
consistent with the 18th-iteration ~13–15 m row (source: C++ ESKF VIO arm).

## A3 — min-inliers 12 tested at scale, rejected (prod 10 keeps crown)

Probe (n=10, R03+R04) uninformative: every accepted match had ≥18 inliers, so
the threshold never bound — byte-identical results 8/10/12/15. Full sweep
(n=40, 6 regions, drift 300, prod config): mi10 → match 25.4%, CEP50 24.1 m,
CEP90 56.8 m, fatal50 16.4%, yield 21.2%; mi12 → 24.2%, 22.7 m, 58.7 m,
17.2%, 20.0%. Bar (fatal lower AND yield within −20%) failed on both counts.
**Adopt: nothing. Void 5 closed.** (This run had the prior-ratio gate off,
hence fatter fatal than the 11th-iteration gated numbers — config, not regression.)

## B1 — R8 fusion curve re-proven as a bound (void 2 closed)

Error-process fusion (IVW mean, w=inliers) on paper fix pools R03+R04+R06,
d150/300/600. Pooled d300: CEP50 21.8→**8.0 m** (k=1→k=10), fatal50
0.157→**0.048**. R03: 13.9→5.1 m. R04: 30.8→8.8 m. R8's qualitative claim
(≈32→9 m) reproduces post-leak at 21.8→8.0 m. Nuance: R06 is non-monotone
(k3/k5 worse than k1, k10 recovers) — coherent-alias contamination, Finding U
in fusion form. Assumption-explicit: truth removed per frame, so this bounds
extractable signal; a navigation filter needs odometry for motion (deployment
has it at video rate). Artifact: `results/void_b1_fusion_reproof.json`.

## B3 — prior-ratio operating curve (void 3 partial)

Thresholds {1.0,1.5,2.0,3.0} × uncertainty {oracle, honest RMS, RMS×3, RMS×5},
pools R03/R04/R06 × d150/300/600. R06 oracle: perfect at 1.5–2.0 (d150/d300),
degrades at d600. Honest RMS works at d150 (frej 1.00, gkeep 0.94 @1.5) but
collapses by d300 (frej 0.14). At RMS×3/×5 the gate passes everything.
**Two results:** (1) operating point thr 1.5–2.0, effectiveness = U
calibration not threshold — deployment VIO covariance (metres, 30 Hz) vs
258 m alias offsets satisfies it with margin; (2) fail-open property:
miscalibrated U degrades to no-gate, never eats goods (R03/R04 gkeep 1.00 at
thr≥1.5 under all scalings). R04 immune at every setting — verdict reconfirmed.
Full closure needs flight covariance. Artifact: `results/void_b3_ratio_curve.json`.
(R06 oracle gate also re-ran green: 7/7 + 14/14 at both 1.5 and 2.0.)

## B2 — Bhopal replay with real matcher statistics (void 1 partial)

40 track points, query = tile crop at GPS truth, 3×3 candidates around 300 m
drifted prior, ORB+affine RANSAC, min_inliers=10 gate. Result: 40/40 fixes,
|err| med 0.9 m, max 1.8 m, inliers med 340 — tile-vs-tile self-matching is
near-trivially easy. Labelled optimistic bound: perspective gap, vintage gap
and retrieval carry essentially ALL real difficulty. Honest-script replication
byte-exact (gauss15 F=1s = 215.7 m mean — matches stored artifact, no copy bug).
Kalman arms F=1s: gauss15 215.7 m (!), emp_fixedR **10.6 m**, emp_adaptiveR
66.6 m. Three conclusions: (a) the weak 2D-KF diverges where the C++ ESKF
holds 12.5 m — estimator machinery (bias tracking/Huber/VIO) carries ~17×;
(b) with near-perfect fixes even the weak filter holds 10 m; (c) prod
adaptive-R overstates noise ~40× on easy matches (regime-calibrated, safe
direction: conservative). Deployment truth lies between σ15-Gaussian
(pessimistic) and tile-matched (optimistic) arms. Full closure needs flight
(real perspective views). Artifact: `results/void_b2_bhopal_empirical.json`.

## C1 — R03 floor upgraded hypothesis→supported (void 4 partial)

Matcher-independence from Action-6 pools (d300): R03 median ORB-only 11.4 m,
SIFT-only 11.7 m, LightGlue 15.0 m (n=9, underpowered) vs prod 13.9 m. Two
classical matchers agree ≈11.5 m → floor is not matcher-side. Matched-modal
control: Xian05 farmland p50 8.6 m < R03 11–14 m → floor not
farmland-physics either. Remaining suspect: UAV-VisLoc GPS/vintage side.
RTK reflight of one R03-like field (first X5 flight target) is the closer.

## Relabels (wording fixes, history untouched)

- 5th-iteration e2e ("full architecture", synthetic IMU @7 s spacing):
  measures filter+matcher only — VIO untestable at 7 s frame gaps.
- coop 2.26 m/318 s uses bag VINS velocity (strong reference), not onboard
  KLT: deployment upper bound, not expected value.
- 18th-iteration "~13–15 m" row: source is the C++ ESKF VIO arm
  (re-measured 12.5 m mean / 9.2 m p50), not the honest 2D script (which
  diverges at σ15: 215.7 m — artifact-confirmed, mechanism above).

## Still open (needs flight or new data)

End-to-end real-sensor run; ratio gate with real VIO covariance; RTK floor
audit; EuRoC/Vicon idle; BPU/flight-binary/hash-retrieval/VecMapLocNet
unbuilt; dense showcase n=1 trajectory; lost XIAN per-traj curves (~2–3 h
re-run); 8 C++ tests now green (this session).
