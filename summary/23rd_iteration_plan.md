# 23rd Iteration — Plan: Fix Propagation, Retrieval Floor, Fine-Tuned Matcher

**Date:** 2026-08-16
**Trigger:** user — "method has to work in all regions, accuracy may vary";
search 2024–2026 (China-dominated) ranked 4 transferable directions;
user assumption: **GPS available at flight start → initial fix always
available** (cold-start problem eliminated by takeoff-time GPS).
**Mode:** autonomous execution loop, gates in order A → D → B.
**Data:** existing only (UAV-VisLoc; coop_uav for nothing here).

## Directions (from survey)

| Gate | Direction                                                                                                | Papers                                                                  | Question                                                                         |
| ---- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| A    | Fix propagation: match once, KLT-track map points, PnP each frame; satellite re-match only on track loss | Yao JAG 2024 §3.3.4, RARFLoc 2025, NGPS IROS 2026 (velocity-predictive) | Does one good fix carry forward across frames?                                   |
| D    | Retrieval floor: DINOv2 top-k tile as coarse fix everywhere                                              | One-to-Many RS 2025, SatLoc-HAF RS 2025                                 | Can ceiling regions get a coarse (≤~130 m) fix instead of none?                  |
| B    | Fine-tune SuperPoint (homographic adaptation) on own drone↔satellite pairs                               | VL-MFL TGRS 2024, R2PLoc TGRS 2025, DINOv2-urban RA-L 2025              | Does training on the vintage gap lift corr→inlier conversion on ceiling regions? |

## Gate A — Fix propagation

- Seed: first frame with GT-tile match ≥10 inliers (production pool) — the
  user's start-of-flight fix; map points = seed inliers → lat/lon via H.
- Chain: KLT track seed pts k→k+1 (7 s spacing), PnP (EPnP + RANSAC, 8 px)
  on tracked 2D ↔ 3D ENU points, score vs GT.
- Re-match trigger: tracked < 20 or PnP inliers < 10 → production re-match;
  fail → no-fix (VIO coast) frame.
- Regions: R03 (control), R04 (sub-tile alias — measure offset coherence
  under propagation), R06 (whole-tile alias + prior-ratio gate at re-match).
  n=40 attempted each (R06 uses its 40).
- **Kill:** propagated p50 error > baseline per-frame match p50 on R03
  (13.9 m) → propagation worse than re-matching; close.

## Gate D — Retrieval floor

- DINOv2 index already built (5th iter, retrieval_index.npz). For every
  frame in all 11 regions: top-1 and top-5 retrieved tile centres vs GT.
- **Kill:** if top-5 median error > 400 m on any region → floor too coarse
  to call "works"; report per-region table either way.

## Gate B — Fine-tuned matcher prototype

- Homographic adaptation: fine-tune SuperPoint (lightglue package) on
  R03 matched pairs (drone ↔ GT patch, known H → supervision), ~500 pairs,
  RTX 3060, ≤ 2 h.
- Eval: R09 (ceiling, unseen) + R03 held-out: corr→inlier conversion and
  solve rate vs baseline SuperPoint+LightGlue and ORB pool.
- **Kill:** R09 solve rate unchanged (≤ baseline) → fine-tuning does not
  cross the vintage gap; close learned-matcher line with mechanism.

## Reporting rules (inherited)

Denominators inline; kill criteria honoured; n≥40 attempted for adoption
claims; no cross-harness quoting.
