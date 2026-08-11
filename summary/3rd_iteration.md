# GPS-Denied UAV Navigation — 3rd Iteration

**Project:** MTech Final Year Project, IIT Madras
**Date:** 2026-08-07
**Status:** Production position-method bug fixed. A benchmark **prior leak**
identified, invalidating the accuracy numbers this project had been reporting.
Four published sequence methods tested under a realistic drifted prior — none
beat the existing pipeline. **Fatal error rate cut 3.4× (35.0 % → 10.3 %) by
raising `min_inliers` 8 → 10**, now shipped. Usable coverage remains farmland
only.

### Headline Numbers (production config, 300 m prior drift, 6 regions, n=40)

| | before this iteration | after |
|---|---|---|
| Fatal error rate (accepted fixes >50 m wrong) | 35.0 % | **10.3 %** |
| CEP90 | 336 m | **47.7 m** |
| CEP50 | 34.6 m | 23.1 m |
| Useful-fix yield (all frames) | 16.2 % | 14.6 % |
| Working terrain | farmland only | farmland only |

**Rule followed throughout this session:** no number from any prior document (this
project's own `.md` files included) was trusted as a decision input. Every number
below comes from a script actually run this session. This iteration supersedes
numeric claims in `final_implementation.md`, `diagnosis_and_plan_2026-04-03.md`,
and even this session's own early write-ups wherever they conflict.

> ### ⚠ Correction (added 2026-08-07, after Sections 2–5 were first written)
>
> **Every accuracy number in Sections 2, 3 and 5 was measured with ground truth
> wired into the estimator, and must be read as an upper bound on the matching
> stage in isolation — not as an end-to-end GPS-denied result.**
>
> `run_map_match_benchmark.py` passes `gt_lat, gt_lon, gt_alt` as the VIO
> dead-reckoning prior. `MapMatcher` consumes that prior in four places:
> candidate tile selection, GSD rescale, the output altitude (copied verbatim,
> so altitude error is structurally zero), and the ~500 m position sanity check.
> With a zero-error prior the correct tile is always candidate #1 and the sanity
> check is gated on ground truth. The benchmark's own docstring says so; these
> summary documents dropped the qualifier.
>
> Two follow-up searches with **injected prior drift** (`graph_search_papers.py`;
> reports `paper_graph_search_2026-08.md` and `rejection_gates_2026-08.md`)
> established three things that change how this iteration should be read:
>
> 1. **CEP50 is the wrong headline metric.** Under drift 0→300 m, aggregate
>    CEP50 barely moves (34.4 → 34.6 m) while CEP90 more than doubles
>    (159 → 336 m). A successful match is anchored by image content; the prior
>    governs the **tail**, which the median cannot see. Every number in §2–§5 is
>    a median.
> 2. **The pipeline is prior-conditioned local map matching, not global
>    localization.** It cannot localize without a prior good to roughly one tile.
> 3. **The metric that actually mattered was never being measured.** At the
>    settings used for §5, **35 % of accepted fixes were wrong by more than
>    50 m** — and two regions had a *100 %* fatal rate, emitting nothing but
>    noise that the aggregate median diluted into respectability. §6c fixes this.
>
> **Which sections survive:** §4 (region-08 geometry) and §6 (the three
> semantic/abstraction attempts) are **unaffected** — both used the ground-truth
> tile directly and never depended on the prior. §2's *qualitative* finding (the
> wrong position method was shipped) stands; its numbers do not. §3 and §5 are
> upper bounds. §6b and §6c were written after the leak was found and are sound.

---

## 1. Why This Iteration Exists

The 1st iteration proposed the satellite-matching architecture. The 2nd iteration
rejected it (too close to BEV-Patch-PF) and pivoted to the nested-filter/AHRS-
consistency research direction, while noting the engineering prototype (kp_vio)
would continue in parallel. This iteration covers what actually happened when the
prototype's claimed accuracy numbers were put through a real reproduction pass —
and what happened when the guide's 27 July "hash a map segment" suggestion was
chased down through three separate implementation attempts.

Four threads converge here, in the order they were worked:

1. **A real bug in the production pipeline** (§2) — the shipped code was not
   using the position method the documentation called final. Found, fixed,
   benefit measured.
2. **Three attempts at semantic/structural map matching** (§6) — classical
   blob-correspondence, classical NCC-abstraction, and a genuinely trained
   supervised network. All three negative or marginal.
3. **A benchmark prior leak** (correction note, §6b) — the harness fed ground
   truth to the estimator as its VIO prior, so the accuracy numbers this project
   had been publishing were upper bounds on the matching stage in isolation.
   Fixing it also showed that CEP50, the metric used throughout, is blind to the
   failure mode that matters.
4. **A reliability fix** (§6c) — once fatal error rate was measured instead of
   median error, the dominant knob turned out to be `min_inliers`, a parameter
   already in the code. Raising it 8 → 10 cut fatal errors 3.4×.

Threads 3 and 4 arose from questioning thread 1's own results, and produced the
most consequential findings in this iteration.

### What Was Retracted During This Iteration

Three claims were made and then withdrawn after further testing. They are kept
visible rather than deleted, because the retractions carry the methodology:

| Claim | Why it failed |
|---|---|
| "24.9 m CEP50 / 93.3 % match is the pipeline's accuracy" | Measured with ground truth wired in as the prior |
| "Particle filtering beats argmax outright" | The filter was clamping onto the leaked prior; monotone-to-the-edge parameter sweep was the tell |
| "Multi-frame pooling is catastrophic (924 m)" | A naive centroid averaging across spatial modes — the bug the cited paper exists to solve, not a result about the paper |

---

## 2. The Accuracy Bug

### 2.1 What was wrong

`map_matcher.py` (the production `MapMatcher` class) was not implementing the
position-estimation method that `final_implementation.md` documented as final. The
document said **H_inv** (drone image centre projected through the inverse
homography into satellite-tile pixel space, then to lat/lon). The actual code was
running **per-inlier-median triangulation** — a different, and empirically worse,
estimator that only ever existed correctly in a disconnected standalone script
(`refine_position.py`), never merged into the class the rest of the project
actually calls.

A second, smaller divergence: the ratio test default was silently 0.92, not the
documented 0.75 the "final config" table claimed.

### 2.2 The fix and its real, measured effect

`map_matcher.py` was patched: H_inv position method, MAGSAC estimator, ratio=0.75
explicit, ORB features bumped 3000→15000 (chosen via the graph search in Section 3).

**Region 04 (rural/farmland), before vs after, same production pipeline:**

| | Match rate | CEP50 |
|---|---|---|
| Before (undocumented per-inlier-median method) | ~45-93%* | 35.8m |
| After (H_inv, documented method) | 93.3% | **24.9m** |

*match rate varied across earlier runs at different feature counts tested this
session; accuracy was consistently worse than after the fix regardless.

This confirms the ~30m single-shot accuracy claim in `final_implementation.md` is
real and reproducible — it just was not the method actually running in the codebase
prior to this session.

---

## 3. Systematic Config Search (Graph-Based)

### 3.1 Method

Built a standalone, single-GT-tile test harness (`scripts/graph_search_config.py`)
to isolate parameter effects from the production pipeline's retrieval/candidate-
selection logic. Traversed a config graph from a ROOT node (documented "final"
settings) via one-dimension-changed children, greedy hill-climbing toward highest
match rate among configs with CEP50 < 50m. Fixed test set: 6 regions, n=40/region.

### 3.2 Full node table

| # | Features | Ratio | min_inliers | Match rate | CEP50 | CEP90 |
|---|---|---|---|---|---|---|
| 1 (ROOT) | 3000 | 0.75 | 8 | 12.5% | 20.3m | 48.2m |
| 2 | 3000 | 0.92 | 8 | 65.0% | 236.1m | 393.5m |
| 3 | 15000 | 0.75 | 8 | 21.2% | 22.2m | 52.7m |
| 4 | 15000 | 0.85 | 8 | 37.1% | 49.3m | 338.9m |
| 5 | 15000 | 0.75 | 6 | 32.1% | 31.6m | 262.7m |

**Key finding — a real, unavoidable accuracy-vs-coverage tradeoff along the ratio
axis:** looser correspondence acceptance finds more candidate positions but admits
geometrically-inconsistent ones the homography fit cannot fully filter (0.75→0.92
moves match rate 12.5%→65.0% but CEP50 20.3m→236.1m). This is not a bug — it is the
matching approach's fundamental limit on this dataset.

More ORB features (3000→15000) at the tight ratio was the cleanest win: nearly
doubles ROOT's match rate with almost no accuracy cost (node 3).

### 3.3 The lesson that mattered most: harness results don't transfer safely

Node 5 (`min_inliers` 8→6) looked like the best node in the isolated harness
(32.1% / 31.6m). Applied to the **real** production pipeline (DINOv2 retrieval +
5-9 candidate tiles + corner fallback), it caused a severe regression: match rate
improved as expected, but CEP50 blew up to 139-343m across most regions. Root
cause: with multiple candidate tiles competing on raw inlier count, a lowered
threshold lets a weak/wrong match on the **wrong** tile win the comparison against
the correct tile — a failure mode that cannot exist in a single-tile test, because
there is no competition to exploit.

**Reverted `min_inliers` to 8.** The production config at the time of writing was:
features=15000, ratio=0.75, MAGSAC, H_inv, min_inliers=8.

> **Superseded — `min_inliers` is now 10 (§6c).** This entire subsection's
> reasoning was sound but its evidence was not: every number above was measured
> with ground truth wired in as the prior, and judged on CEP50. Re-run under a
> drifted prior and judged on **fatal error rate**, the answer is 10, not 8 —
> and 8 turned out to sit *inside* the failure mode, since bad fixes cluster at
> 8–9 inliers. The lesson §3.3 draws (harness results don't transfer) held up;
> it just applied to this section's own conclusion as well.
>
> The features=15000 and ratio=0.75 choices were **not** re-derived under drift
> and remain on the same weak footing. Open item.

---

## 4. Region 08 — A Different, Non-Tunable Failure

Region 08 fails at **every** tested config, including the most permissive
(65% match rate elsewhere). Direct inspection of a "good" frame (13,082 query
keypoints, 13,157 tile keypoints, 2,577 descriptor-level "good" matches at ratio
0.92) found only **9 geometrically consistent inliers** survive MAGSAC — barely
above threshold, below it at tighter ratios.

**Not a feature-count or ratio problem.** Points to non-planar scene structure
(buildings/elevation breaking the flat-ground homography assumption) or a genuine
tile/GT coordinate mismatch specific to this region. Not resolved this session —
needs a different geometry model or a data-integrity check, not more parameter
search.

---

## 5. Final Production Numbers, by Terrain

All numbers: production `MapMatcher`, winning config (features=15000, ratio=0.75,
MAGSAC, H_inv, min_inliers=8), n=60/region, sub-800m-AGL regions only (confirmed
via CSV height field this session — regions at 2000m+ elevation, e.g. mountain
plateau R05 and desert R11, were out of scope for this fix cycle and were **not**
re-verified with it; their last known numbers are from the pre-fix buggy pipeline
and should not be trusted).

| Terrain | Region | Match rate | CEP50 | Verdict |
|---|---|---|---|---|
| Rural/farmland | 04 | 93.3% | **24.9m** | Works |
| Rural/farmland | 03 | 38.3% | **17.8m** | Works, lower coverage |
| Suburban/mixed | 09 | 3.3% | 93.7m | Barely functional |
| Riverside/semi-urban | 01 | 5.0% | 347.3m | Broken — matches when found are wrong |
| Mountain/forest | 06 | 0.0% | — | Complete failure |
| Suburban/mixed | 08 | 0.0% | — | Complete failure, separate geometric cause (Section 4) |

**Only farmland terrain works reliably.** Mountain/forest and one suburban region
are total failures. The other two terrains (riverside, remaining suburban) barely
produce matches, and region 01's matches are actively wrong when they do occur —
worse than not matching at all for a system that would trust these fixes blindly.

> **Correction to region 01 (2026-08-07).** The "matches but wildly wrong"
> behaviour is **drift-triggered, not intrinsic**: CEP50 is 72 m at 150 m prior
> drift and 483 m at 300 m drift. It switches on only once drift pulls a
> look-alike tile into the candidate set — textbook perceptual aliasing. Under
> the zero-drift prior used for the table above it does not appear at all.
>
> **All numbers in this table were measured with a zero-error prior.** Under a
> realistic drifted prior the match rates and medians hold roughly, but CEP90
> across all regions rises from 159 m to 336 m at 300 m drift, and to 513 m at
> 600 m. The 6-region aggregate under drift is: 25.0 % match, 34.6 m CEP50,
> 336 m CEP90.

### 5.1 Per-Scene Method Comparison (300 m prior drift)

Which method wins on which terrain, under a realistic drifted prior. Zero-drift
columns are excluded — they are contaminated by the prior leak (see §6b).

| Region | Terrain | Match% | Best CEP50 | Best CEP90 | Winner | Usable? |
|---|---|---|---|---|---|---|
| 03 | rural/farmland | 52.5 | **21.4 m** | **61.6 m** | argmax | Yes |
| 04 | rural/farmland | 70.0 | **38.2 m** | 198.5 m | argmax | Yes |
| 09 | suburban/mixed | 7.5 | 48.3 m | 88.1 m | argmax | 3 frames only |
| 08 | suburban/mixed | 7.5 | 124.3 m | 273.3 m | argmax | No |
| 01 | riverside/semi-urban | 12.5 | 192.2 m | 363.1 m | PF | No |
| 06 | mountain/forest | 5.0 | 244.6 m | 279.6 m | PF | No (2 frames) |

**argmax wins 4 of 6 scenes, including both scenes that actually work.** The
particle filter wins only on regions 01 and 06 — both broken regardless, where
"winning" means less catastrophically wrong, on 2–5 frames. Not results.

### 5.2 Honest Comparison Against Published Work (cpvrLab / armasuisse)

The cpvrLab feasibility study reports **76.7 % recall within 50 m** with
**zero fatal errors (>50 m)** on unseen flight data. That is not directly
comparable to the numbers above, and the difference cuts both ways:

**Not comparable on accuracy.** Their metric is *recall inside a 50 m radius*;
ours is *CEP50*, a median error distance. Region 03 at 21.4 m CEP50 means the
median frame lands comfortably **inside** their 50 m success radius — scored
their way it would post a high recall figure. Their 56.7 %→76.7 % improvement is
a coarse-retrieval recall gain, not a fine-positioning gain.

**Genuinely worse on reliability.** cpvrLab report **0 fatal errors**. This
pipeline's CEP90 of 336 m at 300 m drift means **>10 % of accepted fixes are
catastrophically wrong** — and it emits them with no confidence signal to
distinguish them from good fixes. A navigation system that occasionally asserts
a confident position 300 m off is worse than one that declines to answer.

**This, not median accuracy, is the real gap.** It is the same tail problem
identified in §4 and confirmed by the drift sweep. Closing it is the priority.

High-elevation mountain (R05) and desert (R11) regions were never re-tested with
the corrected pipeline this session — their status is genuinely unknown, not
"unchanged from before."

**The ~9m EKF-fused accuracy claim in `final_implementation.md` remains unverified**
this session. Fusion needs repeated matches to converge; at this configuration most
terrains don't produce enough matches for that to be tested meaningfully.

---

## 6. Three Semantic/Structural Matching Attempts — All Negative

Prompted by the guide's 27 July hashing suggestion. Escalated in three stages per
explicit instruction to "take the longer route" after the first two came back
negative.

| Attempt | Segmentation source | Matching strategy | Result |
|---|---|---|---|
| `semantic_matcher.py` | Classical HSV/edge heuristic | Blob correspondence + RANSAC | **0/11** regions passed inlier threshold |
| `abstraction_matcher.py` | Classical HSV/edge heuristic | Flat-render + NCC template | **4/11** regions weakly beat raw pixel |
| `abstraction_net.py` | **Trained** (Firefly, real pretrained aerial segmenter, ECCV 2026) + trained dual-encoder | Flat-render + NCC template | **5/11** regions beat both baselines |

Real, monotonic improvement as segmentation quality improved — confirms
segmentation quality (not matching algorithm) was the limiting factor throughout.
But even the best version (genuine supervised training on a real pretrained
segmenter) does not approach the production pipeline's accuracy, and does not
reproduce the cpvrLab paper's own claimed 56.7%→76.7% recall jump — likely because
that paper's number is a coarse-retrieval recall metric, not the fine
position-error metric measured here, and because 173 training pairs is minuscule
next to a real flight dataset.

**Recommendation: do not pursue a fourth attempt at this line of work.** Three
matching strategies over three segmentation sources have now failed to close the
gap to the existing ORB/AKAZE/XFeat + EKF fusion pipeline. Full detail in
`kp_vio_py/results/semantic_matching_research_2026-08.md`,
`abstraction_matching_research_2026-08.md`, `learned_abstraction_research_2026-08.md`.

---

## 6b. Paper-Derived Sequence Methods Under Realistic Prior Drift

After the prior leak was found, a second graph search (22 nodes, 4 generations)
tested methods from the literature against a **drift-injected** prior. Full
report: `kp_vio_py/results/paper_graph_search_2026-08.md`.

Aggregate at 300 m prior drift — the only condition where the prior is not the
answer:

| Method | Source | Match% | CEP50 | CEP90 |
|---|---|---|---|---|
| **argmax** (current production) | baseline | 25.0 | **34.6 m** | 336 m |
| HMM | Newson & Krumm, ACM GIS 2009 | 28.8 | 40.7 m | 563 m |
| Particle filter | Werner et al. 2025 (SPRIN-D winner) | 28.8 | 120.6 m | **269 m** |
| Multi-frame pooling | Video2BEV / MuSe-Net | 28.8 | 256.5 m | 3835 m |

**No published method beat the existing simple argmax pipeline on median
accuracy.** Only the particle filter beat it on the tail (269 vs 336 m). All
sequence methods raise match rate by ~3.5 points by emitting estimates on frames
argmax rejected — but those are the hard frames, so the estimates are poor. Same
coverage-vs-accuracy tradeoff found earlier on the ratio-test axis.

Per-region, the particle filter **helps only where argmax has already failed**
(region 01: 484→269 m) and **hurts wherever argmax works** (region 03: 21→119 m;
region 04: 38→112 m). It is a tail-taming device that costs median accuracy.

**Two negative results were traced to bugs in this project's own implementation,
not to the papers:**

- An apparent particle-filter win at zero drift (11.8 m CEP50) was an artifact:
  the filter initialises particles at the prior, and at zero drift the prior is
  ground truth, so it was scoring against the answer. The tell was that CEP50
  improved monotonically to the edge of the parameter sweep with no interior
  optimum. All zero-drift PF numbers are void.
- The multi-frame method's catastrophic result (924 m CEP50) came from pooling
  candidate positions with a naive centroid, which lands between modes when a
  window spans different tiles — reproducing the exact failure Werner et al.
  solve with largest-cluster selection. Fixing it gave 145 m.

HMM cannot work on this data for a structural reason: region 01's matched frames
are isolated (frames 9, 34, 35, 37 of 40), leaving almost no temporal adjacency
to chain. Newson & Krumm's result assumes a contiguous trajectory. This was
predicted from the frame indices before the node was run, and confirmed — HMM
returned numbers identical to argmax on that region.

## 6c. Improvement Roadmap — What the Better-Performing Projects Do Differently

Reviewing cpvrLab/armasuisse (76.7 % recall, 0 fatal errors) and Werner et al.
(SPRIN-D winner, 9 km GNSS-denied, CPU-only) against this pipeline, four
structural differences explain most of the performance gap. Ranked by expected
benefit per unit of effort.

### Priority 1 — DONE, and the answer was a parameter already in the code

cpvrLab's headline achievement is **0 fatal errors**, not 76.7 % recall. The
measured baseline here was **fatal50 = 35.0 %** — over a third of *accepted*
fixes wrong by >50 m, emitted with no usable confidence signal.

Two new gates were built and tested (full report:
`kp_vio_py/results/rejection_gates_2026-08.md`):

- **Reprojection-residual gate** — best case 35.0 → 32.6 % fatal, but cost 20 %
  of useful fixes. No Pareto gain.
- **Margin gate** (reject unless winner clearly beats runner-up) — made fatal
  errors **worse** (35.0 → 40.0 %). On repeating terrain, contested frames are
  disproportionately the *correct* ones, so it removed good fixes fastest.

**Both failed. The fix was `min_inliers`, already present in the code:**

| min_inliers | match% | CEP50 | CEP90 | fatal50 | good_yield |
|---|---|---|---|---|---|
| **8** (previous) | 25.0 | 34.6 m | 336.0 m | **35.0 %** | 16.2 % |
| **10** (recommended) | 16.2 | 23.1 m | **47.7 m** | **10.3 %** | 14.6 % |

Fatal errors fall **3.4×** for 1.6 points of yield; CEP90 falls **7×**. Diagnosis:
fatal fixes cluster at 8–9 inliers (good fixes median 17), so the old threshold
sat *inside* the failure mode.

**The transition is sharp — 9 is not enough.** fatal50 goes 35.0 → 21.7 → 10.3
across 8 → 9 → 10, then flattens; CEP90 goes 336 → 143 → 48 m. At 9 the fatal
rate is still double that of 10.

**The knee is drift-independent**, so a fixed constant is correct — no need to
estimate prior uncertainty online:

| prior drift | fatal50 | good_yield |
|---|---|---|
| 0 m | 11.6 % | 15.8 % |
| 300 m | 10.3 % | 14.6 % |
| 600 m | **4.3 %** | 9.2 % |

Counter-intuitively fatal50 *improves* as drift grows. Heavier drift pushes the
correct tile out of the candidate set entirely, so those frames produce **no**
match rather than a wrong one (match rate 17.9 → 9.6 %). **The system fails
safe** — it stops answering instead of answering wrongly. Under the old
CEP50-only metric this same effect merely looked like "drift barely matters".

**The per-region result matters more than the aggregate.** At `min_inliers=8`,
regions 06 and 08 had **fatal50 = 100 %** — every fix they produced was >50 m
wrong. They were never marginally working; they were emitting noise that the
aggregate median diluted. At 10 they correctly produce nothing.

So the improvement is mostly *"the broken regions stopped lying"*, not *"good
terrain got better"*. `min_inliers=10` converts a system that answers often and
is wrong a third of the time into one that answers on farmland only and is wrong
~10 % of the time. Remaining gap to cpvrLab's 0 % will not close by threshold
tuning — the knee is reached. It needs Priorities 2 and 3.

### Priority 2 — Coarse-to-fine, not single-shot matching

Both cpvrLab and Werner use an explicit **two-stage** search: coarse retrieval
over a wide area, then fine matching inside a cropped window. cpvrLab reach a
12.5 m radius this way. This pipeline retrieves candidate tiles and then does
one ORB+homography pass — there is no fine refinement stage, and the
phase-correlation step present in the code is applied *after* the winner is
already chosen, so it cannot fix a wrong-tile decision.

Adding a genuine fine stage (re-match at higher resolution within the winning
tile's neighbourhood) is the standard route to sub-tile accuracy.

### Priority 3 — Global retrieval to remove the prior dependency

The pipeline currently cannot localize without a prior good to ~1 tile (§ the
correction note). cpvrLab scan the **entire** 16,000×16,000 orthophoto; Werner
match heightmap gradients against a full prior map. Both are genuinely global.

The DINOv2 retrieval index already exists in this codebase but is used only to
supplement prior-centred candidates. Running it as a true global search — and
measuring recall@k against ground truth — would establish whether global
localization is achievable here at all, and would make the drift question moot.

### Priority 4 — Better invariant representation (lowest priority, already tried)

cpvrLab's abstraction gains came from stripping shadows, cars, and seasonal
colour. Three attempts at this (§6) produced 0/11, 4/11, 5/11. Two caveats
before any fourth attempt:
- Their gain was on **coarse retrieval recall**, which is Priority 3's metric,
  not fine positioning. Abstraction may help retrieval while doing nothing for
  the 21–38 m fine accuracy already achieved.
- Their training set is 4 real flights; ours was 173 pairs. The comparison was
  never fair.

Werner's result is the more relevant precedent: he won using **classical
gradient template matching**, not learned abstraction — evidence that
representation is not the bottleneck at this scale.

### Explicitly not recommended

- **More sequence filtering.** Four methods tested (§6b); none improved median
  accuracy. Region 01's matched frames are too sparse to chain.
- **More parameter tuning on the existing matcher.** Two graph searches have now
  found the axis is a coverage/accuracy tradeoff, not an unexploited optimum.

## 7. Open Items Going Into Next Iteration

### Resolved this iteration

- ~~**Region 01's "matches but wildly wrong" behaviour is uncharacterized.**~~
  **RESOLVED** — it is *drift-triggered*, not intrinsic (72 m at 150 m drift →
  483 m at 300 m). Perceptual aliasing becomes reachable once drift pulls a
  look-alike tile into candidacy. At `min_inliers=10` region 01 stops emitting
  bad fixes entirely.
- ~~**`min_inliers=8` may be an artifact.**~~ **RESOLVED** — it was. The correct
  value under a drifted prior, judged on fatal-error rate, is **10**. Applied to
  `MapMatcher` and `run_map_match_benchmark.py`. See §6c.
- ~~**A finer `min_inliers` sweep was not explored.**~~ **RESOLVED** — swept
  8/9/10/11/12/16 live, plus drift 0/300/600. Knee at 10, sharp (9 still gives
  21.7 % fatal), and drift-independent so a fixed constant is correct. An
  adaptive threshold is **not** needed.

### Still open, highest priority first

1. **Closing the gap to 0 % fatal errors needs P2/P3, not tuning.** The
   threshold knee is reached at 10.3 %. cpvrLab report 0 %. Next steps are
   coarse-to-fine refinement (§6c P2) and global retrieval (§6c P3), both
   substantially larger pieces of work than anything done this iteration.
2. **Region 08's non-planar/geometric failure** needs a different geometry model
   (e.g. fundamental matrix + local homographies) or a check on whether its tile
   data is actually correctly aligned to its stated GT coordinates.
3. **High-elevation regions (mountain plateau, desert) were never re-tested** with
   the corrected pipeline — genuinely unknown status, not carried forward from
   pre-fix numbers.
4. **EKF multi-match fusion accuracy (~9m claim) unverified** — needs real testing
   with the corrected single-shot pipeline once match-rate coverage improves enough
   to matter.
5. **`features=15000` and `ratio=0.75` were never re-derived under drift.** Both
   were chosen in §3 under the leaked prior and judged on CEP50. They may be as
   wrong as `min_inliers=8` was. Re-run the axis on fatal-error rate.
6. **Altitude is never estimated.** `pos_ned[2]` is copied verbatim from the
   prior's `pred_alt_m`, so all reported errors are effectively 2-D and 3-D
   error is structurally zero. Either estimate scale from the homography or
   state explicitly that the output is 2-D.
7. **EKF multi-match fusion accuracy (~9 m claim) unverified** — needs real
   testing with the corrected single-shot pipeline once coverage improves enough
   to matter. Note the claim predates every correction in this document.
8. Research-direction track (nested-filter/AHRS-consistency paper, per 2nd
   iteration) is unaffected by this iteration's engineering findings and
   continues in parallel — this iteration is prototype/engineering only.

### Reporting rules adopted (apply to all future work)

- **Report fatal-error rate and yield, not CEP50 alone.** The median is blind to
  the failure mode that matters. Two regions had a 100 % fatal rate while the
  aggregate median looked respectable.
- **Never quote a number measured with the prior set to ground truth** without
  labelling it an upper bound on the matching stage in isolation.
- **Never cross-quote between the two benchmark harnesses.**
  `run_map_match_benchmark.py` (n=60) and `graph_search_papers.py` (n=40,
  step-sampled) use different frames and report materially different match rates
  for the same region under the same conditions (region 03: 38.3 % vs 62.5 %).
- **Treat a monotone-to-the-edge parameter sweep as unfinished, not as a
  result.** This pattern produced one false finding this iteration (the particle
  filter clamping onto the leaked prior) and was the tell that caught it.
- **Do not let an n≈12 smoke test set search direction.** This happened once
  here: a one-frame fluctuation moved a metric 9 points and steered a whole
  generation of work.

---

## 8. Closing Assessment

The most valuable outcomes of this iteration are negative and methodological.

**What was actually wrong:** the project had been measuring the right system
with the wrong harness (ground truth fed in as the prior) and reporting it with
the wrong statistic (a median, blind to the tail). Both errors pointed the same
way — they made the pipeline look better than it was. Two regions were emitting
a 100 % fatal-error rate while the headline numbers looked respectable.

**What was actually fixed:** one production position-method bug (§2), and one
parameter — `min_inliers` 8 → 10 — that cut fatal errors 3.4× and CEP90 7×. The
second came from a search whose two purpose-built mechanisms both failed; the
answer was already in the codebase.

**What is honestly still true:** the system works on farmland and nowhere else.
`min_inliers=10` did not make the broken terrain work — it made the broken
terrain stop lying. That is a real improvement for a navigation system, where a
confident wrong fix is worse than no fix, but it is not new capability.

**Against published work:** cpvrLab report 0 % fatal errors; this reaches 10.3 %,
and only by declining to operate outside one terrain type. The remaining gap is
not reachable by parameter tuning — the knee is measured and reached.

---

*Document generated: 2026-08-07 | Version: 3rd Iteration (revised, same day) |
Status: **Shipped** — position-method bug fixed, benchmark prior leak identified
and all affected numbers re-qualified, four published sequence methods tested and
none adopted, `min_inliers` raised 8→10 cutting fatal errors 35.0 %→10.3 % and
CEP90 336 m→47.7 m. Working terrain: farmland only. Next step is coarse-to-fine
refinement or global retrieval (§6c P2/P3), not further tuning.*

*Supporting reports: `kp_vio_py/results/paper_graph_search_2026-08.md`,
`kp_vio_py/results/rejection_gates_2026-08.md`.*

---

> **Follow-up — 5th Iteration (2026-08-08) resolved several §7 open items:**
>
> - **Open item #2 (R08 non-planar/geometric failure needs a different
>   geometry model) — RENDERED MOOT.** The 3rd-iter diagnosis (flat-ground
>   homography breakage) was incomplete. The actual bottleneck was that ORB
>   alone fired too few keypoints to reach `min_inliers=10` on R08 —
>   pooling ORB + AKAZE + SIFT solved it without any geometric reformulation.
>   R08 now matches at 7.5% @ 0% fatal at 300 m drift with the same flat-ground
>   homography flagged as broken here. **The "non-planar geometry" framing was
>   wrong; it was an inlier-count problem.**
> - **Open item #3 (high-elevation regions never re-tested) — still open.**
>   The 5th-iter multi-drift comprehensive test covered 150/300/600 m on the
>   same six regions as the 3rd-iter; high-altitude R05/R11 remain untested.
> - **Open item #1 (closing `fatal50<5%` needs P2/P3, not tuning) —
>   CONFIRMED with caveat.** 5th-iter tested both DINOv2 global (P2-equivalent)
>   and CosPlace — both regressed (~5% match, not discriminative enough for
>   aerial↔satellite cross-view). The remaining `fatal50<5%` gap needs
>   **cross-view-TRAINED** retrieval (Sample4Geo / AnyLoc-VLAD-DINOv2), which
>   requires fine-tuning data out of this project's scope. Not the specific
>   retrievers flagged in §6c P3, but the *strategy* (global retrieval) was
>   right — just the candidate retriever was wrong.
> - **Working terrain expanded from "farmland only" (3rd-iter) to
>   "farmland + forest + non-planar suburban" (5th-iter).** The
>   `min_inliers=10` shipped here was the right call — it was never the
>   bottleneck for the broken regions; the missing piece was multi-feature
>   detection, not threshold tuning. See `5th_iteration.md` for the full
>   per-scene multi-drift tables and the new opt-in `MapMatcher` mode.
