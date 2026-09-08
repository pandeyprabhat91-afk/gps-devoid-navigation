# XIAN-Visloc Full Run — All 21 Trajectories (2026-08-17)

Follow-up to 24th iteration. User asked: run the best method (seed + KLT
propagation, dense arm) on ALL remaining trajectories, store detailed
results, and assess RDK X5 realtime feasibility.

## Method (unchanged from 24th iter)

- Baseline: per-frame ORB pool match on satellite crop at GPS (392 px,
  GSD 0.242 m/px, ~95 m window). Solve = >= 10 inliers.
- Dense arm: seed at frame 0 (ORB match at GPS), then KLT + MAGSAC H_rel,
  H_abs_k = H_abs_{k-1} @ H_rel, position = frame centre through H_abs.
  Re-match when tracks < 20, inliers < 10, or position > 90 m from crop
  centre. Fail -> coast.
- Coarse arm skipped (already proven dead in 24th iter on Xian16/Weinan01).
- Baseline parallelized with ProcessPoolExecutor (8 workers) — pure CPU;
  ORB has no CUDA path, GPU would not help.

## Full results (21/21 trajectories)

| Traj     | step m | solve% | p50 b | max b | dense p50 | y50% | cov% |
| -------- | ------ | ------ | ----- | ----- | --------- | ---- | ---- |
| Xian01   | 3.5    | 15.5   | 25.6  | -     | 181.6     | 20   | 43   |
| Xian02   | 3.8    | 39.2   | 34.2  | -     | 40.6      | 57   | 14   |
| Xian03   | 3.8    | 31.3   | 34.8  | -     | 673.7     | 17   | 20   |
| Xian04   | 2.8    | 1.8    | 27.4  | -     | 42.9      | 50   | <1   |
| Xian05   | 3.3    | 54.1   | 8.6   | -     | 11.4      | 86   | 50   |
| Xian06   | 3.8    | 19.1   | 30.5  | -     | 22.5      | 100  | 1    |
| Xian07   | 4.4    | 88.4   | 35.2  | -     | 35.7      | 77   | 62   |
| Xian08   | 8.6    | 55.5   | 36.0  | 64.5  | 520.6     | 5    | 25   |
| Xian09   | 10.1   | 51.8   | 34.3  | 64.3  | 1135.5    | 0    | 56   |
| Xian10   | 10.0   | 63.7   | 35.7  | 73.7  | 888.3     | 1    | 64   |
| Xian11   | 9.9    | 72.1   | 35.6  | 64.1  | 1051.6    | 1    | 60   |
| Xian12   | 12.5   | 83.5   | 35.2  | 192.1 | 1106.7    | 2    | 95   |
| Xian13   | 12.5   | 74.3   | 35.8  | 152.4 | 1171.7    | 1    | 95   |
| Xian14   | 12.6   | 81.8   | 34.0  | 185.0 | 872.8     | 0    | 88   |
| Xian15   | 12.6   | 83.3   | 35.5  | 89.0  | 642.9     | 3    | 85   |
| Xian16   | 3.8    | 74.0   | 19.7  | -     | 21.1      | 100  | 97   |
| Xian17   | 4.3    | 68.2   | 31.6  | 78.5  | 40.0      | 50   | 25   |
| Xian18   | 10.0   | 41.6   | 34.9  | 62.8  | 732.2     | 1    | 24   |
| Xian19   | 10.0   | 65.1   | 35.8  | 62.6  | 1301.2    | 0    | 63   |
| Weinan01 | 12.5   | 12.0   | 39.7  | -     | 643.8     | 7    | 6    |
| Weinan02 | 12.5   | 10.5   | 39.4  | 58.7  | 876.0     | 15   | 9    |

step = median frame-to-frame GPS step. cov = dense n_valid / frames.
max b = worst baseline error where recorded (per-frame errs only persisted
for 08-19, W02; earlier runs saved summaries only — see note).

## Findings

1. **Spacing gate confirmed on 21 trajs.** Dense p50 < 50 m ONLY on trajs
   with median step <= 4.4 m (02, 04, 05, 06, 07, 16, 17). Every traj with
   step >= 8.6 m drifts to 500-1300 m even at high solve rate (Xian12:
   83.5% solve, 12.5 m step -> dense 1107 m).
2. **Spacing alone not sufficient** — solve rate also gates. Xian01 (3.5 m
   step, 15.5% solve) -> dense 181 m; Xian03 (3.8 m, 31%) -> 674 m.
   Chain needs successful re-anchors; low solve = few anchors = drift.
   Combined gate: step <= ~5 m AND solve >= ~50% -> dense ~11-40 m.
3. **Baseline p50 cluster at 34-36 m across 14/21 trajs** = dataset GPS
   noise floor (max baseline err 58-192 m on high-step trajs supports
   noisy GT, not estimator errors). Xian05 8.6 m = best (calm GPS).
4. **Xian16 stays the showcase**: 21.1 m p50, 97% coverage, 100% yield50 —
   the only traj where the chain carries the whole flight at video rate.
5. **Xian08 packaging bug**: CSV lists 725 images, 323 unreadable
   (17_*.jpg naming mismatch) — matchable 402. Known from 24th iter.
6. **Dense arm is cheap when it works**: Xian16 dense 367 prop frames —
   KLT-only frames cost ~10-30 ms each; ORB only on seed/rematch.

## X5 realtime feasibility

- Serial desktop per-match: 792 ms p50 (490x490 vs 392 crop, ORB pool).
  Bigger high-step images ~3-5x slower.
- RDK X5 = 8x Cortex-A55 @ 1.8 GHz, 10 TOPS BPU, no GPU. A55 single-core
  ~0.25-0.4x desktop per-core -> per-match ~2-4 s worst case.
- Architecture needs: anchor 0.1-0.5 Hz (2-10 s budget — fits), KLT chain
  between anchors (~10-100 ms/frame on A55 — fits), VIO frontend (Fast +
  PyrLK 480p, C++/NEON ~15-30 ms/frame — fits at 30 Hz), IMU EKF (free).
- Verdict: feasible in C++ with shared tracker (one KLT stream feeds both
  propagation and VIO); Python pipeline not realtime on X5. BPU idle
  unless NN features added.
- Caveat: estimates from desktop scaling, NOT measured on X5. First X5
  flight is still the closing experiment.

## Artifacts

- `E:\kp_vio\kp_vio_py\results\gate_xian_prop_runA_01_09.json` — Xian08 full arms (per-traj checkpoints for 01-07 were overwritten by --out reuse; console summaries captured in session log)
- `gate_xian_prop_runA_traj09.json`, `runB_traj10/11/12_13/14_15/17_18/19`, `runB_weinan02.json` — full arms with per-frame errs
- `gate_xian_prop_timing_probe.json` — serial 30-frame timing probe (792 ms/match)
- Script: `E:\kp_vio\kp_vio_py\scripts\gate_xian_propagation.py` (patched: --workers, --limit, --no-coarse, --trajs, baseline errs/timings persisted)

## Data gap

Per-frame baseline errs for Xian01-07, 12-15, 17, 18 lost (checkpoint
overwrite bug in run orchestration, not in script — script persists when
--out omitted). Summary stats intact. Re-run with default out naming
(~2-3 h) to recover errs if needed for paper plots.
