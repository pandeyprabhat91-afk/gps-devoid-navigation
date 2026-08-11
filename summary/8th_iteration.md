# GPS-Denied UAV Navigation — 8th Iteration

**Project:** MTech Final Year Project, IIT Madras
**Date:** 2026-08-09
**Status:** Both directions left live by the 7th iteration are now closed. Two
hypotheses tested, both killed on their pre-stated criteria, and the kills
produced the two most consequential measurements in the project: an **oracle
precision ceiling** per region, and the reason `min_inliers=10` has survived
four independent attempts to move it. **No code adopted.** Production
configuration unchanged.

> **Method note.** Same rule as the 7th iteration: gate before you sweep, state
> the kill criterion before running, honour it. Both gates here were stated in
> the script docstring before execution and both were failed. The findings come
> from *why* they failed, not from rescuing them.

---

## 0. Headline

| | |
|---|---|
| Directions left live by 7th iteration | **both closed** |
| Homography position vs correspondence count | **saturates** — 7.4× more inliers moves the fix **0.17 m** |
| R03 production A@5m, re-derived on the comparable metric | **7.5 %** (vs AnyVisLoc 18.5 %) |
| **R03 oracle ceiling** (correct tile, saturated inliers) | **14.3 % A@5m · 92.9 % A@25m · 11.9 m** |
| **R04 oracle ceiling** (correct tile, saturated inliers) | **0.0 % A@5m · 12.5 % A@25m · 40.8 m** |
| Constant georeferencing offset | **none** — error is scattered, not displaced |
| Consequence | **R04 joins R01/R06/R08 as closed to matcher work**, for a different reason |

---

## 1. Re-Derived Metrics — The Comparison The 7th Iteration Called For

The 7th iteration (§6, item 2) identified that `fatal50` presumes an alias to
reject, and that on R04 — whose error distribution is continuous — it measures
the tail of a precision distribution and names it a reliability failure. It
called for re-derivation against the dataset's own convention. Done here, from
the persisted per-frame CSVs, with no matching re-run.

`scripts/rederive_metrics.py`. Adopted config (`multi_feature=True,
ncc_verify=0.30`), drift = 300 m, n = 40 attempted per region.

Two things change. First, **the denominator**: AnyVisLoc reports A@Xm over all
query images, so a no-match is a failure rather than an excluded sample. This
project has always divided by matched frames. Second, **the threshold**:
UAV-VisLoc's own convention is success < 25 m, drift > 50 m.

| Region | matched/attempted | A@5m | A@10m | A@25m | A@25m ǀ matched | median ǀ matched | >50 m ǀ matched |
|---|---|---|---|---|---|---|---|
| R01 riverside | 0/40 | 0.0 | 0.0 | 0.0 | — | — | — |
| **R03 farmland** | 32/40 | **7.5** | **20.0** | **65.0** | 81.2 | **13.2 m** | **0 % (0/32)** |
| R04 repetitive | 33/40 | 2.5 | 5.0 | 27.5 | 33.3 | 32.9 m | 21 % (7/33) |
| R06 forest | 4/40 | 0.0 | 0.0 | 5.0 | 50.0 | 28.1 m | 25 % (1/4) |
| R08 non-planar | 3/40 | 0.0 | 0.0 | 7.5 | 100.0 | 18.3 m | 0 % (0/3) |
| R09 suburban | 2/40 | 0.0 | 0.0 | 2.5 | 50.0 | 38.8 m | 50 % (1/2) |
| **pooled** | **74/240** | **1.7** | **4.2** | **17.9** | 58.1 | 21.2 m | 12 % (9/74) |

Every per-region reliability figure now carries its denominator inline, which
is the 6th iteration's own rule (§8) and had never been applied to a table.
Read that way, R08's "0 % fatal" is `0/3` and R09's "50 %" is `1/2` — neither
can carry any decision, exactly as the 6th iteration warned.

Across drifts, the adopted config's pooled A@25m is 18.3 % (150 m), 17.9 %
(300 m), 12.5 % (600 m). **R03's A@5m is 7.5 % at all three drifts** — the same
three frames each time. Sub-5 m accuracy is drift-independent, which already
hints that whatever limits it is not the prior.

**Finding O — the 7th iteration's Finding M compared two different metrics.**
It set R03's *match rate* (80 %) and *median* (13.8 m) beside AnyVisLoc's
*18.5 % A@5m* and concluded R03 was "plausibly at or near published
satellite-reference state of the art". On the comparable metric R03 scores
**7.5 % A@5m** — under half the published figure. The 7th iteration was right
that the *cpvrLab* comparison was the wrong baseline and right to go looking
for the field's number; it then made a version of the same mistake it was
correcting. The corrected statement is in §4, and it is more interesting than
either.

*What survives from Finding M intact:* R03 at **65 % A@25m over attempted
frames, 0 drift in 32 accepted fixes** is a genuinely strong result under the
dataset's own success convention, and no prior document has reported it.

---

## 2. GIM Precision — Killed, And It Explains Four Prior Results

7th §6 item 3: GIM's 632 inliers vs the ORB pool's 90 on R04 "should tighten
the homography even though it does not improve selection. Untested, cheap, and
aimed at the failure mode §4 actually identified."

`scripts/smoke_gim_precision.py`. Both matchers run against the **ground-truth
tile**, so selection is removed and the only variable is which correspondence
set the homography is fitted to. Position recovered with the production `H_inv`
method, so the numbers sit beside the per-frame CSVs without a cross-harness
caveat. Comparison is **paired** — same frames only — so neither matcher can
look better by failing to solve on hard frames.

**Kill criterion, stated before running:** ≥ 5.0 m paired median improvement on
R04.

| Region | ORB pool | GIM | paired median | verdict |
|---|---|---|---|---|
| R04 | 15/15 solved, 108 mean inliers | 12/15 solved, **525** mean inliers | 26.7 → 24.1 m | **KILLED** (+2.6 m) |
| R03 (control) | 15/15 solved, 74 mean inliers | 10/15 solved, **478** mean inliers | 20.2 → 20.4 m | **KILLED** (−0.2 m) |

The +2.6 m on R04 is one frame: ORB solved it on 6 inliers and landed 743 m
out. Excluding it, GIM is a wash.

### 2.1 What the per-frame data actually shows

`scripts/analyze_inlier_saturation.py`, over the 22 frames where both matchers
solved:

| weaker matcher's inliers | n | median ǀerr_GIM − err_ORBǀ | max | median inlier ratio |
|---|---|---|---|---|
| 0–10 | 4 | **444.93 m** | 734.26 m | 26.9× |
| 10–20 | 3 | **0.31 m** | 1.29 m | 35.9× |
| 20–50 | 4 | **0.54 m** | 5.39 m | 20.0× |
| 50+ | 11 | **0.15 m** | 0.58 m | 3.4× |

On the 17 frames where both cleared 15 inliers: **median disagreement 0.17 m at
a median 7.4× inlier ratio, while both sit a median 23.5 m from ground truth.**

**Finding P — the homography saturates at approximately the existing
`min_inliers` threshold, and above it correspondence count carries no position
information whatsoever.** Below ~10 inliers the fit is degenerate and error is
in the hundreds of metres. Above ~15 it is fully determined: adding 500 further
correspondences from an architecturally unrelated matcher moves the recovered
position by less than a fifth of a metre.

This retro-explains four prior results with one mechanism:

- **`min_inliers=10` re-confirmed optimal in the 3rd, 4th and 6th iterations**,
  each time by a different route. It sits exactly at the saturation knee — the
  lowest value that is not degenerate.
- **6th-iteration Finding F** — "CEP50 is flat to within 0.7 m across an 8×
  threshold range". It is flat because the axis is saturated over that entire
  range.
- **6th-iteration Finding C** — inlier count ranks slightly *backwards* within
  the correct tile. At saturation the residual differences are noise, so a
  ranking on them is a coin flip that happened to land backwards.
- **7th-iteration Finding L** — the tilt correlation was attributed to "tilt →
  perspective distortion → sloppier homography → error". Saturation rules that
  out: the homography is not sloppy. Two unrelated matchers agree to 0.17 m.
  Whatever tilt does, it does not do it by degrading the fit.

**The 23.5 m is common-mode.** Two independent matchers do not converge to
within 0.17 m of each other and land 23.5 m from truth independently. The error
is not in the estimator.

---

## 3. Is The Common-Mode Error A Constant Offset? — No

If the residual is shared by both estimators, the obvious candidate is a
registration offset between the drone GPS ground truth and the satellite tile
raster. That predicts a per-region offset *vector* consistent across frames.

`scripts/smoke_georef_bias.py`, ground-truth tile, ORB pool only (Finding P
says the matcher choice cannot matter above the knee), frames filtered to
≥ 15 inliers.

**The trap and the guard.** A per-region constant offset has two free
parameters; fitting and evaluating it on the same frames always reduces median
error and proves nothing. The offset is therefore fitted on one half of the
frames and applied to the **other** half, halves swapped, both directions
reported. Only cross-validated improvement counts.

**Kill criterion, stated before running:** ≥ 5.0 m cross-validated median
reduction on R03 or R04.

| Region | n | median offset | spread about it | shape | cross-validated |
|---|---|---|---|---|---|
| R03 | 14 | N −1.5 m, E +4.4 m (‖4.7 m‖) | **11.4 m** | **scattered** | 11.9 → 16.7 m (**−4.8 m**) |
| R04 | 16 | N −15.9 m, E +2.7 m (‖16.2 m‖) | **41.5 m** | **scattered** | 40.8 → 40.6 m (+0.3 m) |

**KILLED.** The diagnostic is cleaner than the gate: in both regions the
**spread of the offsets about their own median exceeds the median's
magnitude**. The error is scattered, not displaced. Cross-validation confirms
it — on R03, applying a half-fitted offset made held-out frames *worse* by
4.8 m, the signature of fitting noise.

**Finding Q — the residual is common-mode per frame but not constant across
frames.** Both matchers agree to 0.17 m on any given frame, and where they
jointly land varies by tens of metres between frames. So the error is
deterministic given the image pair and specific to it: the drone image genuinely
registers best to a point some tens of metres from where the GPS record says it
was taken.

That narrows the remaining causes to ones that are frame-specific and shared by
any matcher looking at the same two images — dataset GPS ground-truth error,
local terrain relief under a flat-ground homography, or local warp in the tile
raster. None of these is an algorithm defect, and the first is not even a system
defect. Distinguishing them needs a DEM or better ground truth, neither of which
this project's data provides.

---

## 4. The Oracle Precision Ceiling — The Number The Thesis Needs

Combining §2 and §3: against the **correct tile**, with **saturated
correspondences**, and therefore with **zero selection error and zero fit
noise**, what accuracy is available at all?

| Region | n | **A@5m** | **A@10m** | **A@25m** | median |
|---|---|---|---|---|---|
| **R03** | 14 | **14.3 %** | 28.6 % | **92.9 %** | **11.9 m** |
| **R04** | 16 | **0.0 %** | 0.0 % | **12.5 %** | **40.8 m** |

**Finding R — every region has a hard precision ceiling that no amount of
matching, selection, or retrieval work can pass.**

**R03.** Ceiling 14.3 % A@5m against AnyVisLoc's 18.5 %; production delivers
7.5 %. So R03 is at roughly **half its own ceiling**, and its ceiling is a
little below published satellite-reference SOTA. There is real headroom on R03
— about 7 points of A@5m — and it lives in selection and coverage, which is
where the project's remaining levers actually are. Under the dataset's own
convention the ceiling is **92.9 % A@25m** and production delivers 65 %.

**R04.** Ceiling **0.0 % A@5m and 12.5 % A@25m**. Handed the correct tile and
100–700 correspondences, R04 does not produce a single sub-5 m fix in 16 frames,
and fails the dataset's own 25 m success convention on 7 of 8. R04's production
median of 32.9 m is already close to its oracle median of 40.8 m — the
production pipeline is not underperforming on R04, it is near the best the data
allows.

**This closes R04 to matcher work**, and closes it for a *different reason*
than R01/R06/R08. Those three were closed by the 7th iteration because four
matcher families converge on a 3–7 inlier noise floor against the correct tile —
there is no correspondence to find. R04 has correspondence in abundance; what it
lacks is agreement between where that correspondence points and where the GPS
record says the drone was.

### 4.1 The dataset, four ways

| | status | evidence | remaining lever |
|---|---|---|---|
| **R03** farmland | **works; at ~half its own ceiling** | 65 % A@25m production vs 92.9 % oracle; 7.5 % vs 14.3 % A@5m | selection & coverage — the gap is real |
| **R04** repetitive farmland | **at its precision ceiling** | oracle 0 % A@5m, 12.5 % A@25m, 40.8 m median | none in matching; needs better ground truth or a relief model |
| **R01 / R06 / R08** | **no recoverable correspondence** | four matcher families at the same 3–7 inlier noise floor (7th §6.1) | none; needs better reference imagery |
| **R09** suburban | **undetermined** | 2/40 matched — no denominator supports any claim | measure before theorising |

The 7th iteration's three-way split gains a row and loses its most optimistic
one. R04 was listed as "precision problem, misreported as reliability" with the
implication that the precision was addressable. It is not addressable by
anything in the matching pipeline.

---

## 5. What Is Now Closed, And What Is Not

**Closed with evidence** (do not re-open without new data):

- Candidate scoring — six signals (3rd–6th iterations).
- Candidate generation — oracle test, 1.2 points (7th §1).
- Better matchers for *discrimination* — GIM, 7× inliers, zero gain (7th §2).
- Better matchers for *precision* — GIM, 7× inliers, 0.17 m (this iteration §2).
- Threshold tuning on `min_inliers` — now explained, not merely measured (§2.1).
- Altitude/GSD scale bias (7th §4.1); nadir-point geometry (7th §4.1).
- Constant georeferencing offset (§3).
- R01/R06/R08 by any matcher (7th §6.1); **R04 by any matcher** (§4).

**Not closed:**

1. **R03 coverage and selection.** The one region with measured headroom:
   65 % → 92.9 % A@25m, 7.5 % → 14.3 % A@5m. Whatever is dropping 8 of 40 R03
   frames, and whatever selects a suboptimal position on the rest, is worth
   roughly double the current performance on this region. This is now the
   project's only live *engineering* direction.
2. **R09 has never been measured.** Every R09 statement across five iterations
   rests on 0–2 accepted fixes. It is neither working nor broken; it is
   unmeasured. Cheap to fix and it currently occupies a row in every table on
   no evidence.
3. **What the frame-specific common-mode offset actually is** (§3). Needs a DEM
   or better ground truth. This is a *data acquisition* question, not an
   algorithm question, and it is the honest answer to "why can't this get below
   ~12 m".

---

## 6. Reporting Rules

Carried forward from iterations 3–7, plus:

- **Report the metric the field reports, on the denominator the field uses.**
  Finding O: the 7th iteration correctly identified that the comparison
  baseline was wrong, then compared a match rate against an A@5m figure. Fixing
  the baseline and fixing the metric are two separate jobs.
- **Cross-validate any correction with free parameters.** The georeferencing
  offset (§3) would have shown a 4–5 m in-fold "improvement" on both regions and
  been adopted. Held out, it made R03 worse by 4.8 m. Any fitted correction gets
  split-half treatment before it gets a verdict.
- **Measure the ceiling before optimising toward it.** Four iterations of work
  on R04 preceded the twenty minutes that established R04 cannot reach the
  dataset's own success threshold on 7 of 8 frames even under oracle conditions.
  An oracle-condition measurement is cheap and bounds every downstream effort.

---

## 7. Closing Assessment

Nothing was adopted; the production configuration is unchanged. Both gates
failed. The value is entirely in the mechanism the failures exposed.

**What changed.** The project has spent six iterations treating its error as
something an algorithm could reduce — better gates, better matchers, better
retrieval, better thresholds. Finding P shows the estimator is already exact:
two unrelated matchers, one with seven times the evidence, agree on the answer
to within 0.17 m. Finding Q shows the disagreement with ground truth is
deterministic per frame and not a constant that can be calibrated away. Finding
R puts a number on what that costs: R03 can reach 14.3 % A@5m and no more, R04
can reach 0 %.

**The honest headline for the thesis**, updated from the 6th iteration's
version and now resting on measurement rather than elimination:

> *Prior-conditioned map matching against public satellite tiles is limited by
> the reference data, not by the matching. The homography saturates at ~15
> correspondences; beyond that, position error is a property of the
> drone/satellite image pair. Per-region oracle ceilings (R03: 14.3 % A@5m,
> 92.9 % A@25m; R04: 0 % A@5m) bound what any matcher, retriever or gate can
> achieve on this dataset.*

That is a stronger claim than the 6th iteration's, because a ceiling is a
measurement and an exhaustion argument is not — and the 7th iteration was
retracted precisely for reasoning by elimination.

**Cost discipline.** Two gates, ~60 frames of matching, plus one zero-compute
re-derivation from data already on disk. The re-derivation produced Finding O
and cost nothing but the reading of a CSV.

---

*Document complete — 2026-08-09. All numbers measured this session against the
production `MapMatcher` position-recovery path. Scripts added:
`rederive_metrics.py`, `smoke_gim_precision.py`, `analyze_inlier_saturation.py`,
`smoke_georef_bias.py`. Artefacts: `results/rederived_metrics.json`,
`results/gim_precision_R{03,04}.json`, `results/georef_bias.json`.*

*Data note: `results/comprehensive/adopted_M4_mf+ncc0.30_R03_d300.csv` holds
only 6 frames — it was overwritten by a partial run at some point after the 5th
iteration. §1 therefore reads R03 from the 6th iteration's `repro_` set, which
holds the full n=40 and is documented in 6th §1 as reproducing the shipped
config exactly. `rederive_metrics.py` selects sources automatically and warns
on any cell below n=40.*

*Key references: AnyVisLoc / UAV-AVL Benchmark (CVPR 2026 Findings) ·
UAV-VisLoc (arXiv 2405.11936) · GIM (`vismatch/gim-lightglue`).*
