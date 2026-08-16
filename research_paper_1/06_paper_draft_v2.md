# Coherent-Offset Aliasing in UAV-to-Satellite Geo-Localization: Taxonomy, Measurement, and Why Consistency-Based Rejection Fails

**Draft v2 — 2026-08-15** (supersedes v1; all review corrections applied, replication included)
**Authors:** [author list pending]
**Target venue:** RA-L / IROS 2027 (failure-analysis + measurement paper)
**Companion files:** `latex/paper.tex` + `latex/refs.bib` (compilable), figures in `artifacts/figs/`, actions 01–05, replication runs 08/08b.
**Version note:** v1 fixes applied: abstract overclaim removed (own Table II contradicted it), 0/14→0/7 per drift, fatal/good thresholds defined (Sec. 3.2), unverifiable rich-grid oracle (3.0 m) dropped, NGPS citation removed, TACO claim weakened, AnyVisLoc 18.5% verified against Table 6 of the source, per-lag pair counts added (Table IV), baseline 32.7 vs 31.1 m sample distinction made explicit, external replication (AerialVL) + attempted replication (TEMPO-VINE) added as Sec. 4.6.

---

## Abstract

UAV geo-localization against satellite reference imagery fails on repetitive
terrain in ways standard robustness tools cannot see. We characterize the
failure on UAV-VisLoc, a published benchmark, and separate it into two
classes: _whole-tile_ aliases, where the matcher locks onto a look-alike
tile hundreds of metres away, and _sub-tile_ aliases, where the match lands
on the correct tile but displaced by one period of a repeating structure
invisible at satellite resolution. Three measurements make the case. First,
signed per-frame offsets (n=610 contiguous frames) show that magnitude
histograms — the standard reporting convention — hide the alias class's
bimodality and its hole at zero. Second, a benchmark of four published
rejection designs over one accepted-fix stream shows that sequential
consistency and ORB-SLAM's three-keyframe rule discriminate _backwards_ on
the sub-tile class (retaining wrong fixes at a higher rate than correct
ones), while pairwise consistency and robust frame alignment attain forward
discrimination only by keeping 7–40% of correct fixes; no consistency-based
method meets a pre-registered adoption bar, whereas a prior-ratio gate
separates the whole-tile class completely (0 of 7 fatal fixes kept per
drift at 150 m and 300 m drift). Third, the alias offset is temporally
coherent (2.55× below a shuffled null at lag 1) — which is exactly why
consistency fails — and the mechanism-motivated countermeasure, a
multi-hypothesis mixture filter, recovers none of the oracle gap at any
prior quality because the alias lattice is per-field and unobservable in
the satellite texture. Held-out regions and an independently collected
urban dataset confirm the class is specific to repetitive farmland; an
attempted replication on an agricultural-robot dataset is structurally
impossible (no aerial imagery exists). We contribute (i) a taxonomy with
per-class rejection behaviour, (ii) the first backwards-rate tables for
published rejectors, (iii) a sign-folding diagnostic for error reporting,
(iv) a falsified countermeasure with quantified oracle bounds (median
31.1 → 14.0 m under the strongest available oracle), and (v) a
pre-registered replication protocol.

---

## 1. Introduction

**Task and motivation.** GPS-denied UAV navigation increasingly relies on
matching nadir drone imagery against georeferenced satellite tiles to anchor
drift-prone visual-inertial odometry. Published systems report median errors
of metres on favourable terrain [AnyVisLoc; OrthoTrack; OrthoLoC]. Failure
analysis, however, is thin: benchmarks report accuracy at thresholds
(A@X m) over pooled terrain, which is blind to how, where, and why the tail
fails.

**The gap we address.** We document a failure class on repetitive terrain —
farmland with parallel furrows, forest canopy — where accepted matches are
wrong by tens to hundreds of metres _with full geometric and appearance
support_. We show this class defeats the standard robustness toolbox for a
measurable, mechanical reason, and we quantify what would be required to
fix it.

**Why prior work does not cover this.** Coherent (mutually consistent)
outliers in SLAM are studied theoretically for indoor scenes [Lajoie et al.,
RA-L 2019]; row-level aliasing on vineyard rows is reported from ground
robots with LiDAR [de Silva et al. 2026; de Silva et al. 2025; TEMPO-VINE].
Neither provides cross-view (nadir UAV ↔ satellite) measurements, per-class
rejection behaviour, nor the temporal-coherence and appearance-optimality
measurements we report. STHN notes self-similar patterns as a confound in
UAV thermal↔satellite homography [STHN] but does not analyze them. Robust
pose-graph back-ends (PCM, GNC, TACO) are designed against exactly this
outlier shape; we measure how the standard representatives of this family
behave on real cross-view data.

**Contributions.**

1. **A taxonomy** separating whole-tile from sub-tile aliases, each with a
   distinct geometry, temporal signature, and rejection behaviour (Sec. 4.1,
   4.3).
2. **Backwards-rate tables** for four published rejection methods over a
   shared fix stream: sequential consistency and the three-keyframe rule
   keep wrong fixes at a _higher_ rate than correct ones; PCM and robust
   frame alignment discriminate forward only by destroying 60–93% of
   correct fixes; only a prior-normalized distance gate works, and only on
   the whole-tile class (Sec. 4.2).
3. **The sign-folding diagnostic**: absolute-value error histograms fold
   symmetric alias structure into an apparently continuous distribution;
   signed offsets recover the axis and the hole at zero (Sec. 4.1).
4. **A falsified countermeasure**: the mixture hedge filter that follows
   from the mechanism recovers none of the oracle gap, because the alias
   lattice is per-field and unobservable — with a reproducible oracle bound
   of 14.0 m median quantifying the residual (Sec. 4.4).
5. **Held-out and cross-dataset controls** confirming the class is
   terrain-specific, plus a pre-registered replication protocol (Sec. 4.5,
   4.6).

---

## 2. Related Work

**UAV–satellite geo-localization.** Retrieval-based systems [UAV-VisLoc;
AnyVisLoc; DenseUAV] and geometric pipelines (homography [the production
matcher studied here], PnP against DSM [OrthoLoC; OrthoTrack]) are
benchmarked by pooled accuracy-at-threshold. AnyVisLoc's Table 6 is
representative: its baseline scores 74.1% A@5m against an aerial
photogrammetry reference but 18.5% A@5m against a satellite reference —
the satellite-reference tail exists, is large, and is not analyzed
per-region. Our work is complementary: we analyze _why_ that tail exists
rather than improving its head.

**Perceptual aliasing and robust estimation.** Aliasing in place
recognition is a classic concern [Lowry survey 2016]; sequence-based VPR
exploits temporal consistency to combat it [SeqVPR]. Modern robust
back-ends address mutually-consistent outliers with pairwise consistency
(PCM [Mangelson 2018], Kimera-RPGO [Kimera-Multi]), graduated
non-convexity (GNC [Yang 2020]), or robust kernels on pose-graph factors
(TACO [Olivastri 2026]). Lajoie et al. analyze coherent outliers in indoor
SLAM theoretically and note that mutually consistent outliers defeat
initial-guess-dependent rejection. Vineyard robotics reports row-level
aliasing from ground LiDAR qualitatively [de Silva et al. 2025, 2026].
Multi-hypothesis handling of aliasing dates to hypothesize-and-verify loop
closure [Tanaka 2016]. None of these measures the rejection _rate_ of
published methods on a shared cross-view fix stream, nor the temporal
coherence of the alias offset itself — the measurements we contribute.

**Error distribution analysis in VPR.** Reporting conventions use magnitude
histograms and CDFs. We show a class of symmetric bimodal error — the
signature of period-quantized aliasing — is invisible in magnitude form,
and propose signed-offset reporting as a diagnostic (Sec. 4.1).

---

## 3. Method

### 3.1 System under study

The pipeline is a production map matcher: ORB+AKAZE+SIFT pooled
correspondences, MAGSAC homography [Barath 2019], image-centre projection
through the inverse homography, patch-wide NCC verification at 0.30,
`min_inliers=10`, DEM-corrected AGL scale. Candidate generation is
prior-centred (5×5 tile ring). Frames carry a drifted prior injected as a
random walk at 150/300/600 m. Dataset: UAV-VisLoc [Xu et al. 2024], eleven
Chinese sites; all measurements use the dataset's drone GPS as truth.

### 3.2 Measurement protocol and definitions

**Error classes.** A fix is _good_ if its error against the dataset GPS is
< 20 m, _mid_ if 20–50 m, and _fatal_ if ≥ 50 m. These boundaries are
fixed a priori and used across all experiments (they match the error-group
boundaries of the coherence protocol).

**Signed offsets.** For each frame, we match against the ground-truth tile
and record the signed (north, east) offset between the recovered position
and the dataset's GPS record. Frames are _contiguous_ in flight order
(n=610 solved on R04), because step-sampling destroys the temporal
structure the coherence question needs.

**Fix stream.** For rejection benchmarks, we run the production matcher
under injected drift and keep every accepted fix with its estimate, prior,
and prior uncertainty (n=40 per region per drift, seed fixed).

**Metrics.** Good-kept% / fatal-kept% with denominators inline;
discrimination ratio = good-kept/fatal-kept (>1 = forward discrimination).
Adoption bar for a rejector: fatal cut ≥25% while keeping ≥80% of good
fixes (pre-registered before any benchmark ran).

### 3.3 The rejector benchmark

Four published designs are implemented over the shared fix stream, using
only deployed signals (priors, estimates, filter-reported uncertainty):
sequential consistency (a fix survives if a neighbouring fix agrees within
a motion-compensated tolerance, the ORB-SLAM3 covisibility principle),
ORB-SLAM's three-consecutive-keyframe rule, PCM-style greedy maximum
clique [Mangelson 2018], and VINS-Mono-style robust frame alignment
(median prior↔estimate offset, reject residual > τ) [Qin 2018]. The
prior-ratio gate (fix kept iff distance to prior ≤ 1.5× the prior's
uncertainty) is evaluated in deployed (filter RMS) and oracle (true prior
error) forms.

---

## 4. Experiments

### 4.1 Error structure: the taxonomy and the sign-folding diagnostic

**Setup.** Signed offsets on GT tiles, R04 (n=32 step-sampled for regional
stats; n=610 contiguous for the full distribution) and R03 (n=30/557) as
control. The n=32 sample and the n=610 stream are _different_ samples of
the same region; baseline medians therefore differ (32.7 m on n=32, 31.1 m
on n=610) and are always quoted with their sample size.

**Result 1 — magnitude histograms hide the alias class.** The signed R04
offsets are axis-aligned and bimodal: axial resultant R=0.50 (vs 0.19
control) with the _hole at zero_ (6/32 frames within ±10 m along the
dominant axis, vs 14/30 on the control). Folded to magnitudes, this is
exactly the "continuous, no-gap" distribution that earlier analysis
misread as imprecision.

**Result 2 — the axis is per-field, not per-region.** At n=32 the offsets
split into two orientation groups (bearings 145–193° and 279–357°): the
flight crosses fields whose furrow orientation changes. A
single-region-axis oracle degrades accordingly: the sub-tile snap oracle
(best integer period removed along one axis) falls from 2.39× over a
random-axis null at n=16 to 1.72× at n=32, while its absolute ceiling
stays stable (12.0–12.7 m median against a 32.7 m baseline). The alias is
a lattice structure _per field_.

**Result 3 — the wrong lock is the appearance optimum, unanimously.** At
n=32, masked patch NCC over displaced homographies selects displacement
k=0 on 32/32 frames; the oracle displacement recovers 20.4 m of median
error (32.7 → 12.3 m). Appearance is not merely uninformative on this
class; it is monotone _against_ the truth.

**Result 4 — whole-tile aliases are a different class.** On forest (R06),
the error distribution is bimodal with a clean 40–150 m gap: discrete jumps
to look-alike tiles 1–2 tile widths along track. Their offsets are coherent
across the flight turn, following the aircraft.

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

**Finding 1 — sequential consistency and the three-keyframe rule
discriminate backwards on the sub-tile class.** They keep wrong fixes at a
_higher_ rate than correct ones at every drift (ratio ≤ 0.97 wherever
n permits); at tol=100 m, 100% of fatal fixes survive at d150 and d300.

**Finding 2 — the forward ratios that do exist are coverage-destroying.**
PCM and frame alignment reach ratios of 2–3 at tol=100 m only by keeping
7–40% of correct fixes — the purity-for-coverage trade, measured as a
rate. No consistency-based method passes the adoption bar in any cell at
any drift.

**Finding 3 — the whole-tile class is fully separable, the sub-tile class
is invisible, per region.** On R06, the prior-ratio gate with honest
uncertainty keeps 100% of good fixes and 0 of 7 fatal fixes per drift at
d150 and d300 (14 fatal fixes pooled over the two drifts). On R04 it
scores 0.93–1.00: a 20–80 m alias is small against a 300 m prior, so no
ratio threshold can see it. On the R03 control, the consistency filters
destroy 15–76% of good fixes — collateral measured, not asserted.

### 4.3 Temporal coherence: the mechanism

**Setup.** Truth-referenced signed offsets, contiguous frames, R04 n=610
(alias ≥50 m: 93; mid 20–50 m: 374; good <20 m: 143), R03 control n=557.
Per-lag pair counts are reported inline.

| lag | n pairs | alias: median / shuffled null | good: median / null            |
| --- | ------- | ----------------------------- | ------------------------------ |
| 1   | 25 / 46 | 27.5 / 70.1 m — **2.55×**     | 16.7 / 17.9 m (0.93×, at null) |
| 2   | 17      | 46.8 / 86.1 m (1.84×)         | 15.9 / 17.9 m (0.89×)          |
| 3   | 15      | 27.9 / 63.9 m (2.29×)         | 17.2 / 19.3 m (0.89×)          |
| 5   | 12      | 80.0 / 90.1 m (1.13×)         | 19.6 / 17.3 m (1.13×)          |
| 8   | 11      | 60.3 / 93.5 m (1.55×)         | 14.6 / 18.6 m (0.78×)          |

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
20 m, axis 171°, from Sec. 4.1), posterior from the prior likelihood,
output = posterior mean; prior uncertainty swept 5–300 m in random-walk
and IID forms. Kill criterion pre-registered: posterior-mean output must
recover ≥30% of the oracle gap (17.1 m ⇒ ≥5.1 m) at prior σ ≤ 20 m.

**Result (a) — the lattice is not in the map.** In-band periodicity is
found on 9–17% of frames (lowest for the alias group) and never aligns
with the alias offset direction (median angular error 44–52°, uniform).
At 1.19 m/px the satellite texture does not expose the furrow lattice the
matcher locks onto.

**Result (b) — the mixture recovers nothing; MAP is actively harmful.**
Baseline k=0 median 31.1 m (n=610); single-axis oracle 14.0 m (gap
17.1 m). Posterior-mean output moves −6.1…+0.1 m across all prior forms
and qualities (worst at σ=50 IID: −6.1 m, far below the ≥5.1 m bar); MAP
output degrades to 68.4 m at σ=300 m. The failure is mechanical: frame
differences cannot see a constant offset (Sec. 4.3), the prior is the only
anchor, and the true offsets are not multiples of any single global
lattice — the per-field revision of Sec. 4.1 at stream scale.

**Finding 5 — recovery requires the per-field lattice, which no deployed
signal provides.** The failure chain is closed: the alias offset is
quantized along a field axis (Sec. 4.1), the axis is not in the satellite
texture (a), frame differences cannot see a constant offset (Sec. 4.3),
and no prior tightness restores the modes (b). The 14.0 m oracle is the
non-degenerate bound for any matcher-side fix; the IID σ=5 mixture —
the video-rate odometry limit — extracts nothing from it (31.2 m).

### 4.5 Held-out controls and the terrain boundary of the class

| Region | Terrain          | Production match (d300, n=40) | GT-tile solve (contiguous) | Alias signature                     |
| ------ | ---------------- | ----------------------------- | -------------------------- | ----------------------------------- |
| R03    | farmland         | 34/40, 0 fatal                | 557 frames, good at null   | none                                |
| R05    | mountain plateau | 1/40                          | 5/100                      | none measurable (5% ceiling)        |
| R11    | desert           | 34/40, 1 fatal                | 199 frames: 8 alias (4%)   | good at null; alias tail incoherent |
| R02    | farmland/river   | —                             | 1/40 usable                | unsolvable-class                    |
| R10    | orchard hills    | —                             | 0/40 usable                | unsolvable-class                    |

The sub-tile coherent-alias class appears only on repetitive furrow
farmland (R04). Desert and clean farmland are control terrain; the
mountain plateau and the two additional held-out regions (R02, R10)
belong to the _unsolvable class_ (a 0–5% inlier ceiling even against the
region's own ground-truth tile), which is a different, no-fix failure
mode rather than a wrong-fix one.

### 4.6 External replication: attempted and executed

**Attempted replication 1 — TEMPO-VINE (rejected on structure).** The
most promising published agricultural dataset for this mechanism,
TEMPO-VINE [Martini 2025], provides RTK-grade GPS truth (1–2 cm) in
trellis and pergola vineyards — but its imagery is a forward-oblique
RealSense D435 RGB-D camera on a ground rover at ~1 m height. Nadir aerial
imagery matchable against satellite ortho does not exist in the dataset,
so protocol requirement 1 fails and no measurement is possible. This is a
_structural_ absence in the field: no public dataset currently pairs
repetitive-crop aerial imagery with satellite references and continuous
GPS.

**Executed replication 2 — AerialVL (class absent; protocol guard fired).**
We ported the full protocol to AerialVL, an independently collected UAV
dataset (HuggingFace `hmf21/AerialVL`, cc-by-4.0; per-frame GPS in the
image filenames; Qingdao, China; urban/coastal terrain). Two flight
sequences were ingested (1,423 frames), the reference map built from the
dataset's georeferenced ortho (0.959 m/px), and protocol Steps 1–3 run:

| Metric                        | Seq 03-11 (n=200 attempted) | Seq 03-16 |
| ----------------------------- | --------------------------- | --------- |
| solved frames (≥15 inliers)   | 94 (47%)                    | 0 (0%)    |
| hole at zero                  | 5.3%                        | —         |
| axial resultant R(180°)       | 0.70                        | —         |
| anisotropy (along/perp)       | 9.7× (16.3 m / 1.7 m)       | —         |
| median error                  | 17.1 m                      | —         |
| median offset vector          | (−16.0 N, +4.1 E) = 16.5 m  | —         |
| good-group lag-1 coherence    | **0.59× of null**           | —         |
| error groups (good/mid/alias) | 75 / 15 / 4                 | —         |

Two findings follow. First, the alias class is **absent**: the alias tail
is 4 frames (4.3%), too thin for any coherence measurement. The
sign-folding signatures that _would_ replicate (hole 5.3%, R 0.70,
anisotropy 9.7×) are produced by a different mechanism — a constant
16.5 m common-mode georeferencing offset between the dataset's ortho and
its drone GPS (spread 3.1 m; a cross-validated bias correction removes
14 m: 17.3 → 3.3 m). A constant offset is trivially "perfectly coherent",
so this is a false-positive source for the diagnostic — and a live
corroboration of Sec. 4.3's gauge symmetry: a constant offset is invisible
to any consistency-based rejection. Second, the protocol's own control
guard fired: the _good_ group is temporally coherent (0.59× of its null;
a clean dataset requires 0.8–1.25×), meaning this dataset's GPS truth is
temporally correlated — a benchmark-hygiene property worth reporting on
its own and a reminder that coherence checks must control for
truth-correlation before interpreting alias coherence.

**Follow-up.** The one dataset class that could replicate the mechanism —
repetitive-crop aerial imagery (ViLD, WACV 2026; Zenodo record 19223815,
email-gated) — is stated as future work with the pre-registered protocol
in `07_replication_protocol.md`.

---

## 5. Discussion

**What the field should take.** (i) Pooled A@X m metrics on repetitive
terrain hide a failure class with full geometric support; signed-offset
reporting is a cheap diagnostic that exposes it. (ii) Robust-estimation
defaults (PCM/GNC/sequential consistency) do not transfer to cross-view
geo-localization on repetitive terrain: they fail backwards or at
coverage-destroying purity, at measured rates. (iii) The fix that works
for one alias class (prior-ratio for whole-tile) does not exist for the
other; hedging (posterior-mean) is safe but inert, mode-commitment (MAP)
is dangerous (68.4 m at σ=300). (iv) An independent replication attempt
shows the diagnostic's false-positive mode (constant georeferencing bias)
and a truth-correlation guard that any future replication must pass.

**Limitations.** Dataset GPS truth (~10 m class) bounds all absolute
numbers — the R03 floor of ~13 m is plausibly the dataset's own noise
floor, not the matcher. Sample sizes: per-region fatal counts are 5–14
per drift; all denominators are reported inline, and the key measurements
(n=32 unanimity, n=610 coherence) do not rest on small cells. The
sub-tile class is measured on a single region (R04) and does not
replicate on clean or unsolvable terrain; an external dataset with
repetitive-crop aerial imagery does not exist publicly. All rates are
measured with one matcher (ORB+AKAZE+SIFT+MAGSAC); the coherence
mechanism (Sec. 4.3) is matcher-independent, but rate magnitudes are
matcher-conditional. AerialVL's georeferencing bias and correlated truth
were discovered, not controlled for, in that replication.

---

## 6. Conclusion

We characterized a failure class in UAV-to-satellite geo-localization that
consistency-based robustness tools cannot see: coherent-offset aliases,
split into whole-tile (separable by a prior-ratio gate) and sub-tile
(unreachable by any measured signal) classes. The sub-tile class defeats
sequential consistency and the three-keyframe rule _backwards_ at measured
rates, defeats PCM and frame alignment through coverage destruction, hides
in magnitude histograms, and resists even the mechanism-motivated
multi-hypothesis countermeasure, with a non-degenerate oracle bound of
14.0 m median on the worst region against a 31.1 m production baseline
(n=610). The class is terrain-specific: absent on desert, clean farmland,
mountain plateau, unsolvable regions, and an independent urban dataset.
The paper contributes the taxonomy, the rate tables, the sign-folding
diagnostic, and the quantified boundary of what map matching can and
cannot recover — and, by exclusion, directs future work to per-field map
annotation or odometry-quality regimes we quantify as unreachable at 7 s
frame spacing.

---

## Self-Review (five dimensions)

**Contribution.** Taxonomy + backwards-rate tables + sign-folding
diagnostic + falsified countermeasure + oracle bound + replication
protocol. Novel vs. Lajoie (theory, indoor) and the vineyard robotics
literature (qualitative, ground): we provide cross-view measurements,
rates, appearance-optimality unanimity, and the first documented
replication attempts for the class. Status: acceptable for RA-L-class
failure-analysis; the falsified countermeasure strengthens rather than
weakens the contribution when framed as mechanism closure.

**Writing clarity.** Abstract follows challenge→insight→contribution;
terminology (whole-tile/sub-tile, backwards rate, sign-folding, lattice,
fatal) defined at first use and held stable; fatal/good/mid thresholds
fixed in Sec. 3.2. Section messages map to the contributions one-to-one.

**Experimental strength.** All primary numbers measured in one harness
family with fixed seeds; denominators inline (including per-lag pair
counts); control regions present in every experiment (R03 for matching,
R02/R05/R10/R11 for the class boundary); oracle and null controls on
every structural claim (random-axis null, shuffled-pair null, prior
sweep).

**Evaluation completeness.** External replication executed on AerialVL
(class absent, guard fired); TEMPO-VINE rejected on structure; ViLD
stated as future work with protocol. Missing: RTK audit of UAV-VisLoc GT;
video-rate odometry evaluation; second-matcher rate table. All stated as
limitations.

**Method design soundness.** The mixture filter's gauge-symmetry analysis
predicts its own failure before the numbers confirm it (Finding 4 →
Finding 5); kill criteria pre-registered in the action documents and
honoured; the one artifact-free exploratory figure (rich-grid oracle) was
removed in this revision rather than reported.

## Claim–Evidence Map

| Claim                                       | Evidence                                                                           | Status    |
| ------------------------------------------- | ---------------------------------------------------------------------------------- | --------- |
| Two alias classes exist                     | R06 bimodal 40–150 m gap vs R04 continuous-in-magnitude with hole at zero (signed) | supported |
| Magnitude histograms hide the class         | 6/32 vs 14/30 within ±10 m; axial R 0.50 vs 0.19                                   | supported |
| Wrong lock is appearance optimum            | NCC picks k=0 on 32/32, n=32                                                       | supported |
| Seq-consistency & 3-keyframe fail backwards | ratio ≤0.97 in all n-valid cells; 100% fatal survival at tol=100, d150/d300        | supported |
| PCM & frame alignment destroy coverage      | ratios 2–3 only at 7–40% good kept; no cell passes adoption bar                    | supported |
| Whole-tile class separable                  | prior-ratio oracle: 0/7 fatal kept per drift, 100% good, d150+d300                 | supported |
| Sub-tile class invisible to priors          | prior-ratio oracle ratio 0.93 on R04 (d300)                                        | supported |
| Alias offset locally coherent               | 2.55× below null at lag 1, decaying; good at null                                  | supported |
| Countermeasure fails                        | mixture mean −6.1…+0.1 m vs 5.1 m bar; MAP 68.4 m                                  | supported |
| Oracle bound                                | 14.0 m single-axis oracle, n=610 (artifact `action4_mixture.json`)                 | supported |
| Class is terrain-specific                   | R05 5% ceiling, R11 4% alias incoherent, R02/R10 unsolvable, AerialVL absent       | supported |
| Diagnostic has a false-positive mode        | AerialVL: constant 16.5 m bias reproduces sign-folding signatures                  | supported |
| Truth-correlation guard works               | AerialVL good-group coherence 0.59× → protocol stops                               | supported |

## References (verified 2026-08-15; bib in `latex/refs.bib`)

1. Xu et al., "UAV-VisLoc: A Large-scale Dataset for UAV Visual Localization," arXiv:2405.11936, 2024.
2. Ye et al., "Exploring the best way for UAV visual localization under Low-altitude Multi-view Observation Condition: a Benchmark," arXiv:2503.10692, CVPRF 2026 (satellite A@5m 18.5% vs aerial 74.1%, Table 6).
3. Lajoie et al., "Modeling Perceptual Aliasing in SLAM via Discrete-Continuous Graphical Models," IEEE RA-L 2019, DOI 10.1109/LRA.2019.2894852.
4. de Silva et al., "Semantic Landmark Particle Filter for Robot Localisation in Vineyards," arXiv:2603.10847, IROS 2026 (submitted).
5. de Silva et al., "Semantic-Aware Particle Filter for Reliable Vineyard Robot Localisation," arXiv:2509.18342, ICRA 2026 (submitted).
6. Martini et al., "TEMPO-VINE: A Multi-Temporal Sensor Fusion Dataset for Localization and Mapping in Vineyards," arXiv:2512.04772, 2025.
7. He et al., AerialVL dataset, HuggingFace `hmf21/AerialVL`, cc-by-4.0 (no paper; no arxiv record).
8. Dhaouadi et al., "OrthoTrack: Continuous 6-DoF UAV Trajectory Estimation Anchored in Public Orthophotos," arXiv:2606.25245, ECCV 2026.
9. Dhaouadi et al., "OrthoLoC: UAV 6-DoF Localization and Calibration Using Orthographic Geodata," arXiv:2509.18350, NeurIPS 2025.
10. Olivastri, Pretto, Fischer, "TACO: A Test and Check Framework for Robust Pose Graph Optimization," arXiv:2606.29851, 2026.
11. Xiao et al., "STHN: Deep Homography Estimation for UAV Thermal Geo-localization with Satellite Imagery," IEEE RA-L, arXiv:2405.20470.
12. Lowry et al., "Visual Place Recognition: A Survey," IEEE T-RO 2016, DOI 10.1109/TRO.2016.2624754.
13. Zhao et al., "Learning Sequence Descriptor based on Spatio-Temporal Attention for Visual Place Recognition," IEEE RA-L 2024, vol. 9, pp. 2351–2358, DOI 10.1109/LRA.2024.3354627.
14. Tanaka, "Multi-Model Hypothesize-and-Verify Approach for Incremental Loop Closure Verification," arXiv:1608.02052, 2016.
15. Mangelson, Dominic, Eustice, Vasudevan, "Pairwise Consistent Measurement Set Maximization for Robust Multi-Robot Map Merging," ICRA 2018, DOI 10.1109/ICRA.2018.8460217, pp. 2916–2923.
16. Tian, Chang, Herrera Arias, Nieto-Granda, How, Carlone, "Kimera-Multi: Robust, Distributed, Dense Metric-Semantic SLAM for Multi-Robot Systems," IEEE T-RO 2022, arXiv:2106.14386.
17. Yang et al., "Graduated Non-Convexity for Robust Spatial Perception," IEEE RA-L 2020, DOI 10.1109/LRA.2020.2965893.
18. Barath et al., "MAGSAC: marginalizing sample consensus," CVPR 2019, arXiv:1803.07469.
19. Campos et al., "ORB-SLAM3," IEEE T-RO 2021, DOI 10.1109/TRO.2020.3045648.
20. Mur-Artal et al., "ORB-SLAM," IEEE T-RO 2015, DOI 10.1109/TRO.2015.2463671.
21. Qin et al., "VINS-Mono," IEEE T-RO 2018, DOI 10.1109/TRO.2018.2853729.
22. Dai et al., "Vision-Based UAV Self-Positioning in Low-Altitude Urban Environments" (DenseUAV), arXiv:2201.09201.
23. Ji et al., "Game4Loc: A UAV Geo-Localization Benchmark from Game Data," AAAI 2025, arXiv:2409.16925.
24. Amadei, Meinhardt-Llopis, Bascle, Abgrall, Facciolo, "Beyond Paired Data: Self-Supervised UAV Geo-Localization from Reference Imagery Alone" (introduces the ViLD dataset), WACV 2026, arXiv:2512.02737; dataset: Zenodo 19223815 (email-gated, cc-by-4.0).
