# Action 2 — Backwards-Rate Benchmark vs Published Rejection Methods

**Date:** 2026-08-15
**Script:** `E:\kp_vio\kp_vio_py\scripts\bench_rejectors.py` (new, cross-quote-safe
harness sharing the production `MapMatcher` protocol of
`comprehensive_scene_test.py`).
**Pool:** production config (multi_feature, ncc_verify=0.30, DEM/AGL,
min_inliers=10), n=40/region, regions 03 (control) / 04 / 06, drifts
150/300/600 m, seed 1992. 255 pooled fixes total (vs 55 in the 10th
iteration).

## Method

Five rejection methods implemented from published designs, all operating on
the _accepted-fix stream_, all using only signals a deployed system has
(priors, estimates, filter RMS). Ground truth appears solely in the
oracle-uncertainty diagnostic of the prior-ratio gate, labelled as such.

| Rejector        | Published source                                   | Implementation                                                                                      |
| --------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| seq-consistency | ORB-SLAM3 covisibility principle; 10th iter Step 3 | fix kept iff ≥1 neighbour within ±1 frame agrees ≤ tol, motion-compensated by priors                |
| 3-consecutive   | ORB-SLAM (original) loop rule                      | fix kept iff both immediate neighbour fixes exist and agree ≤ tol                                   |
| PCM max-clique  | Kimera-RPGO PCM                                    | greedy max clique over the pairwise-consistency graph                                               |
| frame-alignment | VINS-Fusion `global_fusion` (TError + Huber)       | robust (median) prior↔estimate frame offset; reject residual > τ                                    |
| prior-ratio     | 11th iteration (project)                           | reject if dist(prior,fix)/prior-uncertainty > 1.5; deployed = filter RMS, oracle = true prior error |

Metric per cell: good-kept% / fatal-kept% (denominators inline), discrimination
ratio = good%/fatal% (>1 = forward). Adoption bar (10th iter Step 3): fatal
cut ≥ 25% AND good kept ≥ 80%.

## Result — pooled

| Method                   | Setting     | d150 ratio              | d300 ratio              | d600 ratio               |
| ------------------------ | ----------- | ----------------------- | ----------------------- | ------------------------ |
| seq-consistency          | w=1 tol=100 | 0.96 (96%/100%)         | 0.84 (84%/100%)         | 0.81 (59%/73%)           |
| ORB-SLAM 3-consecutive   | tol=100     | 0.95                    | 0.97                    | 0.45 (n=3!)              |
| PCM max-clique           | tol=100     | 3.02 (40%/13%)          | 3.17 (23%/7%)           | 0.79                     |
| frame-alignment          | tau=100     | 2.09 (56%/27%)          | 2.80 (20%/7%)           | 1.12                     |
| prior-ratio deployed RMS | r=1.5       | **2.12 PASS** (99%/47%) | 1.08                    | 1.00                     |
| prior-ratio oracle unc.  | r=1.5       | **2.31 PASS** (92%/40%) | **1.95 PASS** (97%/50%) | **1.57 PASS** (100%/64%) |

**Headline 1 — no consistency-based method passes the adoption bar in any
cell at any drift.** Sequential consistency and the 3-consecutive rule
discriminate _backwards_ or neutrally everywhere (ratio ≤ 1.17, and >1 only
in the n=2 cell). PCM and frame-alignment achieve forward ratios only by
keeping 7–40% of good fixes — the purity-for-coverage trade, now measured as
a rate rather than asserted.

**Headline 2 — the prior-ratio gate separates the WHOLE-TILE class and only
that class.** With honest uncertainty it passes at all three drifts. With the
harness's RMS it passes only at d150: the dataset's drift model makes the
reported covariance conservative at d300+ (as predicted in the 11th
iteration). Its failure on the sub-tile class is clean and diagnostic
(§per-region).

## Result — per-region (the taxonomy table)

| Region         | Alias class        | seq-cons (d300, tol=100)         | 3-consec (d300) | PCM (d300, tol=100) | prior-ratio oracle (d300) |
| -------------- | ------------------ | -------------------------------- | --------------- | ------------------- | ------------------------- |
| R03 control    | none (0 fatal)     | 85% good kept                    | 50%             | 24%                 | 100%                      |
| R04 sub-tile   | ±20–80 m, coherent | **85% good / 100% fatal (0.85)** | 30%/57% (0.52)  | 19%/14% (1.30)      | 93%/100% (**0.93**)       |
| R06 whole-tile | 150–400 m jumps    | 79%/100% (0.79)                  | 7%/14% (0.50)   | 29%/0% (inf)        | 100%/**0% (inf)**         |

**The three rows are three clean findings:**

1. **R06 whole-tile aliases are fully separable** — prior-ratio with honest
   uncertainty keeps 100% of goods and 0/7 fatals at d150 and d300
   (reproduces and extends the 11th-iteration 7/7 result).
2. **R04 sub-tile aliases are invisible to every tested signal** —
   consistency methods keep fatal fixes at a _higher_ rate than good ones;
   even the oracle-uncertainty ratio gate scores 0.93 (the alias sits 20–80 m
   from a prior that is 300 m uncertain).
3. **The control (R03) measures the collateral** — the same filters that fail
   on the alias classes destroy 15–76% of good fixes on healthy terrain.

## Verdict

**Action 2 SUCCEEDS.** Finding U generalises from one hand-rolled filter to
four published rejection designs: on sub-tile coherent aliases, rejection is
structurally backwards or coverage-destroying, while a different (non-
consistency) signal cleanly handles the whole-tile class. This is the
quantitative core of the paper's claim — a backwards-rate table the
literature does not have (closest: Lajoie's theoretical treatment; Vineyard
SLAM's qualitative row-aliasing reports).

## Artifacts

- `results/action2_pool_d{150,300,600}.json` — fix pools (est/prior/gt/rms)
- `results/action2_rejectors.json` — pooled + per-region rate tables
- `results/action2_collect_d*.log`, `results/action2_analyze.log`
