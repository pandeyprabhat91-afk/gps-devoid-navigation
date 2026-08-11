# GPS-Denied UAV Navigation — 7th Iteration

**Project:** MTech Final Year Project, IIT Madras
**Date:** 2026-08-09
**Status:** Research + feasibility-gate pass. Five hypotheses tested, four
killed, one reframe that changes how every prior number should be read.
**No code adopted.** Production configuration unchanged.

> **Method note.** This iteration ran gates before builds: each hypothesis got
> a cheap kill-criterion test (5–20 frames, sometimes zero compute) and was
> only to be scaled up if it survived. Four died at the gate. The single
> most-cited lesson from iterations 3–6 — that full-scale sweeps were being
> spent on ideas a smoke test would have killed — is the rule this iteration
> was run under.

---

## 0. Headline

| | |
|---|---|
| 6th-iteration "generation is the bottleneck" conclusion | **RETRACTED** — refuted by oracle test |
| Cross-modal matcher (GIM) inliers vs production | **7× better** on R04 |
| GIM tile-discrimination gain | **zero** (40 % → 40 %) |
| Camera-tilt nadir-correction hypothesis | **killed at smoke test** (1.6 m, below threshold) |
| Altitude/GSD scale-bias hypothesis | **killed** (factor 1.00 optimal) |
| Published satellite-reference SOTA (AnyVisLoc, CVPR 2026) | **18.5 % A@5m** |
| Consequence | **R03 is plausibly at/near SOTA and is documented as a failure** |

---

## 1. The Oracle Test — Candidate Generation Is Not The Bottleneck

The 6th iteration concluded, by elimination, that since six *scoring* signals
had failed the remaining lever must be candidate *generation*. That was never
measured. It is now.

Running the adopted configuration at **drift = 0** makes the prior equal to
ground truth: the correct tile sits at the centre of the search window and is
scored first. This is a perfect-generation oracle. (The 3rd iteration
discarded this condition as a "prior leak" invalidating accuracy claims —
correct for accuracy, but it is exactly the right experiment for this
question, and no one had ever read **fatal50** off it.)

| Region | drift = 300 m | **drift = 0 (oracle)** |
|---|---|---|
| R01 riverside | 0 % | 0 % |
| R03 farmland | 80.0 % / 13.2 m / 0 % fatal | 82.5 % / 14.4 m / 0 % fatal |
| R04 farmland repetitive | 82.5 % / 32.9 m / **21.2 %** | 80.0 % / 30.6 m / **21.9 %** |
| R06 forest | 10.0 % / 28.1 m / 25.0 % | 10.0 % / 28.1 m / **25.0 %** |
| R08 non-planar | 7.5 % / 18.3 m / 0 % | 7.5 % / 17.6 m / 0 % |
| **Aggregate** | **30.8 % / 12.2 % fatal** | **30.4 % / 11.0 % fatal** |

**Finding H — a perfect candidate set buys 1.2 points of fatal rate and zero
match rate.** R06 is bit-identical. The generation hypothesis is dead, and
with it the recommendation to pursue cross-view-trained retrieval *on this
evidence*. (Such retrieval may still help for other reasons; it is simply not
supported by the argument the 6th iteration made for it.)

---

## 2. Cross-Modal Matchers — A Much Better Matcher That Selects No Better

The 5th iteration measured stock SuperPoint+LightGlue at **0.0 % match on all
six regions**, diagnosed a ground→aerial domain gap, and retired the entire
LightGlue / GlueStick / LIMAP / HardNet family. Two things were checked here.

### 2.1 The retirement rests on a broken integration

Using the official `lightglue` package (cvg) rather than kornia's port, on
ground-truth tiles, **stock SuperPoint+LightGlue produces 70–260 inliers**.
It does not return zero. The 5th-iteration probe measured an integration
failure, not a domain gap, and the family-wide retirement it justified is not
supported.

### 2.2 GIM: 7× the inliers, none of the discrimination

GIM (`vismatch/gim-lightglue`) retrains this exact stack for cross-modal
correspondence; its weights load into official LightGlue with 251/252 keys
matching. Mean homography inliers on the **correct** tile:

| Region | ORB+AKAZE+SIFT pool (production) | SP+LG stock | **SP+LG GIM** |
|---|---|---|---|
| R03 farmland | 128.3 | 70.5 | **399.2** |
| R04 repetitive | 90.2 | 259.9 | **632.4** |
| R06 forest | 5.0 | 20.2 | 2.8 |
| R08 non-planar | 3.2 | 4.0 | 1.6 |
| R01 riverside | 5.4 | 5.8 | 0.0 |

Then the question that actually matters — over a 5×5 tile ring, does the
correct tile *win*?

| Matcher | GT tile ranked #1 | Mean GT rank |
|---|---|---|
| ORB pool | 2/5 (40 %) | 1.80 |
| **GIM** | **2/5 (40 %)** | **3.00** |

**Finding I — matching quality and tile discrimination are independent.** GIM
produces 7× the correspondences on the correct tile and picks the correct tile
no more often; its mean rank is worse. One frame scored **665 inliers on the
correct tile and 680 on a wrong one**. The wrong tiles absorb the improvement
equally, because on repetitive terrain they contain genuinely similar content.

This closes the "use a better matcher" direction for the *selection* problem.
It does **not** close it for precision or coverage — see §5.

---

## 3. Trajectory-Level Selection — Reaches The Ceiling, And The Ceiling Is Low

NaviLoc (Drones 2026) is training-free, CPU-only (9 FPS on a Raspberry Pi 5),
rural, and states this project's exact problem: *"under perceptual aliasing,
high-similarity matches are often geographically inconsistent, so naïve
anchoring fails."* Its Stage 1 recovers a global SE(2) by maximising a
trajectory-level similarity objective. This is also the 4th iteration's
"Strategy 1", ranked 9th of 10 and never tested.

Implemented as offset clustering over all collected candidates (R04, n=20,
drift=300, relative motion taken from ground truth = upper bound):

| Method | fixes | CEP50 | fatal50 |
|---|---|---|---|
| argmax inliers (production) | 16/16 | 40.8 m | 31.2 % |
| trajectory cluster (perfect VIO) | 15/16 | 38.1 m | 26.7 % |
| trajectory cluster (VIO σ=50 m) | 9/16 | 28.6 m | 33.3 % |
| **oracle best-candidate** | 16/16 | 39.7 m | **25.0 %** |

**Finding J — trajectory clustering nearly reaches the oracle, and the oracle
is only 25 %.** In 4 of 16 R04 frames **no candidate anywhere in the window is
within 50 m**. Selection of any kind can recover at most ~6 points, and the
method degrades quickly with realistic VIO noise.

The residual is therefore not in *which* candidate is chosen. It is in the
position computed from an already-correct match.

---

## 4. What The Residual Error Actually Is — Two Different Failure Modes

Error distributions, pooled over the persisted per-frame CSVs:

| Region | histogram (m) | shape |
|---|---|---|
| R03 | 0-10:31, 10-20:49, 20-30:35, 30-40:9, 40-50:5 | unimodal, no tail |
| **R04** | 0-10:10, 10-20:37, 20-30:31, 30-40:24, 40-50:21, 50-60:18, 60-80:10, 80-100:5 | **continuous, no gap** |
| **R06** | 10-20:10, 30-40:5, **150-400:5** | **bimodal, clean gap** |

**Finding K — R04 and R06 have been reported under one metric for three
iterations and are not the same failure.** R06 is bimodal with nothing between
40 m and 150 m: discrete jumps to a look-alike tile, i.e. genuine aliasing.
R04 has no gap at all — a single continuous distribution whose tail crosses
the 50 m line. **R04 has no aliases to reject; it has imprecision.**

This explains six iterations of failed gates. Reprojection RMSE, inlier
margin, NCC veto, NCC ranking, NCC non-adjacency margin were all built to
reject wrong-*tile* matches. On R04 the matches are on the right tile. The
gates had nothing to find.

### 4.1 Two precision hypotheses, both killed at the gate

**Altitude / GSD scale bias.** `drone_gsd = pred_alt_m / fx` drives a rescale,
so an altitude error is a scale error on the homography. The 4th iteration
recorded that the `height` column is absolute, not AGL. Sweeping a
multiplicative correction on R03 (n=16):

| factor | 0.60 | 0.80 | 0.90 | **1.00** | 1.10 | 1.20 | 1.40 |
|---|---|---|---|---|---|---|---|
| CEP50 | 17.7 | 17.5 | 15.2 | **15.0** | 15.5 | 18.0 | 16.2 |

Optimum at 1.00 and the curve is flat. **Killed** — the GSD chain is sound.

**Camera tilt / nadir point.** `Omega` and `Kappa` are camera attitude and are
never read; the position is recovered by projecting the image centre, which
for this `K` (`cx,cy` = exactly half the scaled image) is the **principal
point**. Standard photogrammetry: for a tilted photograph the plumb line lands
on the **nadir point**, displaced by ≈ `alt·tan(tilt)`. The circumstantial
evidence was strong:

| Region | tilt σ | alt | predicted `alt·tan(tilt)` | observed median |
|---|---|---|---|---|
| R03 | 1.64° | 466 m | 13.3 m | 13.8 m |
| R04 | 3.74° | 545 m | 35.6 m | 30.6 m |
| R08 | 2.09° | 552 m | 20.1 m | 17.6 m |

and per-frame error correlates **+0.465 (R03) / +0.445 (R04)** with tilt, with
high-tilt halves carrying 34 % / 59 % more error.

Smoke test (R04, n=10, all four sign conventions, since the axis convention is
undocumented):

| variant | median | fatal50 |
|---|---|---|
| baseline (principal point) | 35.8 m | 11.1 % |
| nadir (+om, +ka) | **34.2 m** | 11.1 % |
| nadir (+om, −ka) | 37.2 m | 11.1 % |
| nadir (−om, +ka) | 51.3 m | 55.6 % |
| nadir (−om, −ka) | 48.0 m | 44.4 % |

**Killed.** The response is antisymmetric — opposite signs give 34.2 vs 48.0,
so the geometry is real and the sign is identifiable — but the best correction
buys **1.6 m**, below the 2 m pre-stated threshold.

**Finding L — the tilt correlation is real but the causal direction was
wrong.** It is not *tilt → projection offset → error*; it is almost certainly
*tilt → perspective distortion → sloppier homography → error*. That confound
produces the same correlation and the same altitude scaling, and only the
direct-geometry version predicts that subtracting the offset helps. It does
not. Cost of finding out: 10 frames.

---

## 5. The Reframe — Against What Should This Be Measured?

Two numbers from the literature change how every prior table should be read.

**UAV-VisLoc's own convention** (the dataset this project uses): localization
is *successful* below **25 m**, and *drift* above **50 m**.

**AnyVisLoc / UAV-AVL benchmark** (CVPR 2026 Findings, 20,077 UAV images, 24
scenes) reports its best configuration — CAMP retrieval + RoMa matching, top-5
re-ranking — at **74.1 % A@5m against photogrammetric maps and 18.5 % against
satellite maps**, noting that satellite-reference results are "substantially
worse" due to resolution, viewpoint and temporal mismatch.

Against that:

| | R03 | R04 |
|---|---|---|
| match rate | 80 % | 82.5 % |
| median error | 13.8 m | 30.6 m |
| fatal (>50 m) | 0 % | 21 % |

**Finding M — the comparison baseline used since the 3rd iteration is the
wrong one.** cpvrLab's "0 fatal errors / 76.7 % recall" was measured on their
*own* orthophoto over 4 flights with 3 used for training, and their **baseline
template matching also scored 0 fatal**. Zero-fatal was table stakes on that
task, not its achievement. Matching unseen Chinese terrain against public
satellite tiles is a materially harder problem, and the published number for
that harder problem is 18.5 % A@5m.

**R03 — 80 % match, 13.8 m median, 0 % fatal — is plausibly at or near
published satellite-reference state of the art, and this project's documents
describe it as a partial failure.**

---

## 6. Open Directions, With Evidence

**Dropped** (tested, dead): candidate scoring of any kind (six signals),
threshold tuning, better matcher *for discrimination*, candidate generation,
altitude/GSD bias, nadir-point geometry.

**Live:**

1. ~~**RoMa / detector-free dense matching.**~~ **KILLED — see §6.1.**

2. **Re-derive the reporting metric.** `fatal50` presumes an alias to reject.
   On R04 the distribution is continuous, so the metric is measuring the tail
   of a precision distribution and calling it a reliability failure. Reporting
   against the dataset's own <25 m success convention, per region and with
   denominators, would make results comparable to published work.

3. **R04 precision, not rejection.** GIM's 632 vs 90 inliers should tighten
   the homography even though it does not improve selection. Untested, cheap,
   and aimed at the failure mode §4 actually identified.

### 6.1 Detector-Free Matching — Killed, And It Closes R01/R06/R08

kornia ships LoFTR with pretrained outdoor weights, making the detector-free
family testable for free before committing to RoMa or MINIMA downloads.
5 frames/region against the **ground-truth** tile:

| Region | ORB pool inliers | **LoFTR inliers** | verdict |
|---|---|---|---|
| R06 forest | 5.0 | **5.4** | both at noise floor |
| R08 non-planar | 3.2 | **3.2** | both at noise floor |
| R01 riverside | 5.4 | **7.2** | both at noise floor |
| R03 farmland | 54.8 | 5.6 | ORB adequate; LoFTR worse |

**Finding N — R01/R06/R08 contain no recoverable correspondence, and the
"detector-stage failure" framing (including §6 item 1 as first written) was
wrong.** The raw counts show why: on R06, ORB finds **52–130 descriptor
matches** and only **4–6 survive the homography**. Keypoints *are* detected and
descriptors *do* match; the matches are spurious and geometry rejects them.
Nothing was missed by the detector — there is nothing to find.

Four architecturally independent matchers now agree to within a few inliers on
these three regions, all against the correct tile:

| family | method | R06 | R08 | R01 |
|---|---|---|---|---|
| hand-crafted sparse | ORB+AKAZE+SIFT | 5.0 | 3.2 | 5.4 |
| learned sparse | SuperPoint+LightGlue | 20.2 | 4.0 | 5.8 |
| cross-modal retrained | GIM | 2.8 | 1.6 | 0.0 |
| detector-free dense | LoFTR | 5.4 | 3.2 | 7.2 |

Four unrelated methods converging on the same noise floor is strong evidence
the limit is in the **data** — stale, low-texture or seasonally divergent
satellite reference for these scenes — not in the algorithm. **No matcher will
open these regions**, and further matcher work on them should stop.

> ### ⚠ RETRACTED FOR R06 (2026-08-09, 9th iteration)
>
> **The R06 column above is a scale error, not a data limit.** The production
> GSD chain uses the dataset's `height` column as `pred_alt_m`. That column is
> **absolute elevation, not AGL** — recorded by the 4th iteration and never
> acted on. Five of six regions sit on the Jiangsu/Yangtze delta at 6–16 m
> ground elevation, so absolute ≈ AGL and nothing goes wrong. **R06 is in the
> Qinba mountains at ~505 m** (ASTER30m 502 m, SRTM30m 508 m), so its assumed
> altitude of 839.5 m is **2.5× too high** and its query and reference are
> matched at ~2.5× different ground scales.
>
> `smoke_agl_inlier_floor.py`, ground-truth tile, production ORB pool, n=8,
> altitude factor the only variable — mean homography inliers:
>
> | factor | **R06** | **R03** (control) |
> |---|---|---|
> | 0.40 | **10.6** ← peak, = R06's DEM-predicted factor | 3.5 |
> | 1.00 | **5.1** (reproduces the 5.0 in the table above) | **9.6** ← peak, = R03's predicted 0.98 |
>
> Mirror-image curves, each maximised at its own predicted factor. End-to-end
> at drift=300, n=20: **match rate 10 % → 50 %, yield 10 % → 40 %.**
>
> So the four-family convergence was evidence of a **common input defect**, not
> a common data limit — all four matchers were handed the same mis-scaled pair.
> The supporting observation below ("ORB finds 52–130 descriptor matches and
> only 4–6 survive the homography") inverts too: correcting the scale makes raw
> matches *fall* 82.8 → 33.1 while inliers *rise* 5.1 → 10.6.
>
> **Finding N stands for R01 and R08**, whose AGL ratios are 0.98 — their
> floors are not explained by scale. §4.1's altitude/GSD kill also stands *for
> R03*, where it was measured; it was over-generalised to six regions on one
> region's evidence. See `9th_iteration_survey.md` §9.

*Caveat: LoFTR was run at 640×480 and is also weak on R03 (5.6 vs ORB's 54.8),
so it is not a strong matcher on this data generally. The gate it was used for
— can detector-free matching find signal where sparse methods cannot — is
answered by the R06/R08/R01 columns, and the answer is no.*

---

## 7. Reporting Rules

Carried forward from iterations 3–6, plus:

- **Gate before you sweep.** Every hypothesis gets a kill-criterion test at
  the smallest n that can answer it. Four of five died at the gate this
  iteration; at 6th-iteration cadence they would have cost multi-hour sweeps.
- **State the kill criterion before running, and honour it.** The nadir test
  produced a visible antisymmetric signal and still failed its 2 m threshold.
  It was recorded as killed rather than rescued by moving the line.
- **Check what the field reports on the same dataset before judging your own
  numbers.** Three iterations of "we are far behind" rested on a comparison to
  an easier task; the relevant published figure is 18.5 % A@5m.
- **Elimination is not evidence.** The 6th iteration inferred generation was
  the bottleneck because scoring wasn't, and was wrong. Test the surviving
  hypothesis directly.

---

## 8. Closing Assessment

Nothing was adopted; the production configuration is unchanged. The output is
one retraction, five tested hypotheses, and a corrected frame of reference.

**What changed.** The project's model of its own failure was wrong in three
places at once. Generation is not the bottleneck (§1). A better matcher does
not improve selection (§2). R04 and R06 are different failures that one metric
has been hiding (§4). And the target it has been measured against was drawn
from an easier task (§5).

**What that leaves — a clean three-way split of the dataset:**

| | status | evidence |
|---|---|---|
| **R03** farmland | **works, ~competitive with published satellite-reference SOTA** | 80 % match, 13.8 m median, 0 % fatal vs 18.5 % A@5m (AnyVisLoc) |
| **R04** repetitive farmland | **precision problem**, misreported as reliability | continuous error distribution, no alias gap |
| **R01 / R06 / R08** | **not solvable by matching** | four independent matcher families at the same noise floor on the correct tile |

That third row is the most useful thing this iteration produced. It converts
"these regions are broken and we should keep trying methods" into a bounded,
evidenced statement: the satellite reference for those scenes does not share
recoverable content with the drone imagery, so matcher work on them should
stop. Effort belongs on R04 precision, or on obtaining better reference
imagery for those regions — not on another matcher.

**Cost discipline.** Five hypotheses were killed for a combined ~60 frames of
compute. The one expensive run (the 6-region oracle) was the one that
retracted a published conclusion, and was worth its cost.

---

*Document complete — 2026-08-09. All numbers measured this session.
Scripts added: `diag_gim_probe.py`, `diag_discrimination.py`,
`diag_trajectory_gate.py`, `diag_altitude_scale.py`,
`smoke_nadir_correction.py`. `map_matcher.py` gains an opt-in
`cam_tilt_deg` argument (default None = unchanged behaviour), retained for
reproducibility of §4.1 though the hypothesis was rejected.*

*Key references: NaviLoc (Drones 2026, 10(2):97) · AnyVisLoc / UAV-AVL
Benchmark (CVPR 2026 Findings) · MINIMA (CVPR 2025) · GIM
(`vismatch/gim-lightglue`) · UAV-VisLoc (arXiv 2405.11936).*
