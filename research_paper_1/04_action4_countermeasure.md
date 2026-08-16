# Action 4 — The Countermeasure: Both Routes Killed, Finding V Strengthened

**Date:** 2026-08-15
**Scripts:** `tile_period_fft.py` (4a), `mixture_filter_r04.py` (4b), both new.

Hypothesis (pre-stated): the sub-tile alias is a lock one furrow period off
along the local field axis; therefore (a) the period/axis should be estimable
from the satellite tile itself, and (b) a multi-hypothesis mixture filter
anchored to the prior should recover the oracle gap that rejection cannot
touch. Kill criteria: (a) local periodicity must align with alias offset
bearings; (b) posterior-mean output must recover ≥30% of the oracle gap
(17.1 m ⇒ ≥5.1 m) at prior σ ≤ 20 m.

## 4a — Tile periodicity: KILLED

Detrended autocorrelation of a 500-px crop around each locked position
(R04, n=610), strongest local maximum in the 9.5–95 m band.

| group | n   | in-band% | median period | median \|Δbearing\| vs error |
| ----- | --- | -------- | ------------- | ---------------------------- |
| good  | 143 | 17%      | 22.4 m        | 44.6°                        |
| mid   | 374 | 15%      | 23.6 m        | 46.1°                        |
| alias | 93  | **9%**   | 38.7 m        | **52.2°**                    |

No bearing alignment in any group (≈45° is the uniform-90° expectation), and
the alias group has the _least_ in-band periodicity — the opposite of the
hypothesis. At 1.19 m/px the satellite texture does not expose the furrow
lattice the matcher locks onto. **The deployed system cannot know the local
axis/period from its own map data.**

## 4b — Mixture hedge filter: KILLED on the pre-stated criterion

Grid k ∈ [−4..4], p = 20 m, axis 171° (Gate-1 values). Stream: R04
contiguous, n=610. Baseline k=0: **31.1 m**; global-axis oracle: **14.0 m**
(gap 17.1 m).

| prior             | MAP median | posterior-mean median | mean vs k=0 | verdict |
| ----------------- | ---------- | --------------------- | ----------- | ------- |
| random walk σ=300 | 68.4 m     | 31.9 m                | −0.8 m      | fail    |
| random walk σ=50  | 38.7 m     | 34.3 m                | −3.1 m      | fail    |
| random walk σ=5   | 31.1 m     | 31.2 m                | −0.1 m      | fail    |
| IID σ=50          | 46.7 m     | 37.2 m                | −6.1 m      | fail    |
| IID σ=5           | 31.2 m     | 31.3 m                | −0.2 m      | fail    |

Three mechanisms, each measured:

1. **Gauge symmetry.** Pairwise motion consistency cannot see a constant
   offset (it cancels in frame differences) — this is Finding U in one
   sentence, and it leaves the prior as the only anchor.
2. **The anchor is too noisy.** Even the video-rate limit (IID σ=5 m) fails:
   per-frame debugging shows the posterior concentrates at k=0 on 25/25
   sampled frames, because the true alias offsets are _not_ multiples of the
   global 171°/20 m grid — Action 1's per-field revision at stream scale.
3. **The rich grid is overfit, not structure.** [EXPLORATORY, NO SAVED
   ARTIFACT — removed from paper v2 per reporting rules.] A grid over 12
   axes × 4 periods × 7 k (hypothesis count as logged: 252) reached an
   "oracle" median of 3.0 m — but with 252 free hypotheses per frame it
   fits the good fixes' own noise. It is indistinguishable from
   curve-fitting, and the IID σ=5 mixture extracts nothing from it
   (31.2 m). Because the run was not saved as an artifact, the paper
   reports only the reproducible single-axis oracle (14.0 m,
   `action4_mixture.json`).

**What survives, stronger:** the global-axis oracle bound (14.0 m) is
reproduced at n=610, and the countermeasure _motivated by the mechanism_
fails for a _measured_ reason. Finding V upgrades from "unreachable by any
signal in the pipeline" to: the alias lattice is per-field, unobservable in
the satellite texture, and invisible to frame differences — recovery would
require per-field lattice annotation on the map side, which no current map
provides. The escape hatch is quantified: no prior quality, however tight,
recovers the gap without the lattice geometry.

**Honest note on the positive side.** The posterior-mean (hedged) output is
_never_ materially worse than the production behaviour (worst −3.1 m),
while the MAP (committed) output is _catastrophically_ worse (68.4 m at
σ=300). For fusion consumers, hedging is the safe default: it converts an
unresolvable ambiguity into a wider-but-honest uncertainty.

## Artifacts

- `results/action4_period.json` (610 frames), `results/action4_mixture.json`
- `results/action4_period.log`, `results/action4_mixture.log`
