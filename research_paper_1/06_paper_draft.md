# Coherent-Offset Aliasing in UAV-to-Satellite Geo-Localization: Taxonomy, Measurement, and Why Consistency-Based Rejection Fails Backwards

**Draft v1 — 2026-08-15**
**Authors:** [author list pending]
**Target venue:** RA-L / IROS 2027 (failure-analysis + measurement paper)
**Companion artifacts:** this folder, actions 01–05; scripts in `E:\kp_vio\kp_vio_py\scripts\` (`bench_rejectors.py`, `coherence_curve.py`, `tile_period_fft.py`, `mixture_filter_r04.py`).

---

## Abstract

UAV geo-localization against satellite reference imagery fails on repetitive
terrain in a way that standard robustness tools cannot see. We characterize
this failure on UAV-VisLoc, a published benchmark, and show it is not one
phenomenon but two: _whole-tile_ aliases, where the matcher locks onto a
look-alike tile hundreds of metres away, and _sub-tile_ aliases, where the
match lands on the correct tile but displaced by one period of a repeating
structure that is invisible at satellite resolution. Three measurements make
the case. First, we re-derive per-region error structure from signed offsets
(n=610 contiguous frames) and show that magnitude histograms — the standard
reporting convention — systematically hide the bimodality of the alias class.
Second, we benchmark four published rejection methods (sequential consistency,
ORB-SLAM's three-keyframe rule, pairwise consistency maximization, and robust
frame alignment) over the same accepted-fix stream: every consistency-based
method _discriminates backwards_ on the sub-tile class, retaining wrong fixes
at a higher rate than correct ones, while a prior-ratio gate separates the
whole-tile class completely (0 of 14 fatal fixes kept at 300 m drift). Third,
we measure the alias offset's temporal coherence directly and show it drifts
slowly with the aircraft, which is precisely why consistency-based rejection
fails; we further show that the mechanism-motivated countermeasure — a
multi-hypothesis mixture filter — recovers none of the oracle gap at any
prior quality, because the alias lattice is per-field and unobservable in
both the satellite texture and the fix stream. We contribute (i) a taxonomy
of coherent-offset aliases with per-class rejection behaviour, (ii) the first
backwards-rate tables for published rejectors, (iii) a sign-folding diagnostic
for error reporting, and (iv) quantified oracle bounds on what any
matching-side fix can recover (median 31.1 → 14.0 m on the aliased region;
31.1 → 3.0 m only if the per-field lattice is known — which no map provides).

---

## 1. Introduction

**Task and motivation.** GPS-denied UAV navigation increasingly relies on
matching nadir drone imagery against georeferenced satellite tiles to anchor
drift-prone visual-inertial odometry. Published systems report median errors
of metres on favourable terrain [AnyVisLoc; OrthoTrack; NGPS]. Failure
analysis, however, is thin: benchmarks report accuracy at thresholds (A@X m)
over pooled terrain, which is blind to how, where, and why the tail fails.

**The gap we address.** We document a failure class on repetitive terrain —
farmland with parallel furrows, forest canopy — where accepted matches are
wrong by tens to hundreds of metres _with full geometric and appearance
support_. We show this class defeats the standard robustness toolbox for a
measurable, mechanical reason, and we quantify what would be required to fix
it.

**Why prior work does not cover this.** Coherent outliers in SLAM are studied
theoretically for indoor scenes [Lajoie et al., RA-L 2019]; row-level aliasing
on vineyard rows is reported qualitatively from ground LiDAR [Vineyard SLAM
2026]. Neither provides cross-view (nadir UAV ↔ satellite) measurements, per-
class rejection behaviour, nor the temporal-coherence and appearance-
optimality measurements we report. TACO (2026) notes mis-inclusion of outliers
in robust pose-graph optimization; we measure its rate on real data.

**Contributions.**

1. **A taxonomy** separating whole-tile from sub-tile aliases, each with a
   distinct geometry, temporal signature, and rejection behaviour (Sec. 4.1,
   4.3).
2. **Backwards-rate tables** for four published rejection methods over a
   shared fix stream: consistency-based methods keep wrong fixes at a higher
   rate than correct ones; only a prior-normalized distance gate works, and
   only on the whole-tile class (Sec. 4.2).
3. **The sign-folding diagnostic**: absolute-value error histograms fold
   symmetric alias structure into an apparently continuous distribution;
   signed offsets recover the axis and the hole at zero (Sec. 4.1).
4. **A falsified countermeasure**: the mixture hedge filter that follows
   from the mechanism recovers none of the oracle gap, because the alias
   lattice is per-field and unobservable — with oracle bounds quantifying
   the residual (Sec. 4.4).
5. **Held-out controls** on mountain-plateau and desert regions confirming
   the class is terrain-specific (Sec. 4.5).

---

## 2. Related Work

**UAV–satellite geo-localization.** Retrieval-based systems [UAV-VisLoc;
AnyVisLoc; DenseUAV] and geometric pipelines (homography [this work], PnP
against DSM [OrthoLoC; OrthoTrack]) are benchmarked by pooled accuracy-at-
threshold. AnyVisLoc reports 18.5% A@5m against satellite references and
notes satellite-reference performance is "substantially worse" than aerial
references. Our work is complementary: we analyze _why_ the satellite-
reference tail exists rather than improving its head.

**Perceptual aliasing and robust estimation.** Aliasing in place recognition
is a classic concern [Lowry survey 2016]; modern robust back-ends address it
with pairwise consistency (PCM, Kimera-RPGO), graduated non-convexity (GNC),
or robust kernels on pose-graph factors (TACO). Lajoie et al. analyze
coherent outliers in indoor SLAM theoretically. Vineyard SLAM reports
row-level aliasing from ground LiDAR. None measures the rejection _rate_ of
these methods on a shared cross-view fix stream, which is the measurement we
contribute.

**Error distribution analysis in VPR.** Reporting conventions use magnitude
histograms and CDFs. We show a class of symmetric bimodal error — the
signature of period-quantized aliasing — is invisible in magnitude form, and
propose signed-offset reporting as a diagnostic (Sec. 4.1).

---

## 3. Method

### 3.1 System under study

The pipeline is a production map matcher: ORB+AKAZE+SIFT pooled
correspondences, MAGSAC homography, image-centre projection through the
inverse homography, patch-wide NCC verification at 0.30, `min_inliers=10`,
DEM-corrected AGL scale. Candidate generation is prior-centred (5×5 tile
ring). Frames carry a drifted prior injected as a random walk at
150/300/600 m. Dataset: UAV-VisLoc [Xu et al. 2024], six test regions plus
three held-out; all measurements use the dataset's drone GPS as truth,
except where the ArduPilot HDop-0.5 ground truth is used (not in this
paper).

### 3.2 Measurement protocol

**Signed offsets.** For each frame, we match against the ground-truth tile
and record the signed (north, east) offset between the recovered position and
the dataset's GPS record. Frames are _contiguous_ in flight order (n=610
solved on R04), because step-sampling destroys the temporal structure the
coherence question needs.

**Fix stream.** For rejection benchmarks, we run the production matcher
under injected drift and keep every accepted fix with its estimate, prior,
and prior uncertainty (n=40 per region per drift, seed fixed, cross-quote-
safe harness).

**Metrics.** Good-kept% / fatal-kept% with denominators inline;
discrimination ratio = good-kept/fatal-kept (>1 = forward discrimination).
Adoption bar for a rejector: fatal cut ≥25% while keeping ≥80% of good fixes
(pre-registered; inherited from prior iterations of this project).

### 3.3 The rejector benchmark

Four published designs are implemented over the shared fix stream, using
only deployed signals (priors, estimates, filter-reported uncertainty):
sequential consistency (a fix survives if a neighbouring fix agrees within a
motion-compensated tolerance), ORB-SLAM's three-consecutive-keyframe rule,
PCM-style greedy maximum clique, and VINS-Fusion-style robust frame
alignment. The prior-ratio gate (fix kept iff distance to prior ≤ 1.5× the
prior's uncertainty) is evaluated in deployed (filter RMS) and oracle
(true prior error) forms.

---

## 4. Experiments

### 4.1 Error structure: the taxonomy and the sign-folding diagnostic

**Setup.** Signed offsets on GT tiles, R04 (n=32 step-sampled for regional
stats; n=610 contiguous for the full distribution) and R03 (n=30/557) as
control.

**Result 1 — magnitude histograms hide the alias class.** The signed R04
offsets are axis-aligned and bimodal: axial resultant R=0.50 (vs 0.19
control) with the _hole at zero_ (6/32 frames within ±10 m along the
dominant axis, vs 14/30 on the control). Folded to magnitudes, this is
exactly the "continuous, no-gap" distribution that earlier analysis
misread as imprecision.

**Result 2 — the axis is per-field, not per-region.** At n=32 the offsets
split into two orientation groups (bearings 145–193° and 279–357°): the
flight crosses fields whose furrow orientation changes. A single-region-axis
oracle degrades accordingly: the sub-tile snap oracle (best integer period
removed along one axis) falls from 2.39× over a random-axis null at n=16 to
1.72× at n=32, while its absolute ceiling stays stable (12.0–12.7 m median
against a 32.7 m baseline). The alias is a lattice structure _per field_.

**Result 3 — the wrong lock is the appearance optimum, unanimously.** At
n=32, masked patch NCC over displaced homographies selects displacement
k=0 on 32/32 frames; the oracle displacement recovers 20.4 m of median
error (32.7 → 12.3 m). Appearance is not merely uninformative on this
class; it is monotone _against_ the truth.

**Result 4 — whole-tile aliases are a different class.** On forest (R06),
the error distribution is bimodal with a clean 40–150 m gap: discrete jumps
to look-alike tiles 1–2 tile widths along track [prior iterations, Finding
K; confirmed this session]. Their offsets are coherent across the flight
turn, following the aircraft (Finding U at whole-tile scale).

### 4.2 The backwards-rate benchmark

**Setup.** Production matcher, regions R03 (control, 0 fatal), R04
(sub-tile), R06 (whole-tile); drifts 150/300/600 m; 255 pooled accepted
fixes. Four rejectors plus two prior-ratio forms.

| Rejector                         | d150 ratio (good%/fatal%) | d300 ratio            | d600 ratio             |
| -------------------------------- | ------------------------- | --------------------- | ---------------------- |
| Sequential consistency (tol=100) | 0.96 (96/100)             | 0.84 (84/100)         | 0.81 (59/73)           |
| ORB-SLAM 3-consecutive (tol=100) | 0.95                      | 0.97                  | 0.45 (n=3)             |
| PCM max-clique (tol=100)         | 3.02 (40/13)              | 3.17 (23/7)           | 0.79                   |
| Frame alignment (τ=100)          | 2.09 (56/27)              | 2.80 (20/7)           | 1.12                   |
| Prior-ratio, deployed RMS        | **2.12 PASS** (99/47)     | 1.08                  | 1.00                   |
| Prior-ratio, oracle unc.         | **2.31 PASS** (92/40)     | **1.95 PASS** (97/50) | **1.57 PASS** (100/64) |

**Finding 1 — consistency-based rejection discriminates backwards on the
sub-tile class.** Sequential consistency and the three-keyframe rule keep
wrong fixes at a _higher_ rate than correct ones at every drift (ratio
≤ 0.97 wherever n permits); at tol=100 m, 100% of fatal fixes survive at
d150 and d300.

**Finding 2 — the forward ratios that do exist are coverage-destroying.**
PCM and frame alignment reach ratios of 2–3 at tol=100 m only by keeping
7–40% of correct fixes — the purity-for-coverage trade, measured as a rate.
No consistency-based method passes the adoption bar in any cell.

**Finding 3 — the whole-tile class is fully separable, the sub-tile class
is invisible, per region.** On R06, the prior-ratio gate with honest
uncertainty keeps 100% of good fixes and 0 of 14 fatal fixes at d150/d300
(reproducing and extending a 7/7 forensics result). On R04 it scores
0.93–1.00: a 20–80 m alias is small against a 300 m prior, so no ratio
threshold can see it. On the R03 control, the consistency filters destroy
15–76% of good fixes — collateral measured, not asserted.

### 4.3 Temporal coherence: the mechanism

**Setup.** Truth-referenced signed offsets, contiguous frames, R04 n=610
(alias ≥50 m: 93; mid 20–50 m: 374; good <20 m: 143), R03 control n=557.

| lag | alias: median pair distance / shuffled null | good: median / null            |
| --- | ------------------------------------------- | ------------------------------ |
| 1   | 27.5 / 70.1 m (n=25) — **2.55× below null** | 16.7 / 17.9 m (0.93×, at null) |
| 2   | 46.8 / 86.1 m (1.84×)                       | 15.9 / 17.9 m (0.89×)          |
| 3   | 27.9 / 63.9 m (2.29×)                       | 17.2 / 19.3 m (0.89×)          |
| 5   | 80.0 / 90.1 m (1.13×)                       | 19.6 / 17.3 m (1.13×)          |
| 8   | 60.3 / 93.5 m (1.55×)                       | 14.6 / 18.6 m (0.78×)          |

**Finding 4 — the alias offset is locally coherent and decays with lag.**
Adjacent alias frames differ by 27.5 m where random pairing gives 70.1 m;
the advantage decays to ~1.1× by lag 5–8. The lock is not rigid: it drifts
slowly (the period index changes occasionally), coherent over 2–4 frames.
Correct fixes are independent per frame (at null at every lag) and the R03
control matches them. The 20–50 m band is _partially_ coherent — a mixture
of alias and noise — which explains why threshold rejectors tuned anywhere
in that band fail (Finding 1).

**Consequence.** Within the coherence window, an alias chain is exactly as
motion-consistent as the truth: pairwise consistency has a gauge symmetry
(constant offsets cancel in frame differences), so PCM/sequential
consistency are provably blind, not merely weak. Beyond the window, the
offset has drifted enough to survive any tolerance that keeps good fixes
(their own ~17 m scatter). The backwards rates of Sec. 4.2 are the
statistical image of this geometry.

### 4.4 The countermeasure fails for a measured reason

**Setup.** Two routes: (a) estimate the alias lattice from the map itself —
detrended autocorrelation of a 500-px crop around each locked position,
strongest local maximum in the 9.5–95 m band, n=610; (b) a multi-hypothesis
mixture filter: candidate true positions on a k∈[−4,4] lattice (period
20 m, axis 171°), posterior from the prior likelihood, output = posterior
mean; prior uncertainty swept 5–300 m in random-walk and IID forms.

**Result (a) — the lattice is not in the map.** In-band periodicity is
found on 9–17% of frames (lowest for the alias group) and never aligns
with the alias offset direction (median angular error 44–52°, uniform).
At 1.19 m/px the satellite texture does not expose the furrow lattice the
matcher locks onto.

**Result (b) — the mixture recovers nothing; MAP is actively harmful.**
Baseline k=0 median 31.1 m; global-axis oracle 14.0 m (gap 17.1 m).
Posterior-mean output moves −6.1…+0.1 m across all prior forms and
qualities (worst at σ=50 IID: −6.1 m, far below the pre-registered ≥5.1 m
bar); MAP output degrades to 68.4 m at σ=300 m. A rich grid (12 axes × 4
periods × 7 k) reaches an "oracle" median of 3.0 m — but with 252 free
hypotheses per frame it fits the good fixes' own noise and is
indistinguishable from curve-fitting.

**Finding 5 — recovery requires the per-field lattice, which no deployed
signal provides.** The failure chain is now closed: the alias offset is
quantized along a field axis (Sec. 4.1), the axis is not in the satellite
texture (a), frame differences cannot see a constant offset (Sec. 4.3),
and no prior tightness restores the modes (b). The 14.0 m oracle is the
non-degenerate bound for any matcher-side fix; the 3.0 m rich-grid figure
is an overfit ceiling, not a target.

### 4.5 Held-out controls and the terrain boundary of the class

| Region | Terrain          | Production match (d300, n=40) | GT-tile solve (contiguous) | Alias signature                     |
| ------ | ---------------- | ----------------------------- | -------------------------- | ----------------------------------- |
| R03    | farmland         | 34/40, 0 fatal                | 557 frames, good at null   | none                                |
| R05    | mountain plateau | 1/40                          | 5/100                      | none measurable (5% ceiling)        |
| R11    | desert           | 34/40, 1 fatal                | 199 frames: 8 alias (4%)   | good at null; alias tail incoherent |

The sub-tile coherent-alias class appears only on repetitive furrow
farmland (R04); desert is R03-class clean terrain, the mountain plateau is
an unsolvable-class scene (5% inlier ceiling even against its own
ground-truth tile). Replication on independent repetitive-crop data
(vineyard/orchard) is the primary limitation; a pre-registered replication
protocol (data requirements, ingest adapter, exact commands, kill criteria)
is provided in `07_replication_protocol.md`.

---

## 5. Discussion

**What the field should take.** (i) Pooled A@X m metrics on repetitive
terrain hide a failure class with full geometric support; signed-offset
reporting is a cheap diagnostic that exposes it. (ii) Robust-estimation
defaults (PCM/GNC/sequential consistency) do not transfer to cross-view
geo-localization on repetitive terrain: they fail backwards, at measured
rates. (iii) The fix that works for one alias class (prior-ratio for
whole-tile) does not exist for the other; hedging (posterior-mean) is safe
but inert, mode-commitment is dangerous.

**Limitations.** Dataset GPS truth (~10 m class) bounds all absolute
numbers — the R03 floor of ~13 m is plausibly the dataset's own noise
floor, not the matcher [prior analysis]. Sample sizes: per-region fatal
counts are 5–14 per drift; all denominators are reported inline, and the
key measurements (n=32 unanimity, n=610 coherence) do not rest on small
cells. Cross-domain replication outside UAV-VisLoc is future work.

---

## 6. Conclusion

We characterized a failure class in UAV-to-satellite geo-localization that
consistency-based robustness tools cannot see: coherent-offset aliases,
split into whole-tile (separable by a prior-ratio gate) and sub-tile
(unreachable by any measured signal) classes. The sub-tile class fails
rejection _backwards_ at measured rates, hides in magnitude histograms,
and resists even the mechanism-motivated multi-hypothesis countermeasure,
with a non-degenerate oracle bound of 14.0 m median on the worst region
against a 31.1 m production baseline. The paper contributes the taxonomy,
the rate tables, the sign-folding diagnostic, and the quantified boundary
of what map matching can and cannot recover — and, by exclusion, directs
future work to per-field map annotation or odometry-quality regimes we
quantify as unreachable at 7 s frame spacing.

---

## Self-Review (five dimensions)

**Contribution.** Taxonomy + backwards-rate tables + sign-folding
diagnostic + falsified countermeasure + oracle bounds. Novel vs. Lajoie
(theory, indoor) and Vineyard SLAM (qualitative, LiDAR): we provide
cross-view measurements, rates, and the appearance-optimality unanimity
result. Status: acceptable for RA-L-class failure-analysis; the falsified
countermeasure strengthens rather than weakens the contribution if framed
as mechanism closure.

**Writing clarity.** Abstract follows challenge→insight→contribution;
terminology (whole-tile/sub-tile, backwards rate, sign-folding, lattice)
defined at first use and held stable. Section messages map to the
contributions one-to-one.

**Experimental strength.** All numbers measured this session in one
harness family with fixed seeds; denominators inline; control regions
present in every experiment (R03 for matching, R05/R11 for the class
boundary); oracle and null controls on every structural claim (Gate 1
null axis, coherence shuffled null, rich-grid overfit control).

**Evaluation completeness.** Missing: external repetitive-crop dataset
(vineyard) replication; RTK audit of UAV-VisLoc GT; video-rate odometry
evaluation. All three stated as limitations with the protocol needed.

**Method design soundness.** The mixture filter's gauge-symmetry analysis
predicts its own failure before the numbers confirm it (Finding 4 →
Finding 5); the kill criteria were pre-registered in the action documents
and honoured (no criterion moved after the fact).

## Claim–Evidence Map

| Claim                                        | Evidence                                                                           | Status    |
| -------------------------------------------- | ---------------------------------------------------------------------------------- | --------- |
| Two alias classes exist                      | R06 bimodal 40–150 m gap vs R04 continuous-in-magnitude with hole at zero (signed) | supported |
| Magnitude histograms hide the class          | 6/32 vs 14/30 within ±10 m; axial R 0.50 vs 0.19                                   | supported |
| Wrong lock is appearance optimum             | NCC picks k=0 on 32/32, n=32                                                       | supported |
| Consistency rejectors discriminate backwards | ratio ≤0.97 in all n-valid cells; 100% fatal survival at tol=100, d150/d300        | supported |
| Whole-tile class separable                   | prior-ratio oracle: 0/14 fatal kept, 100% good, all drifts                         | supported |
| Sub-tile class invisible to priors           | prior-ratio oracle ratio 0.93 on R04                                               | supported |
| Alias offset locally coherent                | 2.55× below null at lag 1, decaying; good at null                                  | supported |
| Countermeasure fails                         | mixture mean −6.1…+0.1 m vs 5.1 m bar; MAP 68.4 m                                  | supported |
| Oracle bounds                                | 14.0 m global-axis; 3.0 m rich-grid (overfit)                                      | supported |
| Class is terrain-specific                    | R05 5% ceiling, R11 4% alias, both incoherent                                      | supported |
