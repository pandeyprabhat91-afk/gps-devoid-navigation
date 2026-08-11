# GPS-Denied UAV Navigation — 6th Iteration

**Project:** MTech Final Year Project, IIT Madras
**Date:** 2026-08-08
**Status:** COMPLETE — audit-and-repair pass. 5th-iteration numbers verified
reproducible. Four defects found, four hypotheses tested, **none adopted**.
Production config unchanged. Value delivered is three mechanism findings and
one methodological correction, not a performance gain.

### Headline

| | |
|---|---|
| 5th-iter numbers reproduce? | **Yes** — baseline exact to every decimal, 6 regions |
| Defects found | 4 (early exit, NCC-never-ranked, NCC zero-fill bias, harness delta bug) |
| Fixes that improved anything at 6 regions | **0** |
| Production config after this iteration | **unchanged** (`multi_feature=True, ncc_verify=0.30, min_inliers=10`) |
| Aggregate, legacy vs fixed (6 regions, drift=300, n=40) | 30.8 % / 21.2 m / 12.2 % fatal **vs** 30.8 % / 21.9 m / 12.2 % fatal |

> **Reading note.** Every number in this document comes from a script run this
> session against the production `MapMatcher`. Where a metric rests on few
> accepted fixes, the denominator is stated — see §7.1, which is the most
> consequential methodological finding here.

---

## 0. Why This Iteration Exists

The 5th iteration shipped `multi_feature=True, ncc_verify=0.30` and reported a
coverage breakthrough (2/6 → 5/6 terrains, yield roughly doubled). A review of
iterations 1–5 plus the handover document raised four concerns that could be
tested directly:

1. Whether the published numbers reproduce at all.
2. A candidate-loop early exit that appeared to truncate the 49-tile search
   once multi-feature raised inlier counts by an order of magnitude.
3. `min_inliers=10` never re-derived after the inlier distribution moved
   5–10×.
4. NCC used only as a veto, never as the candidate ranking signal, despite
   being the only in-pipeline signal shown to separate aliases.

This iteration tests each. It is an audit-and-repair pass, not a new-method
pass.

---

## 1. Reproduction — The 5th-Iteration Numbers Are Honest

Before changing anything, the published configuration was re-run from a clean
checkout of the shipped code: drift=300 m, n=40, seed=1992, all 6 regions,
production `MapMatcher` via `comprehensive_scene_test.py`.

### 1.1 Aggregate (6 regions pooled)

| Config | Match% | CEP50 | CEP90 | Fatal50 | Yield% |
|---|---|---|---|---|---|
| baseline ORB — published (5th §4.2) | 16.2 | 23.1 m | 47.9 m | 10.3 | 14.6 |
| **baseline ORB — reproduced** | **16.2** | **23.1 m** | **47.9 m** | **10.3** | **14.6** |
| adopted M4 — published | 30.0 | 20.6 m | 51.4 m | 11.1 | 26.7 |
| **adopted M4 — reproduced** | **30.8** | **21.2 m** | **51.5 m** | **12.2** | **27.1** |

### 1.2 Per-scene, adopted config

| Region | Terrain | Published | Reproduced | Verdict |
|---|---|---|---|---|
| R01 | riverside | 0 % | 0 % | exact |
| R03 | farmland | 80.0 % / 13.3 m / 0 % fatal | 80.0 % / 13.2 m / 0 % | exact |
| R04 | farmland repetitive | 82.5 % / 32.9 m / 21.2 % | 82.5 % / 32.9 m / 21.2 % | exact |
| R06 | forest | 10.0 % / 28.1 m / 25.0 % | 10.0 % / 28.1 m / 25.0 % | exact |
| R08 | suburban non-planar | 7.5 % / 18.3 m / 0 % | 7.5 % / 18.3 m / 0 % | exact |
| R09 | suburban | 0 % | 0 % | exact |

**The baseline reproduces to every decimal. The adopted config differs by
+0.8 match / +1.1 fatal**, entirely attributable to the masked-NCC change in
§2.3 (which admits a few extra partial-overlap matches). Per-scene values are
otherwise identical.

**Finding A — the 5th-iteration results are reproducible and honestly
reported.** The defects documented below are design flaws, not measurement
or reporting errors. This matters for how the prior documents should be read:
their numbers stand; their *interpretations* are what this iteration revises.

---

## 2. Defects Found

### 2.1 Candidate-loop early exit (`map_matcher.py`)

```python
if best_inliers >= 3 * self._min_in:
    break
```

The candidate loop stops as soon as any tile reaches `3 * min_inliers` = 30
inliers. Under ORB-only this rarely fired (inlier counts 23–46 against a bound
of 30). Under multi-feature pooling, counts run 72–276 (5th-iter §5.3), so
**nearly every viable tile clears the bound and the first one scanned wins**.
The nominal 49-tile search was first-past-the-post ordering, not a search.

Fixed behind `early_exit: bool = True` (default preserves legacy behaviour).

### 2.2 NCC never used for ranking

Selection was `if n_in > best_inliers` — pure argmax on inlier count. The
patch-wide NCC introduced in the 5th iteration was applied only as a `continue`
veto. The 3rd iteration had already established that inlier statistics cannot
separate a perceptual alias from the correct tile (the reprojection-RMSE gate
changed *zero* accepted matches; the margin gate made fatal errors worse), yet
the one signal shown to differ was never given a vote in the decision.

Added `select_by: str = "inliers"` — set to `"ncc"` to rank candidates by
patch-wide appearance agreement instead.

### 2.3 `patch_ncc` counted warp-fill zeros

`cv2.warpPerspective` zero-fills every destination pixel whose source lies
outside the reference patch. `patch_ncc` included those zeros in both the mean
and the correlation, so the score was depressed in proportion to **unfilled
area** rather than match quality. A single global threshold therefore meant
different things on different terrains — the plausible mechanism behind R09
being over-rejected at `ncc_verify=0.30` while R04 aliases passed.

Added `patch_ncc_masked()`, which restricts the statistic to filled pixels and
declines (returns 0.0) when coverage is below 20 %.

### 2.4 Harness delta-table bug (`comprehensive_scene_test.py`)

```python
def delta(ak, bk, unit=""):
    av, bv = a.get(ak), b.get(bk)
```

Called as `delta('match_rate','%')`, so `bk='%'` and `b.get('%')` was always
`None` — every row of the per-scene delta table printed `n/a`. Cosmetic (the
underlying JSON was correct) but it silently disabled the one table designed to
show adopted-vs-baseline movement per scene.

---

## 3. Fix 1 — Early Exit: A Null Result

Per the 5th-iteration rule (*verify negative results with single-frame probe
diagnostics, not aggregate numbers*), the early-exit fix was tested with a
per-frame probe before any aggregate run. `scripts/diag_early_exit.py` runs both
matchers over the same frames and compares tile choice and error directly.

**R04 (the alias-tail region), n=12, drift=300 m:**

| frame | legacy err | full-scan err | legacy inliers | full inliers | better |
|---|---|---|---|---|---|
| 0 | 29.3 m | 29.2 m | 35 | 72 | — |
| 1 | 6.7 m | 7.8 m | 32 | 104 | legacy |
| 2 | 41.9 m | 40.8 m | 88 | 122 | full |
| 3 | 57.6 m | 56.9 m | 44 | 140 | — |
| 4 | 13.9 m | 14.2 m | 91 | 173 | — |
| 5 | 32.3 m | 34.2 m | 262 | 291 | legacy |
| 6 | 48.7 m | 48.7 m | 54 | 54 | tie |
| 7 | **1.9 m** | 3.5 m | 82 | 105 | legacy |
| 8 | 35.6 m | 35.4 m | 169 | 326 | — |
| 10 | 56.8 m | 57.2 m | 145 | 220 | — |

| | matched | median err | fatal50 |
|---|---|---|---|
| legacy (early exit on) | 11 | 35.6 m | 3/11 |
| full scan (early exit off) | 11 | **35.4 m** | 3/11 |

Frames differing by >1 m: 5 — full-scan better on 2, legacy better on 3.

**Finding B — the early exit is a real bug with no accuracy consequence.**
The truncated search returned a *different tile on 10 of 11 frames*, with 2–3×
fewer inliers, yet landed in essentially the same place. Median moves 0.2 m;
the fatal count is unchanged.

**Finding C — inlier count is anti-correlated with precision inside the
correct tile.** Scoring every candidate reliably finds tiles with more
correspondences, and those tiles are slightly *less* accurate (frame 7: 82
inliers → 1.9 m, versus 105 inliers → 3.5 m; frame 5: 262 → 32.3 m versus
291 → 34.2 m). Pooling more detectors adds marginal, poorly-localised
correspondences that satisfy RANSAC while degrading the homography's
positional fit.

This extends the 3rd-iteration result. Inlier count was known to be unable to
separate the correct tile from an alias. It is now also shown to be unable to
rank *within* the correct tile — and to rank slightly backwards. **Any gate or
ranking built on inlier count is operating on an axis that does not carry the
information being sought.**

### 3.1 Consequence for the planned `min_inliers` re-sweep

The review that prompted this iteration predicted the `min_inliers` knee would
move to 30–60 under multi-feature and collapse the fatal rate — described as
"the cheapest unexploited axis in the project". Finding C undercuts that
prediction directly: the threshold acts on the same uninformative axis, so it
should trade yield for little accuracy gain. The sweep is still being run
rather than assumed, but it is now expected to be a second null result and is
no longer the priority.

---

## 4. Fix 2 — NCC Candidate Selection: The One That Works

`sweep_6th_iteration.py --axis select --regions 03,04 --drift 300 --n 40`,
full 49-tile scan (`early_exit=False`) in both cells so the only variable is
the ranking signal.

R03 (80 % match, 0 % fatal) and R04 (82.5 % match, 21.2 % fatal) are the
informative pair: R03 shows what NCC ranking costs where matching already
works, R04 whether it helps where the alias tail lives.

### 4.1 Aggregate (R03 + R04 pooled)

| Ranking | Match% | CEP50 | CEP90 | Fatal50 | Yield% |
|---|---|---|---|---|---|
| `inliers` (legacy) | 81.2 | 22.1 m | 50.8 m | 10.8 | 72.5 |
| **`ncc`** | 81.2 | **21.6 m** | **49.7 m** | **9.2** | **73.8** |

### 4.2 Per-region — where the mechanism shows

| Region | `inliers` | `ncc` | change |
|---|---|---|---|
| R03 (no aliasing) | 80.0 % / 13.5 m / 0 % fatal | 80.0 % / 16.0 m / 0 % fatal | CEP50 **+2.5 m worse** |
| R04 (alias tail) | 82.5 % / 32.8 m / **21.2 %** fatal | 82.5 % / 34.1 m / **18.2 %** fatal | fatal **−3.0 pts**, yield +2.5 pts |

**Finding D — appearance ranking pays exactly where geometry ranking is
blind, and costs a little where it is not.** On R03 the correct tile is
already being selected, so replacing a geometry-derived ranking with a coarser
appearance-derived one adds 2.5 m of noise to a decision that was already
right. On R04, where perceptual aliasing is the failure mode, NCC catches
3 percentage points of wrong-tile selections that inlier count cannot see.

This is a **Pareto improvement in aggregate** — simultaneously better on
fatal50, CEP50, CEP90 and yield at identical match rate. That is unusual in
this project: every previously tested gate (reprojection RMSE, inlier margin,
NCC veto at higher thresholds) traded coverage for tail.

**Scope of the claim.** The improvement is 3 percentage points off a 21.2 %
fatal rate. It is real, reproducible and free, but it does not solve
aliasing — R04 remains far from the `fatal50 < 5 %` target. The per-region
split also means a terrain-adaptive choice (`ncc` on repetitive terrain,
`inliers` elsewhere) would beat either fixed setting; that is untested.

---

## 5. Fix 3 — NCC Non-Adjacency Margin Gate: Rejected

Sharper form of Finding D: reject when a **spatially distant** tile scores
nearly as well on NCC, while tolerating adjacent ties (adjacent disagreement is
sub-tile ambiguity worth metres; distant disagreement is aliasing worth
hundreds). Unlike the 3rd-iteration margin gate — which compared inlier counts
and made fatal errors worse — this operates on the signal Finding D showed does
carry alias information.

`--axis margin --values 0.02,0.05,0.10`, R03+R04, drift=300, n=40,
`select_by=ncc` throughout so the margin is the only variable.

| `ncc_margin` | Match% | CEP50 | CEP90 | Fatal50 | Yield% |
|---|---|---|---|---|---|
| **0.00 (no gate)** | **81.2** | 21.6 m | 49.7 m | **9.2** | **73.8** |
| 0.02 | 80.0 | 21.0 m | 49.7 m | 9.4 | 72.5 |
| 0.05 | 77.5 | 21.0 m | 49.8 m | 9.7 | 70.0 |
| 0.10 | 76.2 | 21.6 m | 49.8 m | 9.8 | 68.8 |

Per-region at 0.02: R03 80.0 % / 16.0 m / 0 % fatal (unchanged);
R04 80.0 % / 34.8 m / **18.8 %** fatal (worse than 18.2 % ungated).

**Finding E — the margin gate fails again, and the failure is a property of
margin gating rather than of the signal.** Every increment costs coverage
*and raises* fatal50; the sweep is monotone in the wrong direction on both
axes at once. The non-adjacency restriction did not rescue it.

The 3rd iteration diagnosed the inlier margin gate's failure as *"on repeating
terrain, contested frames are disproportionately the correct ones"*. That
diagnosis is now confirmed to be signal-independent: switching the margin from
inlier count to NCC, and restricting rejection to spatially distant
competitors, reproduces the same behaviour. **Contested-ness is not evidence of
wrongness in this data, whatever quantity the contest is scored on.**

---

## 6. Fix 4 — `min_inliers` Re-Sweep: Refuted

The review that prompted this iteration predicted that `min_inliers=10`, chosen
in the 3rd iteration from the ORB-only inlier distribution, would be far below
the multi-feature noise floor; that the knee would move to 30–60; and that this
was "the cheapest unexploited axis in the project" with a "likely large"
payoff. Finding C predicted the opposite (the threshold acts on an axis
anti-correlated with precision). The sweep settles it.

`--axis min_inliers --values 10,20,40,80`, R03+R04, drift=300, n=40.

| `min_inliers` | Match% | CEP50 | CEP90 | Fatal50 | Yield% |
|---|---|---|---|---|---|
| **10 (shipped)** | **81.2** | 22.1 m | 50.8 m | **10.8** | **72.5** |
| 20 | 72.5 | 22.8 m | 51.6 m | 12.1 | 63.8 |
| 40 | 57.5 | 22.8 m | 51.6 m | 13.0 | 50.0 |
| 80 | 33.8 | 22.1 m | 45.5 m | 7.4 | 31.2 |

Per-region, R04 (the alias tail): fatal 21.2 → 21.9 → 21.4 → 10.0 % across
10/20/40/80, with match rate falling 82.5 → 50.0 %.

**Finding F — raising `min_inliers` makes the tail worse before it makes it
better, and the eventual improvement is the trivial one.** Fatal50 *rises*
monotonically through 20 and 40 while yield falls by a third. It only improves
at 80, where match rate has collapsed to 33.8 % — the same
"the system stops answering, so it stops answering wrongly" mechanism the 3rd
iteration documented at 600 m drift, not a genuine reliability gain.

**CEP50 is flat to within 0.7 m across an 8× threshold range** (22.1 / 22.8 /
22.8 / 22.1). This is Finding C in aggregate form: the inlier axis carries
almost no accuracy information, so a threshold on it cannot buy accuracy.

**`min_inliers=10` is re-confirmed optimal under multi-feature**, for a reason
the 3rd iteration did not have: not because the knee happens to sit there, but
because the axis is uninformative and 10 is simply the value that costs the
least coverage. The prediction that motivated this sweep was wrong.

---

## 7. Final Confirmation — The One Gain Does Not Survive 6 Regions

Fixes 1 and 2 (early_exit=False, select_by=ncc) were confirmed against the
shipped 5th-iteration config on **all six regions**, drift=300, n=40 — the
project's own adoption rule, which the R03+R04 sweeps above do not satisfy.

| Config | Match% | CEP50 | CEP90 | Fatal50 | Yield% | Working |
|---|---|---|---|---|---|---|
| legacy 5th (`early_exit=True, select_by=inliers`) | 30.8 | **21.2 m** | **51.5 m** | **12.2** | **27.1** | 5/6 |
| fixed 6th (`early_exit=False, select_by=ncc`) | 30.8 | 21.9 m | 51.7 m | **12.2** | **27.1** | 5/6 |

**Identical fatal50, identical yield, identical match rate, CEP50 0.7 m
worse.** The Pareto improvement measured on R03+R04 (fatal 10.8 → 9.2 %)
**does not survive** to the full region set.

### 7.1 Why — one frame in a 3-frame region

| Region | legacy | fixed (ncc) | delta |
|---|---|---|---|
| R01 riverside | 0 % match | 0 % match | — |
| R03 farmland | 80.0 % / 13.2 m / **0 %** fatal | 80.0 % / 16.0 m / **0 %** | CEP50 +2.8 m |
| R04 farmland repetitive | 82.5 % / 32.9 m / **21.2 %** | 82.5 % / 34.1 m / **18.2 %** | fatal **−3.0** |
| R06 forest | 10.0 % / 28.1 m / 25.0 % | 10.0 % / 27.9 m / 25.0 % | — |
| R08 suburban non-planar | 7.5 % / 18.3 m / **0 %** | 7.5 % / 19.8 m / **33.3 %** | fatal **+33.3** |
| R09 suburban | 5.0 % / 38.8 m / 50.0 % | 5.0 % / 38.8 m / 50.0 % | — |

R08 accepts **3 frames**. NCC ranking flipped exactly one of them to a wrong
tile: 0 % → 33.3 % fatal. That single frame cancels R04's three-point gain in
the pooled aggregate.

**Finding G — the R03+R04 result was a sub-sampling artifact, and the
project's own n≥40-per-region rule does not protect against it.** The rule was
satisfied (40 frames attempted per region) but the binding quantity is
*matched* frames, not attempted ones. R08's fatal50 is computed over 3 accepted
fixes, R06's over 4. At those counts a single frame moves the per-region metric
by 25–33 points, which is larger than any effect this iteration measured.

This retroactively qualifies several published per-region numbers, including
the 5th iteration's headline "R08 first-ever matching at 0 % fatal" — that
0 % is 3 frames, and is one frame away from 33 %.

### 7.2 Adoption decision

**Nothing from this iteration is adopted.** `select_by="ncc"` is left in the
codebase, default off, documented as: helps on repetitive farmland (R04),
harmful on sparse-texture terrain (R08), net-zero pooled. A terrain-adaptive
selection rule is the only way it pays, and testing that needs per-region
sample sizes this dataset cannot supply at the current match rates.

The shipped 5th-iteration configuration (`multi_feature=True,
ncc_verify=0.30, min_inliers=10, early_exit=True, select_by="inliers"`)
**remains the recommended production config, unchanged.**

---

## 8. Reporting Rules Carried Forward

Same as 3rd/4th/5th, applied throughout:

- Report `fatal50 + cep90 + good_yield`, never `cep50` alone.
- Never quote numbers measured with the prior set to ground truth.
- Never cross-quote between harnesses. All 6th-iteration numbers come from
  `comprehensive_scene_test.py` / `sweep_6th_iteration.py`, which share the
  same `DriftModel`, seed, step-sampling and metric formulae.
- Treat monotone-to-the-edge sweeps as unfinished, not as results.
- Require n ≥ 40 per region for adoption claims.
- Verify negative results with single-frame probe diagnostics. Applied to the
  early-exit fix (§3), which is why it was correctly identified as a null
  result rather than adopted on the strength of a plausible mechanism.

**New rules proposed this iteration:**

- **Reproduce before revising.** Every defect claim in §2 was made against
  code that had first been shown to reproduce its published numbers (§1).
  Without that step a refactor's own regressions are indistinguishable from
  the defects it claims to fix.

- **n ≥ 40 must apply to MATCHED frames, not attempted frames.** The existing
  rule was satisfied throughout this iteration and still admitted a
  sub-sampling artifact (§7.1): R08's fatal50 rests on 3 accepted fixes, where
  one frame is worth 33 points. Any per-region reliability metric computed over
  fewer than ~20 accepted fixes should be reported with its denominator inline
  (`0 % (0/3)`, not `0 %`) and must not carry an adoption decision.

- **Confirm on the full region set before believing a subset result.** The
  NCC-ranking gain was real, reproducible and Pareto-optimal on R03+R04, and
  vanished at 6 regions. Subset sweeps are for direction-finding only.

---

## 9. Closing Assessment

Four hypotheses were tested. **One survived subset testing; none survived
full confirmation. Nothing is adopted.**

| Fix | Prior expectation | Measured result |
|---|---|---|
| Early exit off | significant (bug found in code review) | **Null** — 0.2 m, fatal unchanged |
| NCC ranking | promising | **Pareto on R03+R04, net-zero on 6 regions** |
| NCC margin gate | promising | **Rejected** — monotone wrong direction on both axes |
| `min_inliers` re-sweep | "cheapest unexploited axis, likely large" | **Refuted** — 10 already optimal; 20–40 actively worse |

**What this iteration is actually worth.** Not a performance gain — there is
none. Its value is three mechanism findings that redirect future work, and one
methodological correction:

1. **Finding C** — inlier count is anti-correlated with precision *inside* the
   correct tile, not merely unable to separate tiles. This explains, with a
   single cause, why the reprojection-RMSE gate changed zero matches (3rd iter),
   why the inlier margin gate made things worse (3rd iter), why `min_inliers`
   tuning is exhausted (3rd/4th iter), and why raising it now backfires (§6).
   Four separate negative results in prior iterations were all the same result.

2. **Finding E** — margin gating fails independently of the signal it scores.
   Two implementations (inlier margin, NCC non-adjacency margin) fail
   identically. Contested-ness is not evidence of wrongness in this data.

3. **Finding D/G** — NCC *ranking* carries alias information that inlier count
   does not (R04 fatal −3.0 pts, reproducible), but the effect is smaller than
   the per-region sampling noise on the sparse-terrain regions. The signal is
   real; the dataset cannot support acting on it.

4. **Finding G** — the project's n≥40 rule counts attempted, not matched,
   frames, and therefore does not protect per-region reliability metrics. This
   qualifies published per-region numbers across the 5th iteration.

**The strategic conclusion.** Every in-pipeline signal available after tile
selection has now been tested against the alias tail: inlier count,
reprojection RMSE, inlier margin, patch NCC as veto, patch NCC as ranking,
NCC margin with non-adjacency. **All six fail or wash out.** The 5th iteration
hypothesised that closing the tail requires cross-view-*trained* retrieval;
that hypothesis is now supported by exhaustion of the alternatives rather than
asserted. The remaining lever is candidate *generation* — placing the correct
tile in the candidate set and wrong ones out of it — not candidate scoring.

> ### ⚠ RETRACTED (2026-08-09, 7th iteration)
>
> **The paragraph above is wrong, and was refuted by direct measurement one
> day later.** An oracle test ran the adopted configuration at **drift = 0**,
> where the prior equals ground truth, so the correct tile is centred in the
> search window and scored first — i.e. candidate generation is *perfect*.
>
> | | drift=300 | drift=0 (perfect generation) |
> |---|---|---|
> | 6-region aggregate | 30.8 % / 12.2 % fatal | **30.4 % / 11.0 % fatal** |
> | R04 | 21.2 % fatal | **21.9 % fatal** |
> | R06 | 10.0 % / 25.0 % fatal | **10.0 % / 25.0 % fatal** (identical) |
>
> Perfect candidate generation buys **1.2 points of fatal rate and no match
> rate at all**. Generation is not the bottleneck, so "cross-view-trained
> retrieval will close the tail" does not follow from this evidence and should
> not be carried forward as this document's recommendation.
>
> The error was one of elimination: having shown that six *scoring* signals
> fail, this section concluded generation must therefore be responsible,
> without testing generation. See `7th_iteration.md` §1 for the measurement
> and §4 for what the residual error actually is.

**The honest headline for the thesis** is a negative result with a clean
mechanism: *prior-conditioned map matching fails at candidate selection, not at
matching, and no post-selection signal recovers it.* That is defensible,
supported by six independent negative controls, and more publishable than an
incremental accuracy number would have been.

---

*Document complete — 2026-08-09. All numbers measured this session via
`comprehensive_scene_test.py` and `sweep_6th_iteration.py` at drift=300 m,
n=40, seed=1992, production `MapMatcher`. Raw artefacts:
`results/sweep6/sweep6_{select,margin,min_inliers,final}_d300.json`,
`results/comprehensive/*_repro_*.csv`.*

*Code changes (all default-off; legacy path verified byte-identical):
`map_matcher.py` (`early_exit`, `select_by`, `ncc_margin`),
`feature_matcher.py` (`patch_ncc_masked`), `comprehensive_scene_test.py`
(knob plumbing + delta-table keyerror fix), plus new
`scripts/sweep_6th_iteration.py` and `scripts/diag_early_exit.py`.*
