# GPS-Denied UAV Navigation — 10th Iteration: Implementation

**Project:** MTech Final Year Project, IIT Madras
**Date:** 2026-08-09
**Status:** Implementation pass. Three steps chosen by measured probability of
success, executed in sequence. **Step 1 adopted — the first production config
change since the 5th iteration.** **Step 2 revises 7th-iteration Finding K.**
Step 3 in progress.

### Headline

| | |
|---|---|
| Step 1 — AGL correction | **ADOPTED** |
| R06 matched fixes | **4/40 → 21/40**; good fixes **3 → 14** |
| Pooled A@25m over attempted frames | **17.9 % → 22.5 %** |
| Pooled A@5m / A@10m | 1.7 → **2.5 %** / 4.2 → **5.8 %** |
| Trade | **+14 good fixes for +5 bad** (2.8:1) |
| Step 2 — R04's residual | **sub-tile aliasing, not imprecision** (revises Finding K) |
| Legacy path | verified byte-equivalent (`dem=None`) |

> **Why these three.** The 9th iteration produced a large survey (§1–8, §10) and
> one measured result (§9). Rather than work down the survey's novelty ranking,
> the steps here are ordered by *evidence already in hand*:
>
> 1. **AGL correction** — already demonstrated on R06 (GT-tile inliers 5.1 →
>    10.6, peak exactly at the DEM-predicted factor; end-to-end match 10 % →
>    50 %). Not a hypothesis; a confirmed defect with a measured fix.
> 2. **R04 error-direction analysis** — zero compute, resolves an open question
>    from existing persisted data.
> 3. **N-frame sequential consistency** — cheap, and aimed at the tail that
>    Step 1 makes worse on R06.
>
> Sensor stack is fixed: barometer, IMUs, global-shutter camera, RDK X5. Every
> step here respects that — a DEM is offline map data, not a sensor, and all
> three run on CPU.

---

## Step 1 — AGL Correction (implemented, validation running)

### 1.1 What was wrong

`MapMatcher` derives ground sample distance from

```python
drone_gsd = pred_alt_m / fx
gsd_ratio = drone_gsd / tile_ground_resolution(...)
```

`pred_alt_m` traces to the dataset's `height` column, which the 4th iteration
established is **absolute elevation, not AGL**, and then discarded as
unusable. Five of six regions sit on the Jiangsu/Yangtze delta at 6–16 m ground
elevation, so absolute is AGL to within 2–3 % and nothing goes wrong. R06 is in
the Qinba mountains. Full detail and the confirming experiment are in
`9th_iteration_survey.md` §9.

### 1.2 What was built

**`scripts/build_dem_cache.py`** — fetches a ground-elevation grid per region
from OpenTopoData (ASTER GDEM v3, 30 m), 500 m spacing, track bounding box plus
a 3 km margin that covers the largest drift tested (600 m) plus the search
radius. Respects the public API's 100-locations/call and 1 call/second limits,
checkpoints after each region.

Built grids:

| Region | grid | elevation range | mean |
|---|---|---|---|
| R01 | 28×17 | 5–82 m | 17 |
| R03 | 27×30 | 0–32 m | 9 |
| R04 | 35×21 | 0–36 m | 8 |
| **R06** | 21×18 | **444–940 m** | **596** |
| R08 | 22×35 | 0–24 m | 5 |
| R09 | 32×35 | 0–451 m | 26 |

**R06 spans 444–940 m within its own flyable area.** A per-region constant
elevation would have been wrong by up to ±250 m; the grid was necessary, not
decorative.

**`kp_vio/map_matching/dem.py`** — `DEMGrid` with bilinear sampling and edge
clamping, plus `agl()` with a 20 m floor guarding the degenerate case where a
bad prior in steep terrain puts the reported altitude at or below the sampled
terrain (which would otherwise drive the GSD to zero and take the rescale with
it).

**`MapMatcher(dem=...)`** — new optional argument. When `None` the legacy path
is unchanged. When supplied, the GSD chain uses AGL.

**The sampling contract matters.** The DEM is sampled at the **prior (drifted)
position**, never at ground truth. At match time the true position is unknown,
and sampling at ground truth would be exactly the "number measured with the
prior set to ground truth" the project has forbidden since the 3rd iteration.
This is why a *grid* was built rather than a per-frame elevation keyed by
filename — the grid can be sampled anywhere, including at a prior that is
hundreds of metres off. Terrain varies slowly relative to the drift magnitudes,
so a prior a few hundred metres out still yields a usable elevation.

**`comprehensive_scene_test.py --dem`** — plumbing, default off.

### 1.3 Validation

6 regions × drift 300 m × n=40, adopted config (`multi_feature=True,
ncc_verify=0.30`), with and without `--dem`, run back-to-back in one session as
a paired comparison — no cross-harness or cross-session quoting.

**Prediction stated before the run:** large gain on R06, a worse R06 tail (more
coverage on a genuinely aliasing-prone region admits more aliases), essentially
no change on R01/R03/R04/R08 (AGL ratios 0.97–0.98), small change on R09 (0.89).

**Legacy identity confirmed first.** The no-DEM arm reproduces the 6th-iteration
`repro_` numbers exactly — R03 80.0 % / 13.2 m / 0 % fatal, R04 82.5 % / 32.9 m
/ 21.2 %, R06 10.0 % / 28.1 m / 25.0 %, R08 7.5 % / 18.3 m / 0 %, R09 5.0 % /
38.8 m / 50 %, aggregate 30.8 %. The `dem=None` path is unchanged.

### 1.4 Per-region result

Denominators inline, per the 6th iteration's rule.

| Region | AGL ratio | no-DEM | **with-DEM** | good fixes (≤50 m) |
|---|---|---|---|---|
| R01 riverside | 0.98 | 0/40 | 1/40 · 4.5 m · 0 fatal | 0 → 1 |
| R03 farmland | 0.98 | 32/40 · 13.2 m · 0/32 | **34/40** · 13.9 m · 0/34 | 32 → 34 |
| R04 repetitive | 0.97 | 33/40 · 32.9 m · 7/33 | **34/40** · **30.9 m** · 7/34 | 26 → 27 |
| **R06 mountain/forest** | **0.40** | 4/40 · 28.1 m · 1/4 | **21/40** · **23.3 m** · 7/21 | **3 → 14** |
| R08 non-planar | 0.98 | 3/40 · 18.3 m · 0/3 | 2/40 · 20.0 m · 0/2 | 3 → 2 |
| R09 suburban | 0.89 | 2/40 · 38.8 m · 1/2 | 1/40 · 21.7 m · 0/1 | 1 → 1 |

The prediction held on every row. R01, R08 and R09 each move by **exactly one
frame** — that is noise, not signal, and none of it can carry a decision.
R03 and R04 both improve slightly and in the right direction, which is what a
2–3 % scale correction should do. **R06 is the result: 4 → 21 matched, 3 → 14
good fixes, median 28.1 → 23.3 m.**

### 1.5 Pooled, on the comparable metric

The 8th iteration established that `fatal50` and `CEP50` divide by *matched*
frames, so they move when the system answers more often. Accuracy-at-threshold
over *attempted* frames has a fixed denominator and is what published work
reports. Both are given.

| pooled, 240 attempted | no-DEM | **with-DEM** |
|---|---|---|
| matched | 74/240 = 30.8 % | **93/240 = 38.8 %** |
| **A@5m** (attempted) | 1.7 % | **2.5 %** |
| **A@10m** | 4.2 % | **5.8 %** |
| **A@25m** | 17.9 % | **22.5 %** |
| median (matched) | 21.5 m | 21.7 m |
| >50 m (matched) | 9/74 = 12.2 % | 14/93 = 15.1 % |

**Every fixed-denominator metric improves**: A@5m +0.8, A@10m +1.6, A@25m +4.6
points, all over the same 240 attempted frames with a no-match counting as
failure in both arms. In absolute counts the correction buys **14 more good
fixes for 5 more bad ones** — a 2.8:1 ratio.

The `fatal50` rise from 12.2 % to 15.1 % is a denominator effect: the system
answers 26 % more often, and the extra answers are concentrated on R06, which
7th-iteration Finding K showed is genuinely bimodal. R06's previous 25 % fatal
was 1 wrong fix out of 4 — "not fatal because not answering". That is the same
mechanism the 3rd iteration documented at 600 m drift and the 6th iteration
documented at `min_inliers=80`: the system stops answering, so it stops
answering wrongly.

### 1.6 Adoption

**Adopted.** This is a defect fix, not a tuning knob. The GSD was factually
wrong on R06 by a factor of 2.5, verified against two independent DEMs and
confirmed by a controlled paired experiment whose peak landed exactly on the
DEM-predicted factor. Declining it because it exposes R06's pre-existing
aliasing would be preferring a system that stays silent to one that answers and
is sometimes wrong — and the project's own architecture (map matching as loop
closure into an estimator that can gate) is built to absorb exactly that, which
is what Step 3 addresses.

**Recommended production config becomes** `multi_feature=True, ncc_verify=0.30,
min_inliers=10, early_exit=True, select_by="inliers", dem=<region grid>`.

**Caveats carried forward.** R06's tail is now the project's largest single
source of fatal fixes (7 of 14 pooled). The DEM is 30 m ASTER; a finer DSM would
sample terrain better in the Qinba mountains, where the grid spans 444–940 m.
And on the real vehicle the absolute altitude comes from the barometer rather
than a dataset column, so `AGL = baro_altitude − DEM(estimated position)` — which
needs no sensor the platform does not already have, but does inherit barometric
drift.

---

## Step 2 — R04's Residual Is Aliasing, Not Imprecision (complete)

### 2.1 The question

The 9th-iteration survey left R04 with two mechanisms and no way to choose:

- **Relief displacement** — a point at height `h` above the fitted plane, seen
  at off-nadir ray angle `θ`, lands `h·tan(θ)` away. With this project's `K`,
  `θ_max ≈ 41°`, so a 15 m tree line displaces 13 m at the frame corner. Every
  matcher reproduces it identically, matching 8th-iteration Finding Q's
  signature. But the arithmetic only reaches R03's 11.9 m; R04's 40.8 m would
  need ~46 m of relief, and the DEM built in Step 1 says R04's terrain spans
  0–36 m across a 16 km box, most of it flat farmland.
- **Furrow aliasing** — both matchers locking onto the same *wrong period* of
  the repetitive furrow pattern **inside the correct tile**.

They differ in what they predict about error **direction**. Relief scatters
errors according to the local height distribution. Aliasing quantises them along
one axis, with a hole near zero.

`scripts/analyze_r04_error_direction.py`, over the signed north/east offsets
already persisted in `results/georef_bias.json`. **Zero compute — no matching
re-run.**

### 2.2 Result

| | R03 (control) | **R04** |
|---|---|---|
| directional resultant `R` (360°) | 0.29 | 0.25 |
| **axial resultant `R` (180°)** | 0.27 | **0.62** |
| axis bearing | — | **171°** (N–S) |
| along-axis projections (m) | −33, −19, −8, −4, +3, +4, +5, +5, +11, +13, +14, +17, +19, +20 | −51, −41, −36, −24, −24, −22, **+8**, +14, +22, +37, +38, +40, +49, +50, +60, +69 |
| **frames within ±10 m of zero** | **6/14** | **1/16** |
| along-axis median \|·\| | 12.7 m | 38.0 m |
| perpendicular median | 6.9 m | 11.3 m |
| **anisotropy** | 1.8× | **3.4×** |

R04's errors are **axis-aligned but bidirectional** — axial `R` = 0.62 with
directional `R` = 0.25 means they go both north *and* south along the same line.
That is precisely the signature of locking one period ahead or one period
behind. And **only 1 of 16 frames lands within ±10 m of zero**: there is a hole
where a precision error would put most of its mass.

R03, by contrast, is a single blob centred near zero (6/14 within ±10 m), mildly
anisotropic, with a much smaller spread.

**Finding T — R04 has sub-tile aliasing inside the correct tile, and the 7th
iteration's "continuous, no gap" reading was an artifact of discarding the
sign.**

7th-iteration Finding K measured R04's error **magnitude** histogram, found it
continuous with no gap, and concluded: *"R04 has no aliases to reject; it has
imprecision."* A symmetric bimodal distribution at roughly ±22 m and ±40 m,
folded to absolute value, looks exactly like a continuous spread from 14 to 69 m
— which is what that histogram showed. The bimodality lives in the sign, and
taking the magnitude threw it away.

### 2.3 What this explains and what it changes

- **Why six rejection gates failed on R04.** All six were built to reject
  wrong-*tile* matches. Finding K was right that the tile is correct. What it
  missed is that being on the correct tile does not mean being at the correct
  *place on* it. The gates had nothing to find because they were looking one
  level too coarse.
- **Why 8th-iteration Finding P holds and does not help.** Both matchers agree
  to 0.17 m because both lock to the same wrong furrow. More correspondences
  cannot break a tie the imagery itself does not break.
- **Why R04's oracle ceiling was 0 % A@5m** (8th-iteration Finding R). If every
  frame is locked one or more periods off, no sub-5 m fix is reachable. **That
  ceiling is a property of the lock, not of the data** — if the lock can be
  resolved the ceiling moves. This is a weaker and more hopeful reading of
  Finding R than the 8th iteration gave.
- **It is actionable.** A sub-tile disambiguation step — evaluate candidate
  positions displaced by ±k along the estimated dominant axis, score each by
  patch NCC, keep the best — attacks the mechanism directly. Unlike the six
  failed gates it does not try to reject anything; it tries a small discrete set
  of alternatives.

### 2.4 Honest limits

- **n = 16 on R04, n = 14 on R03.** Direction-finding, not adoption-grade. The
  6th iteration's own rule (denominators inline, no decision below ~20 matched
  fixes) applies here and this is below it.
- **The period is not established.** The projections hint at clusters near ±22,
  ±40 and ±60 m, suggesting something around 20 m, but 16 samples cannot resolve
  a period. Confirming it needs the same analysis at n≈60, which is cheap.
- **The axis is estimated from the errors themselves**, not measured from the
  imagery — which is circular unless the imagery independently shows structure
  at the same orientation. That check was run and **it was inconclusive**; see
  §2.5.
- Frames come from the subset that solved with ≥15 inliers against the GT tile,
  so this describes the *good* matches. That is the correct population for this
  question, but it is not the whole distribution.

### 2.5 The corroborating imagery test failed to discriminate

`scripts/measure_furrow_axis.py` takes the FFT power spectrum of each
ground-truth tile patch, discards the DC neighbourhood and the noise band, and
finds the orientation carrying the most power. A repetitive furrow pattern of
period `p` should produce a spectral peak perpendicular to the furrows at radius
`1/p`, recovering both the axis and — unlike 16 error samples — the period.

| | R04 | R03 (control) |
|---|---|---|
| axial mean bearing | **176°** | **9°** |
| **axial resultant `R`** | **0.29** | **0.30** |
| period median | **19.8 m** (range 9.7–63.7) | 34.2 m (range 11.8–52.5) |
| peak/mean power | 9.3 | 11.1 |
| difference from Step 2's 171° error axis | **5°** | 18° |

**Read naively this looks like confirmation — 5° agreement, and a 19.8 m period
right where the error clusters (±22, ±40, ±60 m) suggested ~20 m. It is not.**

The axial resultant is **0.29**, meaning the per-frame orientation estimates are
scattered, not aligned (individual frames returned 114°, 180°, 90°, 14°, 124°…).
At that resultant the mean bearing is barely determined, so a 5° agreement is
well within what chance produces. Worse, **the R03 control also lands "within
25°"** (18° away) — so the test does not discriminate between the region that
should show the effect and the one that should not. A check that passes for both
arms has not tested anything.

The likely cause is that the measurement is too coarse: a radius-1 patch spans
~750 m of ground and contains many fields at different orientations, so "the
dominant orientation of the patch" is not a well-defined quantity.

**Recorded as inconclusive.** Step 2's conclusion rests on the error geometry
alone — the hole at zero (1/16 within ±10 m) and the 3.4× anisotropy — which are
properties of the measured offsets and do not depend on this test. A sharper
version would estimate orientation locally, over the footprint the drone frame
actually covers, at the tile pyramid's native resolution rather than on a
downsampled composite patch.

---

## Step 3 — Sequential Consistency: Killed, And It Closes A Whole Family

### 3.1 What was tested

Rationale in `9th_iteration_survey.md` §10.3. Original ORB-SLAM would not accept
a loop candidate unless it was consistent across three consecutive keyframes;
ORB-SLAM3 replaced that with covisibility verification and reports the change
*raises* recall. This project accepts or rejects every frame alone and has never
required corroboration between neighbours.

This is **not** the 3rd iteration's rejected temporal gate (S9), which compared a
match against a **VIO prediction** and was killed for over-rejecting. This
compares accepted matches against **each other**, so it does not require the VIO
to be trustworthy — which matters because at 7-second frame spacing it is not.

`scripts/sweep_sequential_consistency.py`. A fix survives only if at least one
other accepted fix within ±`window` frames agrees with it to within `tol` metres
*after compensating for the motion flown between them*. The expected displacement
comes from the **prior** positions, not ground truth — a real system has the
prior, and its frame-to-frame delta is dominated by real motion because the drift
model's random-walk increment over a few frames is small next to the distance
flown.

R04 and R06 at drift = 300 m, n = 40, with the Step 1 AGL correction active.
Baseline: **55 fixes, 41 good, 14 fatal.**

**Kill criterion, stated before running:** cut fatal fixes by ≥25 % relative
while retaining ≥80 % of good fixes.

### 3.2 Result

| window | tol | good kept | fatal kept | **ratio** |
|---|---|---|---|---|
| 1 | 30 m | 15 % | 29 % | **0.51** |
| 1 | 60 m | 49 % | 71 % | **0.68** |
| 1 | 100 m | 83 % | **100 %** | **0.83** |
| 2 | 30 m | 17 % | 29 % | **0.60** |
| 2 | 60 m | 68 % | 71 % | **0.96** |
| 2 | 100 m | 95 % | **100 %** | **0.95** |
| 3 | 30 m | 17 % | 29 % | **0.60** |
| 3 | 60 m | 71 % | 71 % | **0.99** |
| 3 | 100 m | 95 % | **100 %** | **0.95** |

A filter that discriminates has ratio > 1 — it keeps good fixes and drops fatal
ones. **Every cell is below 1.** The filter does not merely fail to
discriminate; it discriminates *backwards*, retaining wrong fixes at a higher
rate than right ones at every single setting.

**KILLED**, and not narrowly.

### 3.3 Why — the aliases travel with the aircraft

The decisive number is the tol = 100 m row: **100 % of fatal fixes survive.**
Every wrong fix in the pool is corroborated by a neighbouring frame to within
100 m of the expected inter-frame motion.

**Finding U — the aliases are spatially coherent across frames.** They are not
independent per-frame errors that corroboration can average away. The repetitive
structure the matcher locks onto — furrows on R04, canopy on R06 — *translates
with the aircraft*, so a wrong lock is self-consistent from frame to frame in
exactly the way a correct lock is. Two consecutive frames locked one furrow
period north are separated by precisely the distance flown, and are therefore
indistinguishable from two consecutive correct fixes.

This also answers the question Step 2 left open. Step 2 could not tell whether
R04's furrow lock is the same across frames or random per frame; §3.2 says it is
**the same**, because otherwise the fatal fixes would have failed corroboration.

### 3.4 What this closes

Finding U is not specific to sequential consistency. **Any rejection method that
relies on aliases being temporally independent is defeated by the same
mechanism:**

- sequential / N-frame consistency (this step);
- PCM and GNC over the candidate set (`9th_iteration_survey.md` §10.2, S6) — PCM's
  premise is that inlier loop closures compose to identity around a cycle while
  outliers do not. Coherent aliases compose to identity too;
- trajectory clustering (7th-iteration Finding J) — which is now explained. It
  "nearly reached the oracle, and the oracle was only 25 %" because the aliases
  cluster just as tightly as the correct fixes;
- multi-frame pooling and voting (2nd/3rd iterations, already failed).

**Directions S6 and S7 from the 9th-iteration survey should be considered dead**
on this evidence, and the ORB-SLAM-style corroboration idea with them. That is
four survey directions closed by one 55-fix experiment.

The `min_support` parameter and larger windows cannot rescue it: window 3
performs the same as window 1, because the coherence extends across the whole
window.

### 3.5 Limits

- n = 55 pooled fixes, 14 of them fatal. Small, and the 6th iteration's rule
  says a per-region reliability metric below ~20 accepted fixes cannot carry a
  decision. This is a **pooled** result at 55, and the effect is unanimous across
  9 parameter cells, which is why it is reported as a kill rather than as
  direction-finding.
- Tested only on R04 and R06 — deliberately, since those hold 14 of the project's
  14 pooled fatal fixes at this configuration. R01/R08/R09 have too few accepted
  fixes to contribute.
- Motion compensation uses the prior, so it inherits the prior's error. At
  tol = 100 m that slack is larger than the drift increment between adjacent
  frames, so the 100 % fatal survival is not an artifact of sloppy compensation —
  a tighter tolerance would only reduce it, and the tol = 30 m row shows fatal
  fixes still outliving good ones there.

---

## Step 4 — Both Remaining Directions Gated And Killed

Verify-before-build, three cheap gates run in sequence against the two
directions §Closing left live.

### 4.1 Gate 1 — do the sub-tile offsets exist? SURVIVES

`scripts/gate_subtile_snap.py`, zero compute over `results/georef_bias.json`.
For a single global period `p`, does a per-frame integer `k` exist such that
`error − k·p·axis` is small? Oracle test, with a random-axis null control
because a free period plus a free integer per frame is a permissive model.

| region | baseline median | best period | oracle median | random-axis null | gain |
|---|---|---|---|---|---|
| **R04** | 41.3 m | 15 m | **12.7 m** | 30.3 m | **2.39×** |
| R03 (control) | 12.7 m | 10 m | 7.5 m | 10.8 m | 1.44× |

**SURVIVES on R04, and the R03 control correctly fails** — the gate
discriminates between the region with the lock and the one without. Finding T's
structure is real and removable in principle.

### 4.2 Gate 2 — can appearance pick the right offset? KILLED

`scripts/gate_subtile_ncc_select.py`. Against the ground-truth tile, displace
the tile-space correspondence by `k·15 m` along 171°, warp the reference under
the displaced homography, score masked patch NCC, take argmax.

| n=16, R04 | median error |
|---|---|
| k = 0 (current) | **41.3 m** |
| NCC-selected k | **41.3 m** |
| oracle k | **14.0 m** |

**NCC picked k = 0 on 16 of 16 frames.** Not ambiguously — unanimously. The
homography is fitted to maximise correspondence agreement, and patch NCC is
maximised at that same alignment, so **the wrong lock is itself the appearance
optimum**. Appearance is not weakly informative here; it is monotone *against*
the truth.

This generalises the 5th iteration's observation that patch NCC agrees with R04
aliases because the content is texturally self-similar. Sub-tile disambiguation
by any appearance score is dead.

### 4.3 Gate 3 — would a robust back-end separate the fixes? KILLED

`scripts/gate_robust_smoother.py`, zero compute over
`results/sequential_consistency.json`. A robust kernel keeps the largest
mutually-consistent measurement set. So: do good fixes form a larger
mutually-consistent clique than fatal ones? Motion-compensated with priors, not
ground truth.

| tol | R04 good/fatal clique | R06 good/fatal clique | pooled ratio |
|---|---|---|---|
| 30 m | 2 / 1 | 2 / 2 | **1.33×** |
| 60 m | 4 / 2 | 2 / 2 | **1.50×** |
| 100 m | 5 / 2 | 4 / 3 | **1.80×** |

**KILLED at every tolerance** (bar was 2×).

The reason is more damaging than the ratio. **The good fixes barely form cliques
either** — 27 good fixes on R04 yield a maximum mutually-consistent set of 5 at
a 100 m tolerance. Their own ~30 m scatter is large enough that pairs of correct
fixes disagree by as much as a correct-and-aliased pair does. The premise every
consistency-based robust method rests on — inliers agree with each other,
outliers do not — **does not hold in this data for either group**.

Pooled clique purity does rise (75 % → 83–100 %), but only by keeping 3–8 of 55
fixes. That is the same trade every gate from the 3rd iteration onward has
offered: purity bought with most of the coverage.

**Scope of this kill.** It rules out the *pairwise-consistency* family
(PCM, GNC-over-candidates, clique selection) directly, reinforcing Finding U. A
magnitude-based Huber kernel inside a smoother is not identical, and R06's
bimodal error distribution (7th-iteration Finding K) means such a kernel could
separate R06's 150–400 m jumps *if* the trajectory estimate were good enough to
expose them as residuals. At 7-second frame spacing this project's odometry is
not (5th iteration: tracked features collapse to 0–14 by frame 2), so that
condition is not met here. Recorded as killed for this platform, not as a
statement about robust smoothing in general.

---

## Step 5 — Coverage Ceilings, And The DSM Direction Closed

### 5.1 Is coverage recoverable? Mostly no

GT-tile probe with the Step 1 AGL correction active, n=40, `min_inliers=10`.
"Ceiling" is the share of frames clearing the threshold against the tile they are
*supposed* to match — the upper bound on match rate for this matcher, independent
of retrieval, drift or gating.

| Region | mean inliers | ceiling | observed | headroom |
|---|---|---|---|---|
| R01 riverside | 4.9 | 10.0 % (4/40) | 2.5 % | +7.5 |
| R03 farmland | 35.8 | ~at limit | 85.0 % | — |
| R04 repetitive | 97.4 | ~at limit | 85.0 % | — |
| R06 forest | 11.9 | ~at limit | 52.5 % | — |
| R08 non-planar | 6.6 | 7.5 % (3/40) | 5.0 % | +2.5 |
| R09 suburban | 10.8 | 15.4 % (4/26) | 2.5 % | +12.9 |

**Coverage is not broadly recoverable.** Every scene sits within a few points of
its own ceiling, and the ceilings on R01/R08/R09 are themselves 7.5–15.4 %.
Finding N extends to R09, just less extremely. R09 additionally has 14 of 40
drone images missing, which caps it independently.

*A correction to an intermediate claim made during this work:* an n=16 probe put
R09's ceiling at 36.4 % and its headroom at +33.9 points. That rested on 4 of 11
usable frames. At n=40 the ceiling is 15.4 %, and R09 reaches 7.5 % at
`ncc_verify≤0.10` and 10.0 % under a drift=0 oracle. Real headroom is ~5 points,
not 34.

**The one actionable coverage item** is that `ncc_verify=0.30` over-rejects
sparse-texture scenes: R09 goes 2.5 % → 7.5 % at `ncc≤0.10`. The 5th iteration
documented this and recommended a per-terrain threshold; it was never acted on.

### 5.2 PnP against a 2.5D map — closed, with a mechanism

The largest untested structural difference from published work
(`9th_iteration_survey.md` §1). Three attempts, in order.

**Attempt 1 — PnP, discarded as broken.** `scripts/gate_pnp_dem.py` lifted tile
points to 3D and solved PnP. It returned ~100 m errors on frames where the
homography got 19 m *from the same correspondences*. With 0.4–3.3 m of relief the
points are effectively coplanar — degenerate for `SOLVEPNP_EPNP`, rejected by
`SOLVEPNP_IPPE`. **Recorded as an implementation failure, not a result.** No
conclusion is drawn from it.

**Attempt 2 — the bound, solver-independent.** From the cached DEM alone, per
region: median relief within one footprint, times `tan(41°)`, is the most a
perfect DSM at this resolution could remove.

| Region | AGL | footprint | relief | max correctable | observed median | fraction |
|---|---|---|---|---|---|---|
| R01 | 393 m | 680 m | 8.3 m | 7.2 m | 4.5 m | — |
| **R03** | 456 m | 789 m | 8.8 m | **7.6 m** | 13.9 m | **55 %** |
| R04 | 534 m | 924 m | 3.5 m | 3.1 m | 30.9 m | **10 %** |
| **R06** | 311 m | 538 m | 28.6 m | **24.7 m** | 23.3 m | **~100 %** |
| R08 | 544 m | 941 m | 4.8 m | 4.2 m | 20.0 m | 21 % |
| R09 | 538 m | 931 m | 6.6 m | 5.7 m | 21.7 m | 26 % |

On this evidence the direction looked genuinely promising on R03 and R06, and
worthless on R04 — the latter consistent with Finding T.

**Attempt 3 — relief-corrected homography, the right model.** For a near-planar
scene the correct treatment is not PnP but moving each correspondence onto the
reference plane along its camera ray before fitting:
`P' = C + (P − C)·H/(H − h)`, with one refinement iteration to recover `C`.
`scripts/gate_relief_corrected_homography.py`.

| region | flat | relief-corrected | gain | frames improved |
|---|---|---|---|---|
| R03 | 18.3 m | 17.3 m | **+1.0 m** | 2/14 |
| R06 | 18.6 m | 18.6 m | **−0.0 m** | **0/8** |

**KILLED on both.** R06 is the informative cell: the inlier set carries
17.6–17.9 m of relief and the correction moves the answer by 0.0–0.1 m.

**Finding W — RANSAC already selects a coplanar subset, so relief never biased
the homography.** The flat-ground fit is not a compromise plane averaged over
points at different heights; it is the plane that the largest consistent set of
points lies on, with the relief-displaced remainder rejected as outliers. There
is therefore nothing for a DSM to correct in the surviving correspondences, which
is why the bound in Attempt 2 — real as a statement about the terrain — does not
translate into recoverable error.

This closes the PnP/2.5D direction on this data with a mechanism rather than a
failed number, and it also explains why R08 was never a non-planar-geometry
problem (5th iteration) despite containing buildings.

### 5.3 What that leaves for R03's residual

R03's ~13.9 m median is now not explained by: fit quality (Finding P,
saturation), candidate selection (oracle ≈ pipeline, +2 m), a constant
georeferencing offset (8th iteration, split-half negative), altitude/GSD scale
(7th iteration, and Step 1 for the regions where it mattered), or terrain relief
(Finding W).

The most parsimonious remaining explanation is **the dataset's own ground-truth
accuracy**. UAV-VisLoc positions come from onboard GPS, not RTK. A ~10 m GPS
error reproduces every observed property at once: common-mode across
architecturally independent matchers (they agree with each other because they are
both matching the imagery correctly — the *reference* is what is wrong),
frame-specific rather than constant, unaffected by relief correction, and
invisible to every in-pipeline signal.

This is consistent with the field: OrthoLoC audited aerial-VL datasets for
ground-truth pose accuracy and found CrossLoc and UAVD4L exhibit "noticeable
projection errors", while its own GCP-verified ground truth reaches ~5 cm.
**UAV-VisLoc was not audited.** Testing this needs either RTK ground truth or an
OrthoLoC-style reprojection audit against a high-precision DOP/DSM — neither
available here — so it is recorded as the leading hypothesis, not a finding.

If it is right, **R03 at 13.9 m is at or near this dataset's noise floor**, and
its 92.9 % A@25m oracle ceiling is the real ceiling rather than an intermediate
target.

---

## Closing Assessment

Three steps, chosen by evidence in hand rather than by novelty. **One adopted,
one reframed a prior finding, one killed a family of four.**

| Step | Outcome |
|---|---|
| 1 — AGL correction | **ADOPTED.** R06 4/40 → 21/40 matched, 3 → 14 good fixes. Pooled A@25m 17.9 % → 22.5 % over attempted frames. First production config change since the 5th iteration. |
| 2 — R04 error direction | **Finding T.** R04's residual is sub-tile aliasing, not imprecision. 7th-iteration Finding K's "continuous, no gap" was an artifact of taking the magnitude and discarding the sign. |
| 3 — sequential consistency | **KILLED (Finding U).** Aliases are spatially coherent across frames, so consistency-based rejection discriminates backwards. Closes sequential consistency, PCM/GNC, trajectory clustering and multi-frame voting together. |

Step 4 then gated both directions the closing assessment had left live, and
**killed both**:

| Gate | Question | Result |
|---|---|---|
| 1 | Do sub-tile offsets exist? | **SURVIVES** — R04 oracle 41.3 → 12.7 m, 2.39× over null; R03 control correctly fails |
| 2 | Can appearance pick them? | **KILLED** — NCC selects k=0 on 16/16; the wrong lock is the appearance optimum |
| 3 | Would a robust back-end separate fixes? | **KILLED** — good/fatal clique ratio 1.33–1.80×; good fixes do not form cliques either |

**Finding V — the alias tail on this dataset is not reachable by any signal
available to this pipeline.** Gate 1 proves the structure is there and worth
14 m of median error on R04. Gates 2 and 3 prove nothing in the system can find
it: appearance is monotone against the truth, and consistency cannot bind even
the correct fixes, whose own ~30 m scatter is comparable to the alias
displacement.

**Where this leaves the project.** Findings T, U and V together give a tight,
evidenced statement: the wrong fixes sit on the *correct tile*, displaced by a
repeating structure's period, translating coherently with the aircraft, at a
magnitude comparable to the scatter of the correct fixes. Candidate scoring
cannot see them (six signals, iterations 3–6, plus NCC-over-offsets here),
candidate generation is not the cause (7th-iteration oracle), better matchers do
not help (Findings I and P), temporal consistency is defeated by their coherence
(Finding U), and pairwise-consistency robust estimation has no purchase
(Gate 3).

**That is the thesis result.** It is a negative with a fully characterised
mechanism and an oracle bound on what a solution would be worth — which is
stronger than the elimination argument the 6th iteration offered and was
retracted for.

**What genuinely remains** is outside the matching pipeline, and each item is
now stated with what would have to change:

1. **Better reference imagery** for R01/R06/R08 (7th-iteration Finding N, still
   standing for R01 and R08 after the 9th iteration retracted it for R06).
2. **A finer DSM plus PnP** (`9th_iteration_survey.md` §1) — untested here.
   Gate 3's failure is about consistency, not geometry, so this is not closed by
   Step 4. It remains the largest untested structural difference between this
   project and published work.
3. **Odometry good enough to expose alias residuals.** Gate 3's kill is
   conditional on 7-second frame spacing. A platform capturing at video rate
   would give a smoother something to grip, and the same robust-kernel argument
   would need re-testing rather than inheriting this result.

---

*Document complete — 2026-08-09. All three steps measured this session.
Step 1: `scripts/build_dem_cache.py`, `kp_vio/map_matching/dem.py`,
`MapMatcher(dem=)`, `comprehensive_scene_test.py --dem`; artefacts
`datasets/uav_visloc/dem_cache.json`,
`results/comprehensive/adopted_M4_mf+ncc0.30{nodem,dem}_R*_d300.csv`.
Step 2: `scripts/analyze_r04_error_direction.py`,
`scripts/measure_furrow_axis.py` (inconclusive, §2.5).
Step 3: `scripts/sweep_sequential_consistency.py`, artefact
`results/sequential_consistency.json`.*

*Document in progress — 2026-08-09. Step 2 measured this session via
`scripts/analyze_r04_error_direction.py` over `results/georef_bias.json`
(persisted by the 8th iteration). Step 1 code complete
(`scripts/build_dem_cache.py`, `kp_vio/map_matching/dem.py`, `MapMatcher(dem=)`,
`comprehensive_scene_test.py --dem`); validation running. Step 3 not started.*
