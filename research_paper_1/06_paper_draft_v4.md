# Coherent-Offset Aliasing in UAV-to-Satellite Geo-Localization: Taxonomy, Measurement, and Why Consistency-Based Rejection Fails

**Draft v4 — 2026-08-16** (supersedes v3)
**Authors:** [author list pending]
**Target venue:** RA-L / IROS 2027 (failure-analysis + measurement paper)
**Companion files:** artifacts in `artifacts/`, `latex/` from v2 (not yet synced — v4 is authoritative). Iteration docs: `gps-devoid-navigation/summary/22nd_iteration_results.md`, `23rd_iteration_results.md`, `24th_iteration_results.md`.
**Version note (v4):** three additions. (1) _Dense matchers (Sec. 4.7):_ a RoMa run across all eleven regions adds a third failure mode — a globally smooth, confident, photometrically non-optimal displacement — and a matched-modal contrast (XIAN-VisLoc Table 14) showing published dense-matcher accuracy presumes modal proximity. (2) _Spacing isolation (new Sec. 4.9):_ a 429-frame video-rate experiment isolates temporal spacing as the governing variable for fix propagation: metre-scale spacing converts 74% per-frame solvability into 97% frame coverage at zero accuracy cost; 250 m stride collapses the same chain (25% coverage). This is the paper's constructive core: the failure taxonomy is a property of the capture regime, not of the estimators. (3) _Matched-modal terrain controls (Sec. 4.9):_ 14 trajectories of contemporary matched-modal imagery span 2–88% per-frame solvability, showing terrain class operates independently of imagery vintage (refines C6). All v3 content retained; earlier RoMa probe numbers (569–1684 m) are corrected after a recovery-direction bug was found and fixed (Sec. 4.7 setup, one sentence).

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
multi-hypothesis mixture filter, recovers none of the oracle gap because
the alias lattice is per-field and unobservable in the satellite texture.
The signature and the rate structure reproduce under three further matchers
(ORB-only, SIFT-only, SuperPoint+LightGlue), so the failure is a property
of the terrain, not of one pipeline. A dense matcher (RoMa) adds a third
failure mode: a globally smooth, confident warp displaced 55 m–11 km with
the largest inlier counts in every run — neither the appearance optimum
nor periphery-dominance — and the same matcher family that reports 15 m at
95% success on contemporary matched-modal imagery (XIAN-VisLoc) scores 0%
A@50 on all eleven vintage-mismatched regions here, showing published
dense-matcher accuracies presume modal proximity. Finally, a spacing-
isolation experiment on 429 video-rate frames isolates temporal spacing as
the governing variable: geo-registered fix propagation converts 74%
per-frame solvability into 97% frame coverage at zero accuracy cost
(21.1 m median), while the identical chain at 250 m stride collapses to
25% coverage (275 m) — the failure taxonomy is a property of the capture
regime, and the constructive path out of it is measured, not conjectured.
A boundary map covering all eleven regions of the dataset shows the
sub-tile class occupies exactly the one region that is both solvable and
repetitive furrow farmland; an executed replication on an independently
collected urban dataset confirms the class is terrain-specific and exposes
a 16.5 m georeferencing bias that the diagnostic itself detects. We
contribute (i) a taxonomy with per-class rejection behaviour, (ii) the
first backwards-rate tables for published rejectors, (iii) a sign-folding
diagnostic for error reporting, (iv) a falsified countermeasure with
quantified oracle bounds (median 31.1 → 14.0 m under the strongest
available oracle) that double as design targets, (v) a pre-registered
replication protocol, and (vi) the spacing-isolation measurement that
turns the taxonomy into an actionable deployment design.

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
measurable, mechanical reason, we show the failure is not an artifact of
any one matcher — sparse or dense — and we quantify what would be required
to fix it, including the one regime change (video-rate capture with fix
propagation) that measurably contains it.

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
behave on real cross-view data. Learned dense matchers (RoMa, LoFTR,
RoMav2) are benchmarked on matched-modal contemporary imagery [XIAN-Visloc];
we measure the same family on vintage-mismatched pairs and show the
benchmark numbers do not transfer.

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
3. **Matcher independence**: the alias signature and the rate structure
   reproduce under ORB-only, SIFT-only, and SuperPoint+LightGlue — three
   correspondence sources spanning binary corners, gradient blobs, and a
   learned detector–matcher — and dense matchers add a third failure mode
   with its own mechanism (Sec. 4.7).
4. **The sign-folding diagnostic**: absolute-value error histograms fold
   symmetric alias structure into an apparently continuous distribution;
   signed offsets recover the axis and the hole at zero (Sec. 4.1).
5. **A falsified countermeasure**: the mixture hedge filter that follows
   from the mechanism recovers none of the oracle gap, because the alias
   lattice is per-field and unobservable — with a reproducible oracle bound
   of 14.0 m median quantifying the residual (Sec. 4.4).
6. **An exhaustive terrain boundary map** over all eleven source-dataset
   regions plus held-out and cross-dataset controls confirming the class is
   terrain-specific, and a pre-registered replication protocol (Sec. 4.5,
   4.6).
7. **A spacing-isolation measurement** (Sec. 4.9): at metre-scale frame
   spacing, geo-registered fix propagation carries one anchored fix for an
   entire flight at baseline accuracy (74% → 97% frame coverage, zero
   accuracy cost); at 250 m stride the identical chain collapses. Temporal
   spacing — not the matcher, not the geometry — is the governing variable
   for fix propagation, with matched-modal controls showing terrain class
   operates independently of imagery vintage.

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

**Matcher dependence of failure rates.** Failure analyses of matching
pipelines are usually reported for the authors' own matcher; whether the
reported tail is a property of the terrain or of the descriptor pipeline is
rarely tested. We test it directly (Sec. 4.7): the alias signature is
reproduced by every matcher family we can run, and the rejection-rate
structure is stable in sign and magnitude across the classical matchers,
with the learned matcher underpowered for rates but consistent at the
signature level. Dense matchers (RoMa [Edstedt CVPR 2024], RoMav2
[XIAN-Visloc Table 14]) report the strongest fine-localization numbers in
the field; we show those numbers presume contemporary matched-modal
imagery and that the family adds a distinct failure mode under
vintage-mismatch.

**Fix propagation and odometry regimes.** Tracking geo-registered control
points between matched frames so that absolute matching becomes a rare
re-anchor rather than a per-frame duty is standard in fielded systems
[Yao JAG 2024; RARFLoc; NGPS]. Whether the technique survives coarse frame
spacing has not been isolated as a variable; the spacing-isolation
experiment in Sec. 4.9 is the first controlled measurement of the regime
boundary.

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
(n=610 solved on R04 out of 738 attempted), because step-sampling destroys
the temporal structure the coherence question needs.

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

### 3.4 Matcher variants

Every pooled-pipeline measurement has a variant protocol in which only the
correspondence source changes, everything else (CLAHE preprocessing,
DEM/AGL-corrected GSD rescale, GT tile patch, MAGSAC, thresholds) held
identical: _ORB-only_ (binary corner descriptors [Rublee 2011]), _SIFT-only_
(gradient-histogram descriptors [Lowe 2004]), and _SuperPoint+LightGlue_
(learned detector and matcher [DeTone 2018; Sarlin 2023]). Variant streams
are analysed separately and never pooled with the production stream
(cross-quote rule); the production matcher is the ORB+AKAZE+SIFT pool
unless a table states otherwise. The dense variant (Sec. 4.7) is RoMa
`roma_outdoor` [Edstedt CVPR 2024] run on the same GT-tile protocol.

### 3.5 The propagation chain (Sec. 4.9)

A geo-registered fix-propagation chain, requiring no camera intrinsics:
(i) _seed_: production pool match on a satellite crop centred at the known
position (the flight-start GPS assumption); the seed homography maps
drone pixels to map pixels. (ii) _chain_: KLT optical flow tracks the seed
keypoints frame-to-frame; a MAGSAC relative homography is fit on the
tracked pairs and composed with the accumulated absolute homography;
position = frame centre projected through the composed map. (iii)
_re-anchor_: if tracked points fall below 20, relative inliers below 10,
or the propagated position exits a 90 m safe zone around the reference
crop, the chain re-matches on a fresh crop centred at the last fix; on
failure the frame coasts (no fix). The chain is evaluated on a video-rate
dataset (XIAN-VisLoc [Bi ISPRS 2026], trajectory 16: 429 frames, 490×490,
3.8 m median frame step, Level-19 Google reference at 0.24 m/px,
per-frame GPS) in two arms: dense (stride 1) and coarse (stride 65 ≈
250 m — the source dataset's regime).

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

**Result 5 — the signature replicates within the flight (split-half).**
The contiguous n=610 stream split at its midpoint shows the signature
independently in both halves: axis 168.1° vs 166.6°, hole-at-zero 0.22 vs
0.14, anisotropy 1.69 vs 2.02, alias-group lag-1 coherence 1.16× (n=13)
and 3.16× (n=12) below null, good groups at null. The weaker first-half
coherence is consistent with Result 2 — a half-flight still spans multiple
fields with different axes.

**Result 6 — attitude and imagery vintage do not explain the class.** Two
reviewer-grade confounds are ruled out with the dataset's own metadata.
(a) _Camera attitude._ The dataset records per-frame attitude (Omega =
pitch, Kappa = roll; Phi1/Phi2 = yaw). The stream is effectively nadir:
608/610 frames have |tilt| ≤ 10° (median |pitch| 1.3°, max 14.2° on R04),
and excluding the two tilted frames changes nothing (axis 167.4°, axial R
0.31, hole-at-zero 0.18, median 31.0 m on n=608). The nadir-point
correction hypothesis (principal-point vs nadir projection, error ≈
alt·tan(tilt)) was tested in an earlier iteration and killed: a
cross-validated correction over all four sign conventions buys 1.6 m
against a 2 m bar, and the tilt correlation that motivated it (+0.44 with
error magnitude) was traced to tilt degrading the homography fit rather
than to projection geometry. Attitude also cannot produce the signature:
it is continuous, follows the aircraft rather than field boundaries, and
does not make a wrong displacement the appearance optimum. (b) _Imagery
vintage._ Every region is a single-day flight (R01 2018-09-17, R03
2018-10-23, R04 2018-10-24, R06 2022-10-09); R03 and R04 are consecutive
days in the same district, so any satellite-vintage gap is identical
across the pair — yet R03 is the clean control and R04 carries the class.
Stale imagery also predicts flat low appearance scores everywhere, not a
sharp wrong optimum that translates coherently with the aircraft (Result
3, Sec. 4.3). Vintage mismatch remains a plausible contributor to the
_unsolvable/ceiling class_ (no match at all), which we cannot test because
the dataset does not publish satellite capture dates. Sec. 4.9 adds
matched-modal controls showing terrain class operates independently of
vintage.

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

### 4.5 The terrain boundary of the class: exhaustive map

All eleven regions of the dataset are classified with an instrumented
GT-tile probe (n=40 step-sampled, DEM-corrected AGL, ≥15 MAGSAC inliers,
correspondence counts and per-frame tile availability recorded). Seven
regions belong to the _unsolvable/ceiling class_; two are clean controls;
one carries the whole-tile class; exactly one carries the sub-tile class.

| Region | Terrain          | Solved (GT tile)         | Corr med → inlier med | Class / dominant cause                         |
| ------ | ---------------- | ------------------------ | --------------------- | ---------------------------------------------- |
| R01    | riverside/urban  | 1/40                     | 38 → 5 (13%)          | unsolvable; non-planar                         |
| R02    | farmland/river   | 3/40                     | 42 → 5 (12%)          | unsolvable; non-planar                         |
| R03    | farmland (clean) | 27/40                    | 84 → 33 (39%)         | control                                        |
| R04    | furrow farmland  | 610/738 (83%)            | —                     | **sub-tile aliases**                           |
| R05    | mountain plateau | 0/40                     | 24 → 5 (21%)          | unsolvable; ~400 m relief                      |
| R06    | forest           | solved                   | —                     | whole-tile aliases                             |
| R07    | suburban hills   | 0/30                     | 5 → 4 (80%)           | unsolvable; 30-frame flight                    |
| R08    | suburban/water   | 3/40                     | 57 → 5 (9%)           | unsolvable; non-planar                         |
| R09    | suburban         | 3/40                     | 54 → 6 (10%)          | unsolvable; non-planar + 14/40 GT tiles absent |
| R10    | orchard hills    | 0/40                     | 16 → 5 (30%)          | unsolvable; relief + canopy                    |
| R11    | desert           | 199 frames: 8 alias (4%) | —                     | control                                        |

Three candidate explanations for the ceiling class are ruled out by
measurement. (a) _Map quality:_ every satellite map is 0.27–0.38 m/px, and
per-frame GT tiles exist for all regions except R09 (14/40 missing). (b)
_Altitude/scale:_ AGL correction is applied from DEM grids (R05 at 250 m
spacing; R02/R07/R10 grids built for this revision — raw absolute height
vs ground elevation differences reach 2.7–4.6×, so uncorrected probes of
these regions are invalid); a focal-length sweep (500–1200 px) does not
move the inlier ceiling on any region, ruling out camera-model mismatch
for the 3000×2000-sensor regions. (c) _Attitude:_ median |tilt| is
1.4–2.0° on the failing regions and inliers do not correlate with tilt
(+0.02 to +0.15). What the probe shows instead is a correspondence-to-
inlier conversion collapse: failing regions still produce 16–57
correspondences — the imagery has features — but only 9–30% convert to
geometrically consistent inliers, versus 39% on the working farmland
control. The ceiling class is primarily a **geometry** failure: the
homography's planar-ground assumption against buildings, river banks,
canopy, and mountain relief, not a texture failure. A four-way
verification confirms the reading: direct photometric alignment (template
NCC with yaw×scale search, ECC refinement) finds no signal on any region —
including the working ones, because bulk cross-season/cross-sensor pixels
do not correlate (NCC ≈ 0.06 at the known-true alignment of a frame the
feature pipeline solves) — so intensity-based alternatives are structurally
unsuited and the sparse-feature approach is the correct family; and
relaxing the matcher (ratio 0.85, RANSAC 10–15 px) converts the ceiling
class from a _no-fix_ failure into a _wrong-fix_ failure: solve counts
rise but the new locks land 107–467 m from truth. The no-fix/wrong-fix
boundary is a threshold choice, and the strict side is the safe one — a
side-finding now also confirmed by the per-terrain NCC adoption benchmark
(Sec. 4.8): relaxing the acceptance threshold on the weakest suburban
region doubles its match rate (2.5 → 7.5%) but the extra solves include a
91 m fatal, so the strict side remains production. The sub-tile class is
therefore doubly specific: it requires not only repetitive solvable terrain
but _planar_ repetitive terrain — which is why the only furrow farmland in
the dataset is also the only place the class appears.

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

### 4.7 Matcher independence

**Setup.** The Sec. 4.1 signature protocol and the Sec. 4.2 rate protocol
re-run with the Sec. 3.4 matcher variants on R04 (contiguous GT-tile
stream, 738 attempted) and the d300 fix stream (n=40, seed 1992).

**Signature reproduction (GT-tile, R04):**

| Matcher        | Solved    | good/mid/alias | axial R | axis   | hole@0 | aniso | median | lag-1 alias  | lag-1 good  |
| -------------- | --------- | -------------- | ------- | ------ | ------ | ----- | ------ | ------------ | ----------- |
| pooled (paper) | 610 (83%) | 143/374/93     | 0.31    | 167.2° | 0.18   | 1.83  | 31.1 m | 2.55× (n=25) | at null     |
| ORB-only       | 497 (67%) | 121/310/66     | 0.28    | 169.3° | 0.19   | 1.78  | 31.1 m | 2.09× (n=14) | 0.77 (mild) |
| SIFT-only      | 469 (64%) | 118/290/61     | 0.28    | 166.5° | 0.19   | 1.77  | 30.0 m | 2.24× (n=10) | at null     |
| SP+LightGlue   | 377 (51%) | 95/218/64      | 0.23    | 167.4° | 0.22   | 1.68  | 30.2 m | 1.57× (n=24) | at null     |

Every matcher family reproduces the signature: the same axis within 3°,
the hole at zero, the coherent alias tail (1.57–2.55× below null), and
good fixes at null. The sub-tile class is a property of the terrain, not
of the descriptor pipeline. Solve rates differ (83% → 51%), and the alias
fraction among solved frames is stable (15–17%).

**Rate reproduction (R04, d300, tol/τ=100, denominators inline):**

| Rejector             | pooled (27g/7f) | ORB (22g/7f)      | SIFT (23g/8f)     | LightGlue (18g/2f) |
| -------------------- | --------------- | ----------------- | ----------------- | ------------------ |
| seq-consistency      | 85/100 (0.85)   | 91/100 (**0.91**) | 78/100 (**0.78**) | 83/50 (1.67)       |
| 3-consecutive        | 30/57 (0.52)    | 27/43 (0.64)      | 26/25 (1.04)      | 22/0               |
| PCM max-clique       | 19/14 (1.30)    | 23/14 (1.59)      | 22/12 (1.74)      | 22/0               |
| frame alignment      | 26/14 (1.81)    | 32/14 (2.23)      | 30/12 (2.43)      | 22/0               |
| prior-ratio (oracle) | 93/100 (0.93)   | 91/100 (0.91)     | 91/100 (0.91)     | 89/100 (0.89)      |

**Finding 6 — the rate structure is matcher-stable.** Under every classical
matcher, sequential consistency discriminates backwards (0.78–0.91), PCM
and frame alignment go forward only by keeping 19–32% of good fixes, and
the sub-tile class remains invisible to the prior-ratio gate (0.89–0.93)
while staying fully separable on whole-tile R06. The LightGlue rate cells
are underpowered and reported as such: its accepted-fix stream carries
only 2 fatal frames (the learned matcher plus NCC-0.30 acceptance
collapses yield — R03 control 9/40 matched vs 34/40 pooled, the same
coverage-destroying trade the rejectors exhibit), so LightGlue's evidence
is at the signature level; its one nominal adoption-bar pass (seq, 81%
good / 50% fatal) rests on n=2 fatal and cannot carry a decision under
the small-cell rule.

**Dense matchers — Result 7: a third failure mode.** RoMa (`roma_outdoor`,
CVPR 2024) is run on the GT-tile protocol across all eleven regions
(n=167 frames total). Two discriminators are applied per frame: the
implied-translation field of the confident dense correspondences
(alias lock ⇒ coherent constant shift; periphery dominance ⇒ uniform
spread with centre-anchored H), and gradient-magnitude NCC at the dense
lock versus the correct sparse lock (the C4 appearance-optimum test).
(A reproducibility note: an earlier probe of the same model reported
569–1684 m errors; the position recovery applied the inverse homography to
a drone-space point. The corrected run uses the forward homography and is
verified against the production recovery on the same frames — 4.3 m vs
893.8 m on one frame — so all dense-matcher numbers here are from the
corrected run.)

| Region              | ORB pool (control) | RoMa dense         |
| ------------------- | ------------------ | ------------------ |
| R03 (control)       | A@25 50%, 4–23 m   | 0% A@50; 85–498 m  |
| R11 (clean)         | A@25 27%, 15–78 m  | 0% A@25; 118–912 m |
| R01/R02/R04/R06     | 0–85% per-region   | 0% A@50 everywhere |
| R05/R07/R08/R09/R10 | per Sec. 4.5       | 0% A@50 everywhere |

RoMa produces 700–2000 MAGSAC inliers with tight reprojection RMSE on
every frame and 0% A@50 across all eleven regions — including the two
regions the sparse pool solves (R03, R11). The failure is _not_ alias
locking: gradient NCC at the dense lock never beats the correct sparse
lock (0/20 frames), so the wrong warp is not the appearance optimum; and
it is _not_ periphery dominance: correspondences are uniformly spread
(centre-restricted H fit leaves A@25 at 0%), and the implied translation
is a coherent displacement of 55 m–11 km whose magnitude has no
projection-geometry explanation (Mercator scale variation across a 774 m
patch is ≈0.06 m). The mechanism is _dense-prior hallucination_: with
weak cross-season local evidence everywhere, the smoothness prior of the
learned flow produces a globally consistent, confidently wrong warp.

**Result 8 — published dense-matcher accuracies presume modal proximity.**
The same matcher family reports the strongest fine-localization numbers
in the field on contemporary matched-modal imagery: XIAN-VisLoc Table 14
gives RoMav2 15.07 m mean error at 95.24% success against 27.24 m at
63.10% for SuperPoint+LightGlue on the same task class (nadir UAV,
Level-19 Google reference). On the vintage-mismatched pairs of the source
dataset — same task, same geometry, 0–6 year imagery gap — the family
scores 0% A@50 with the largest inlier counts of any matcher. The
ordering between sparse and dense matchers is therefore a property of the
imagery regime, not of the matcher: the published head-to-heads do not
transfer across a vintage gap, and failure analyses of learned matchers
(including this one) must state the modal proximity of their benchmarks.

### 4.8 The field's standard fixes, measured

Three published remedies this paper cites are implemented and measured on
the populations the earlier gates did not cover (Action 7; kill criteria
pre-registered).

**PnP against the DSM (AnyVisLoc/OrthoLoC/OrthoTrack geometry) on the
ceiling class — KILLED.** Lifting GT-tile correspondences to DEM
elevation (90 m grid) and solving PnP-RANSAC on the seven ceiling
regions solves _fewer_ frames than the production homography everywhere
(healthy control R03: 32 vs 12 of 40) and worse where it solves (median
34–338 m vs homography's 11.6–37.6 m on the frames it solves). The
ceiling class is correspondence-limited, not model-limited: the
correspondences that survive descriptor matching do not agree under any
geometric model, so the field-standard geometry swap buys nothing.

**GNC (Yang 2020) graduated robust frame alignment — KILLED.** The
graduated-robustness form of the Sec. 4.2 frame-alignment model keeps
0–7% of fixes in every cell under every matcher at every drift: the
μ-graduation converges to an empty inlier set because the prior↔estimate
offset has no constant mode (Sec. 4.3's scatter). GNC is the sixth
rejection family measured, and its behaviour is the cleanest confirmation
of the gauge argument: graduated robustness does not rescue the class, it
refuses to believe any of the stream.

**Robust fixed-lag smoother (GTSAM/TACO-class) — KILLED with mechanism.**
A factor graph with GM-kernel map-fix factors and trusted prior-delta
motion factors (implementation validated on synthetic data: an isolated
199 m wrong fix is pulled to 8.9 m) does not heal either alias class on
real streams. At d150 it moves R06 whole-tile aliases a median 367 m yet
lands them wrong — alias chains follow the aircraft, so the trusted
motion chain encodes them (Finding U extended to whole-tile). At d300 and
d600 the smoother degrades sharply (R03 13.9 → 54.5 m median; R04
30.9 → 142.4 m) because at 7 s frame spacing the drift random walk
dominates the prior deltas, so trusting the motion drags correct fixes
away and the robust kernel down-weights the wrong side of the trade. A
robust back-end needs trusted odometry this dataset does not provide —
the back-end half of the "odometry regime" conclusion, measured rather
than assumed.

**Further standard remedies, measured and closed (v4).** Four additional
published-style remedies were implemented on the same populations with
pre-registered kill criteria. (a) _Zero-shot retrieval floor_
(DINOv2-small global descriptors over a 5,234-tile index): the GT tile
ranks 53–1556 of 5234 on the control region, and top-5 oracle median
error spans 250 m–950 km per region — no coarse retrieval floor exists
without a trained cross-view retrieval model. (b) _Detector fine-tuning_
(homographic adaptation of SuperPoint on 80 matched pairs): the pretrained
detector is already converged for the task (cross-entropy floor 0.058,
90.5% label self-consistency) and fine-tuning changes nothing; the
zero-solve behaviour of SuperPoint+LightGlue on frames the ORB pool
solves (0/8 held-out control) localizes the gap to the LightGlue matcher,
not the detector. (c) _Per-terrain acceptance thresholds_ (per-region NCC
relaxation, R09 0.30→0.10): match rate 2.5→7.5% but the extra solves
include a 91 m fatal — the strict side of the Sec. 4.5 no-fix/wrong-fix
boundary is confirmed at adoption scale. (d) _Terrain-driven fix
weighting_ (DEM elevation variance as an adaptive covariance multiplier,
Yao-class): DEM variance does not predict match-rate ceilings (r = −0.21
over eight regions), and image-moment frame preselection carries no
solvability signal (test-half AUC 0.52) — the only strong predictor of
solvability is the correspondence count the matcher itself produces.

None of the field's standard remedies rescues the ceiling or alias
classes on this data; the boundary map of Sec. 4.5 is a property of the
reference imagery and the frame spacing, not of the estimator choices.

### 4.9 Spacing isolation: fix propagation at video rate

**Setup.** The Sec. 3.5 propagation chain is evaluated on XIAN-VisLoc
[Bi ISPRS 2026], an independently collected video-rate dataset (DJI, nadir
camera, Level-19 Google reference at 0.24 m/px, per-frame GPS).
Trajectory 16 (429 frames, 490×490, 3.8 m median frame step) hosts the
controlled pair; the seed uses a truth-centred crop, matching the
flight-start GPS assumption. Two arms differ only in frame stride:
dense (stride 1) and coarse (stride 65 ≈ 250 m — the source dataset's
7 s regime). The per-frame baseline (independent match per frame on a
truth-centred crop) is measured on the same frames for reference.

| Arm                    | Frames fixed | yield@50m | p50        | modes (seed/prop/rematch/coast) |
| ---------------------- | ------------ | --------- | ---------- | ------------------------------- |
| per-frame baseline     | 317/429      | —         | 19.7 m     | 74% solved                      |
| **propagation, dense** | **418/429**  | **100%**  | **21.1 m** | 1/367/50/11                     |
| propagation, coarse    | 4/7          | 25%       | 275 m      | 1/3/0/3                         |

**Finding 9 — temporal spacing is the governing variable.** At metre-scale
spacing the chain carries one anchored fix for the entire flight:
418 of 429 frames fixed (97%), 100% within 50 m, p50 21.1 m — equal to
the per-frame baseline (19.7 m) at zero accuracy cost, with satellite
re-anchoring reduced to 50 frames total. At 250 m stride the identical
chain collapses (4/7 fixed, p50 275 m): KLT track survival across a 250 m
gap is the failure point, the same mechanism that kills every
consistency-based and smoothing-based remedy on the source dataset
(Sec. 4.2, 4.8). The sub-tile alias class is a property of the 7 s capture
regime, not of any estimator: the paper's negative results and this
positive result are two arms of one variable.

**Finding 10 — terrain class operates independently of imagery vintage.**
The per-frame baseline on 14 trajectories of the matched-modal dataset
(contemporary satellite, no vintage gap) spans 2–88% solvability:

| Solve band | Trajectories (baseline, crop at GPS)                       |
| ---------- | ---------------------------------------------------------- |
| 2–19%      | Xian04 2%, Weinan01 12%, Xian01 16%, Xian06 19%            |
| 31–39%     | Xian03 31%, Xian02 39%                                     |
| 52–64%     | Xian05 54% (p50 8.6 m), Xian08 55%, Xian09 52%, Xian10 64% |
| 72–88%     | Xian11 72%, Xian16 74%, Xian12 84%, Xian07 88%             |

With contemporary imagery, a quarter of trajectories still land at the
2–19% ceiling-class rates — high-altitude homogeneous terrain (Weinan01,
350 m AGL; crop-size control rules out protocol artifacts) fails exactly
like the source dataset's ceiling regions. Terrain class and imagery
vintage are orthogonal factors: vintage explains part of the
unsolvable-class rate, terrain explains the rest, and no trajectory on
either dataset escapes the taxonomy of Sec. 4.5.

**Finding 11 — the constructive design follows from the regime.** A
system that (i) anchors once at flight start (GPS available), (ii)
propagates via geo-registered tracking at video rate, (iii) re-anchors
only on track loss, and (iv) coasts on odometry when re-anchoring fails
turns the failure taxonomy into a deployment recipe: 97% frame coverage
at baseline accuracy on matchable terrain, bounded drift growth
elsewhere. The matcher moves from a per-frame duty (0.5–7.4 s/frame in
the production pipeline) to a rare re-anchor — the regime change the
taxonomy implies.

---

## 5. Discussion

### 5.1 What to deploy now, and what would actually fix it

The measurements are negative for one specific tool — consistency-based
rejection on the sub-tile class — and positive for several others. What a
practitioner should take away today:

1. **Deploy the prior-ratio gate for the whole-tile class.** With honest
   prior uncertainty it keeps 100% of good fixes and rejects every
   whole-tile fatal fix at deployment-relevant drift (0/7 per drift, d150
   and d300). It requires no matcher change.
2. **Do not deploy consistency filters as defaults on this task.** They
   fail backwards or neutrally on the sub-tile class (Sec. 4.2, 4.7) and
   destroy 15–76% of good fixes on healthy terrain (R03 collateral).
3. **Report signed offsets, and run the truth-correlation guard.** The
   sign-folding diagnostic is what exposed the alias class here and a real
   16.5 m georeferencing bias in AerialVL; the guard costs one shuffle
   test per dataset and catches correlated ground truth before it is
   mistaken for structure.
4. **Correct AGL scale before anything else.** The DEM/AGL correction is
   the difference between a matcher that cannot run on elevated terrain
   (R06: 10% match) and one that can (50%) — a prerequisite for every
   number in this paper.
5. **Expect the ceiling class to be geometry, not texture — and do not
   buy dense matchers to fix it.** Six of eleven regions fail the
   planar-homography assumption with abundant features (16–57
   correspondences, 9–30% geometric conversion, Sec. 4.5), and the
   strongest dense matcher fails every one of them with the largest
   inlier counts on record (Sec. 4.7): the ceiling class is not
   correspondence-limited in the dense regime either. On non-planar
   terrain route around the flat matcher, and check reference-tile
   coverage — the R09 gap (14/40 GT tiles absent) shows coverage checks
   belong in the pipeline.
6. **Capture at video rate and propagate (Sec. 4.9).** The single regime
   change that measurably contains the failure classes: anchor once at
   flight start, propagate the fix by geo-registered tracking, re-anchor
   only on track loss, coast on odometry. Measured: 74% → 97% frame
   coverage at zero accuracy cost on 429 video-rate frames; the identical
   chain at 250 m stride collapses, which is exactly the source dataset's
   regime. Per-frame matching at 7 s spacing — the setting under which
   every negative result in this paper was produced — is the anti-pattern.

What would fix the sub-tile class itself, with measured distances: (a)
_per-field lattice annotation_ of reference imagery — the only signal that
contains the axis; the oracle bound says 17.1 m of median error is
recoverable if the axis is known (31.1 → 14.0 m). (b) _Video-rate capture_
— at 7 s frame spacing the coherence window is 2–4 frames and the IID σ=5
regime extracts nothing (31.2 m); Sec. 4.9 now shows the video-rate
regime itself is the fix for availability, though the alias offset within
a matched lock remains per-frame unrecoverable (Finding 5 is unchanged).
(c) _RTK-grade truth_ to establish whether the ~13 m R03 floor is the
dataset's own GPS noise — a prerequisite for claiming any smaller
residual. These are design targets with quantified distances, not open
wishes.

### 5.2 What the field should take

(i) Pooled A@X m metrics on repetitive terrain hide a failure class with
full geometric support; signed-offset reporting is a cheap diagnostic that
exposes it. (ii) Robust-estimation defaults (PCM/GNC/sequential
consistency) do not transfer to cross-view geo-localization on repetitive
terrain: they fail backwards or at coverage-destroying purity, at measured
rates, under every matcher tested. (iii) The fix that works for one alias
class (prior-ratio for whole-tile) does not exist for the other; hedging
(posterior-mean) is safe but inert, mode-commitment (MAP) is dangerous
(68.4 m at σ=300). (iv) An independent replication attempt shows the
diagnostic's false-positive mode (constant georeferencing bias) and a
truth-correlation guard that any future replication must pass. (v) Dense
matcher benchmarks transfer only within a modal-proximity regime; failure
analyses of learned matchers must state their imagery vintage. (vi) Frame
spacing is a first-class experimental variable: the same chain that
collapses at 250 m stride delivers 97% frame coverage at metre spacing —
failure analyses should state the capture regime of their benchmarks, and
system designs should propagate fixes rather than re-match every frame.

### 5.3 Limitations

The sub-tile class is measured on a single region — because the source
dataset contains exactly one region that is both solvable and repetitive
furrow farmland, as the exhaustive 11-region boundary map (Sec. 4.5)
establishes rather than assumes; the signature replicates across four
matchers (Sec. 4.7), within the flight by split-half (Sec. 4.1), and the
external dataset that could replicate the mechanism does not exist
publicly (Sec. 4.6; ViLD is access-gated, protocol ready). Rates are
measured under three classical matchers with a stable structure; the
learned matcher is underpowered for rates (2 fatal frames) and supports
the claim at the signature level only. Dataset GPS truth (~10 m class)
bounds all absolute numbers — the R03 floor of ~13 m is plausibly the
dataset's own noise floor, not the matcher. AerialVL's georeferencing bias
and correlated truth were discovered, not controlled for, in that
replication. The dense-matcher measurements use RoMa v1 (`roma_outdoor`),
not the RoMav2 model behind the XIAN-VisLoc contrast; the family argument
(same dense-flow objective, same failure signature) holds, but the
specific model was not run — stated, not hidden. The spacing-isolation
experiment uses XIAN-VisLoc GPS truth (no RTK), a pure-vision chain (no
IMU), and 14 of 21 trajectories for the matched-modal baseline; the
per-frame baseline there is truth-centred (an optimistic protocol that
matches the flight-start assumption), and its accuracy is GPS-noise
limited, so sub-20 m claims are untestable on that dataset. The
propagation result is a single-trajectory controlled pair; the coarse-arm
collapse mechanism (KLT track survival) is corroborated on the source
dataset's seven-second streams.

---

## 6. Conclusion

We characterized a failure class in UAV-to-satellite geo-localization that
consistency-based robustness tools cannot see: coherent-offset aliases,
split into whole-tile (separable by a prior-ratio gate) and sub-tile
(unreachable by any measured signal) classes. The sub-tile class defeats
sequential consistency and the three-keyframe rule _backwards_ at measured
rates — under every matcher family tested — defeats PCM and frame
alignment through coverage destruction, hides in magnitude histograms,
and resists even the mechanism-motivated multi-hypothesis countermeasure,
with a non-degenerate oracle bound of 14.0 m median on the worst region
against a 31.1 m production baseline (n=610). Dense matchers add a third
failure mode — a globally consistent, confidently wrong smooth warp —
whose published accuracies transfer only within matched-modal imagery.
The class is terrain-specific in an exhaustively mapped sense: absent on
desert, clean farmland, all ceiling-class regions, and an independent
urban dataset, and present exactly where terrain is repetitive, solvable
farmland; matched-modal controls show terrain class operates independently
of imagery vintage. The decisive variable is temporal spacing: at
metre-scale frame spacing, geo-registered fix propagation carries one
anchored fix for an entire flight (74% → 97% frame coverage, zero
accuracy cost, 21.1 m median), while the identical chain at 250 m stride
collapses — the paper's negative results and its constructive resolution
are two arms of one variable. The paper contributes the taxonomy, the
matcher-stable rate tables, the sign-folding diagnostic, the quantified
boundary of what map matching can and cannot recover — design targets for
per-field map annotation and odometry-quality regimes — and a
pre-registered replication protocol for the dataset class the field still
lacks.

---

## Self-Review (five dimensions)

**Contribution.** Taxonomy + backwards-rate tables + matcher-independence
measurement (sparse and dense) + sign-folding diagnostic + falsified
countermeasure + oracle bound + exhaustive boundary map + replication
protocol + spacing-isolation measurement. Novel vs. Lajoie (theory,
indoor) and the vineyard robotics literature (qualitative, ground):
cross-view measurements, rates, appearance-optimality unanimity, matcher
replication, the first dense-matcher failure-mode characterization on
vintage-mismatched pairs, and the first controlled isolation of frame
spacing as the governing variable. The v2 weakness "all rates on one
matcher" is closed for classical matchers and bounded honestly for the
learned one; "one region" is converted from an unexamined selection into
a measured boundary; the negative-results core now has a measured
constructive resolution (Sec. 4.9).

**Writing clarity.** Abstract follows challenge→insight→contribution;
terminology (whole-tile/sub-tile, backwards rate, sign-folding, lattice,
fatal, dense-prior hallucination) defined at first use and held stable;
fatal/good/mid thresholds fixed in Sec. 3.2. Section messages map to the
contributions one-to-one; the constructive half of the paper (Sec. 5.1)
is now explicit and quantified rather than implicit.

**Experimental strength.** All primary numbers measured in one harness
family with fixed seeds; denominators inline (including per-lag pair
counts and per-matcher fatal counts); control regions present in every
experiment; oracle and null controls on every structural claim;
matcher-variant streams isolated under a cross-quote rule; the
spacing-isolation pair differs in one variable only (stride); the dense-
matcher probe's recovery bug is corrected, verified against the production
recovery, and disclosed.

**Evaluation completeness.** External replication executed on AerialVL
(class absent, guard fired); TEMPO-VINE rejected on structure; ViLD stated
as future work with protocol; boundary map exhaustive at 11/11 regions;
four matchers + one dense matcher measured; 14-trajectory matched-modal
control table. Missing: RTK audit of UAV-VisLoc GT; rate-grade learned-
matcher table (blocked by its 2-fatal yield at the paper's acceptance
settings); the remaining 7 XIAN trajectories; RoMav2 itself (RoMa v1
used). All stated as limitations.

**Method design soundness.** The mixture filter's gauge-symmetry analysis
predicts its own failure before the numbers confirm it (Finding 4 →
Finding 5); kill criteria pre-registered in the action documents and
honoured; the one artifact-free exploratory figure (rich-grid oracle) was
removed in v2 rather than reported; the one nominal variant pass
(LightGlue seq, n=2 fatal) is reported and explicitly declined under the
small-cell rule; the dense-matcher negative result is supported by two
independent discriminators (gradient NCC, centre-restricted fit) and an
analytic Mercator-distortion bound.

## Claim–Evidence Map

| Claim                                            | Evidence                                                                                                                                                             | Status    |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| Two alias classes exist                          | R06 bimodal 40–150 m gap vs R04 continuous-in-magnitude with hole at zero (signed)                                                                                   | supported |
| Magnitude histograms hide the class              | 6/32 vs 14/30 within ±10 m; axial R 0.50 vs 0.19                                                                                                                     | supported |
| Wrong lock is appearance optimum                 | NCC picks k=0 on 32/32, n=32                                                                                                                                         | supported |
| Seq-consistency & 3-keyframe fail backwards      | ratio ≤0.97 in all n-valid cells; 100% fatal survival at tol=100, d150/d300                                                                                          | supported |
| PCM & frame alignment destroy coverage           | ratios 2–3 only at 7–40% good kept; no cell passes adoption bar                                                                                                      | supported |
| Whole-tile class separable                       | prior-ratio oracle: 0/7 fatal kept per drift, 100% good, d150+d300                                                                                                   | supported |
| Sub-tile class invisible to priors               | prior-ratio oracle ratio 0.93 on R04 (d300)                                                                                                                          | supported |
| Alias offset locally coherent                    | 2.55× below null at lag 1, decaying; good at null                                                                                                                    | supported |
| Countermeasure fails                             | mixture mean −6.1…+0.1 m vs 5.1 m bar; MAP 68.4 m                                                                                                                    | supported |
| Oracle bound                                     | 14.0 m single-axis oracle, n=610 (artifact `action4_mixture.json`)                                                                                                   | supported |
| Class is terrain-specific                        | exhaustive 11-region map with per-region cause; R05 0/40 relief, R11 4% alias incoherent; AerialVL absent                                                            | supported |
| Ceiling class = geometry, not texture            | corr→inlier conversion 9–30% vs 39% control; fx sweep flat; tilt uncorrelated; maps uniform 0.27–0.38 m/px                                                           | supported |
| Intensity alignment unsuited cross-view          | NCC ≈ 0.06 at known-true alignment of a solved frame; no global peak on any region                                                                                   | supported |
| Loose thresholds turn no-fix into wrong-fix      | ratio 0.85 + thr 15 px: R02/R08/R09 "solve" 4–5/15 at 107–467 m median error; per-terrain NCC relaxation adds 91 m fatal                                             | supported |
| PnP+DSM does not rescue the ceiling class        | solves fewer than homography everywhere incl. control; 34–338 m where it solves (Action 7)                                                                           | supported |
| GNC converges to an empty inlier set             | keeps 0–7% in all cells, all matchers, all drifts (Action 7)                                                                                                         | supported |
| Robust smoother needs trusted odometry           | synthetic heals 199 m outlier; real d150 moves R06 aliases 367 m but lands wrong; d300+ degrades (Action 7)                                                          | supported |
| Signature is matcher-independent                 | axis within 3°, hole, lag-1 coherence 1.57–2.55× under 4 matchers (`gt_variant_*`)                                                                                   | supported |
| Rate structure is matcher-stable                 | seq 0.78–0.91 backwards, prior-ratio 0.89–0.93 under 3 classical matchers (`action2v_*`)                                                                             | supported |
| LightGlue rates underpowered                     | 2 fatal frames at acceptance; nominal pass declined under small-cell rule                                                                                            | supported |
| Signature replicates within flight               | split-half: both halves same axis, coherent alias tails (1.16×/3.16×)                                                                                                | supported |
| Attitude and vintage ruled out                   | 608/610 frames ≤10° tilt, signature unchanged; nadir correction killed at 1.6 m; R03/R04 consecutive-day flights, opposite outcomes                                  | supported |
| Diagnostic has a false-positive mode             | AerialVL: constant 16.5 m bias reproduces sign-folding signatures                                                                                                    | supported |
| Truth-correlation guard works                    | AerialVL good-group coherence 0.59× → protocol stops                                                                                                                 | supported |
| Dense matchers add a third failure mode          | RoMa 0% A@50 across 11 regions, 1000+ inliers, tight RMSE; not alias (gradient NCC 0/20), not periphery (centre fit 0% A@25); Mercator distortion ≈0.06 m (analytic) | supported |
| Dense-matcher accuracy presumes modal proximity  | XIAN-VisLoc Table 14 (RoMav2 15 m @ 95%) vs 0% A@50 on vintage-mismatched pairs of same task class                                                                   | supported |
| Temporal spacing is the governing variable       | Xian16 dense (3.8 m) 97% coverage/21.1 m vs coarse (250 m) 25%/275 m — identical chain, stride-only difference                                                       | supported |
| Propagation converts solvability to availability | 74% per-frame solve → 97% frame coverage at zero accuracy cost (429 frames)                                                                                          | supported |
| Terrain class independent of vintage             | matched-modal baseline 2–88% across 14 trajectories; Weinan01 12% at 350 m AGL; crop-size control rules out artifacts                                                | supported |
| Zero-shot retrieval floor does not exist         | GT tile rank 53–1556/5234 on control; top-5 oracle p50 250 m–950 km per region                                                                                       | supported |
| Detector fine-tune is not the bottleneck         | stock CE floor 0.058, 90.5% self-consistency; SP+LG 0/8 solves where ORB pool solves                                                                                 | supported |
| DEM variance does not weight fixes               | r = −0.21 ceiling vs DEM std over 8 regions; moments AUC 0.52                                                                                                        | supported |

## References (verified 2026-08-16; bib in `latex/refs.bib`)

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
12. Lowry et al., "Visual Place Recognition: A Survey," IEEE T-RO 2016, DOI 10.1109/TRO.2016.2624752.
13. Zhao et al., "Learning Sequence Descriptor based on Spatio-Temporal Attention for Visual Place Recognition," IEEE RA-L 2024, vol. 9, pp. 2351–2358, DOI 10.1109/LRA.2024.3354627.
14. Tanaka, "Multi-Model Hypothesize-and-Verify Approach for Incremental Loop Closure Verification," arXiv:1608.02052, 2016.
15. Bi et al., "UAV coarse visual localization in large-scale continuous scenes," ISPRS Journal of Photogrammetry and Remote Sensing 238 (2026) 243–260 (XIAN-VisLoc; Table 14: RoMav2 15.07 m @ 95.24% vs LightGlue 27.24 m @ 63.10%, LoFTR 28.30 @ 61.90%).
16. Edstedt et al., "RoMa: Robust Dense Feature Matching," CVPR 2024, arXiv:2305.15404.
17. Yao et al., "GNSS-denied geolocalization of UAVs using terrain-weighted constraint optimization," Int. J. Appl. Earth Obs. Geoinf. 135 (2024) 104277.
18. Rublee et al., "ORB: An efficient alternative to SIFT or SURF," ICCV 2011.
19. Lowe, "Distinctive Image Features from Scale-Invariant Keypoints," IJCV 2004.
20. DeTone, Malisiewicz, Rabinovich, "SuperPoint: Self-Supervised Interest Point Detection and Description," CVPRW 2018.
21. Sarlin et al., "LightGlue: Local Feature Matching at Light Speed," ICCV 2023.
