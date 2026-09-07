# Coherent-Offset Aliasing in UAV-to-Satellite Geo-Localization: Measurement and Failure Analysis

**Draft v7 — 2026-09-07** (restructure of v6 per the v7 outline: one central message, mechanism-first, secondary experiments moved to the Supplement; all numbers unchanged from measured artifacts)
**Authors:** [author list pending]
**Target venue:** RA-L (measurement + failure-analysis paper)
**Companion files:** artifacts in `artifacts/` (result JSONs, `figs/` print-size figures), `latex/paper_v7.tex` (submission version). Predecessor: `06_paper_draft_v6.md` (exhaustive record; retained).

## Abstract

UAV geo-localization against satellite reference imagery fails on repetitive terrain in a way standard robustness tools do not visibly catch. We observe that wrong matches can form spatially coherent modes: the estimate sits tens to hundreds of metres from truth, yet consecutive wrong estimates agree with each other. We separate two manifestations — whole-tile aliases (a look-alike tile hundreds of metres away) and sub-tile aliases (the correct tile, displaced by one period of a repeating structure). A two-line model explains the consequence: if the estimate equals truth plus a persistent offset, frame-to-frame relative motion is preserved, so temporal-consistency checks observe nothing wrong. We measure the effect on UAV-VisLoc (6,742 images, 11 regions): signed per-frame offsets (n=610) reveal bimodality with a hole at zero that magnitude histograms hide; sequential consistency and a three-keyframe rule retain wrong fixes at higher rates than correct ones on the sub-tile class, while pairwise and alignment methods discriminate only by discarding most good fixes; the signature reproduces across four matcher families including a dense matcher that adds its own confidently-wrong warp mode; a falsified mixture countermeasure and a 14.0 m oracle bound quantify the residual. Frame spacing governs operability: identical propagation chains deliver 97% coverage at metre spacing and collapse at 250 m stride. A boundary map over all eleven regions, an independent-dataset replication, and a pre-registered replication protocol complete the contribution.

## 1. Introduction

### 1.1 Problem

GPS-denied UAVs anchor drift-prone odometry by matching nadir camera frames against georeferenced satellite tiles. On favourable terrain published systems report metre-level medians. On repetitive terrain — farmland furrows, canopy, dense low-rise repetition — appearance stops discriminating, and a wrong match is most dangerous exactly when it looks geometrically plausible: many inliers, tight fit, high similarity.

### 1.2 The missing failure mode

We observe wrong fixes that are not scattered outliers but a coherent spatial offset, stable across consecutive frames. Two shapes: the matcher locks a visually similar but geographically distant tile (whole-tile alias), or it lands on the correct tile displaced by one period of a repeating structure (sub-tile alias). The error persists rather than flickers.

### 1.3 Why existing rejection may fail

Temporal consistency and geometric consistency checks assume wrong solutions behave differently from the true trajectory. If the wrong solution carries approximately the same offset frame to frame, relative motion still looks correct — and consistency alone cannot expose the error. This is an intuition before it is a measurement; Sections 6–7 test it.

### 1.4 What this paper does

A measurement and failure-analysis study, not a new localizer. We document the coherent-offset class, explain the mechanism in two lines (Sec. 3), measure rejection behaviour of published methods on a shared fix stream, map the terrain boundary, test matcher dependence, and quantify what would be required to fix it — including the one regime change that measurably contains it.

**Contributions.** (1) A whole-tile/sub-tile taxonomy with distinct geometry and behaviour. (2) Backwards-rate tables for four published rejection methods over a shared stream. (3) Matcher independence across four families plus a dense-matcher failure mode. (4) The sign-folding diagnostic. (5) A falsified countermeasure with oracle bound, an averaging bound with its coherent-terrain exception, and a spacing-isolation measurement.

## 2. Related Work (by problem)

**UAV-to-satellite geo-localization.** Retrieval systems and geometric pipelines (homography; PnP against elevation), benchmarked by pooled accuracy-at-threshold. AnyVisLoc's split (74.1% vs 18.5% A@5 m, aerial vs satellite reference) shows the satellite tail is large and unanalyzed per-region — we analyze why it exists.

**Perceptual aliasing.** Repetitive environments and look-alike places are classic in place recognition; sequence VPR exploits temporal consistency against them. Coherent outliers are studied theoretically for indoor SLAM (Lajoie et al., RA-L 2019); vineyard robotics reports row aliasing from ground LiDAR qualitatively (de Silva et al. 2025/2026; TEMPO-VINE; VinePT-Map). Neither provides cross-view measurements, per-class rejection behaviour, or temporal-coherence/appearance-optimality numbers.

**Robust matching and rejection.** RANSAC-family estimators, temporal/pose consistency, graph and frame rejection (PCM, GNC, TACO). Built for mutually consistent outliers in general — we measure the standard representatives on real cross-view streams.

**Dense and learned matching.** Modern sparse matchers (SuperPoint+LightGlue) and dense flow (RoMa, RoMav2, LoFTR). Benchmarked on matched-modal contemporary imagery (XIAN-VisLoc); concurrent LoRetta documents unreliability across acquisition gaps at scale and Sat-RoMa adapts RoMa to multi-temporal pairs — construction-side corroboration of the regime dependence we isolate mechanistically in stock models.

**Gap, stated plainly:** spatially coherent aliasing in UAV-to-satellite localization, its temporal behaviour, and its measured effect on consistency-based rejection.

## 3. Problem Formulation

### 3.1 Setup

UAV frame $I_t$, satellite reference map $M$, estimate $\hat{p}_t$, ground truth $p_t$.

### 3.2 Error: use the signed offset

Position error $e_t = \hat{p}_t - p_t$ as signed (north, east), not $|e_t|$. Magnitude folds symmetric structure into a continuous-looking distribution; Sec. 5 shows the fold hides the class.

### 3.3 Coherent offset (the whole mechanism)

$$\hat{p}_t = p_t + c$$
with $c$ approximately constant over consecutive frames. Then
$$\hat{p}_{t+1} - \hat{p}_t = p_{t+1} - p_t.$$
Relative motion is preserved exactly. Any check that compares consecutive relative motions — sequential consistency, keyframe rules, smoothed residuals — observes agreement between truth and alias alike. The rest of the paper measures how far this two-line model carries in practice.

### 3.4 Alias types

**Whole-tile:** a similar-looking, geographically different tile wins. Offset scale: hundreds of metres (tile widths). **Sub-tile:** the correct tile wins but the lock sits one structure-period off. Offset scale: tens of metres. Both are observed instances of the Sec. 3.3 model at different scales.

## 4. Experimental Setup

| Item       | Setting                                                                                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dataset    | UAV-VisLoc: 6,742 nadir drone images, 11 satellite regions, drone GPS truth (~10 m class)                                                                                       |
| Pipeline   | ORB+AKAZE+SIFT pooled correspondences, MAGSAC homography, centre projection, patch NCC verify 0.30, min-inliers 10, DEM-corrected AGL scale; 5×5 tile ring around drifted prior |
| Priors     | Random-walk drifted priors at 150/300/600 m RMS (never ground truth)                                                                                                            |
| Error cats | good (<20 m), mid (20–50 m), fatal/alias (>50 m)                                                                                                                                |
| Metrics    | position error, signed (N,E) offset, good-kept/fatal-kept rates, coverage, lagged offset difference                                                                             |

## 5. Observation 1 — Coherent aliasing exists (Figs. 1–3)

Failures are not scattered large errors. On R04 farmland, signed offsets (n=610 contiguous frames) form an axis-aligned structure (~167°) with a hole at zero; R03 control (n=34) is unstructured. The same R04 data folded to magnitudes looks continuous (median 31.1 m) — the standard convention hides the class. Whole-tile R06 offsets are bimodal with a 40–150 m gap. Fig. 1 states the model; Fig. 2 draws both alias shapes; Fig. 3 shows the signed-vs-folded contrast. Main observation: incorrect solutions form coherent spatial modes, visible only in signed coordinates.

## 6. Observation 2 — Consistency-based rejection fails (Figs. 4–5, Table 2)

The Sec. 3.3 model predicts consistency tools should accept coherent aliases: relative motion agrees. Measured over one shared accepted-fix stream (255 fixes, three drifts): sequential consistency and the three-keyframe rule keep wrong fixes at higher rates than correct ones (ratios ≤0.97, 100% fatal survival at tol=100 m); PCM and frame alignment score above 1 only by keeping 7–40% of good fixes. No consistency method passes the pre-registered bar (fatal cut ≥25%, good kept ≥80%). Stated as measured behaviour, not as a verdict on the methods: where aliases cohere, consistency cannot separate them. The one gate that works — prior-normalized distance, thresholds 1.5–2.0 — separates only the whole-tile class (0/7 fatal kept per drift) and fails open under miscalibrated uncertainty (keeps everything rather than eating good fixes). R04 ignores it at every setting.

## 7. Observation 3 — The failure is spatially structured (Fig. 6)

R04's alias axis matches the furrow lattice direction; per-field analysis shows the lattice is local (axis/period vary field to field), so no universal geometry is claimed. Concrete instance, frame 04_0487: the lock carries 279 inliers at NCC 0.66 yet sits 51.7 m from truth along the furrows — the wrong answer is the appearance optimum (NCC selects k=0 on 32/32 frames). Fig. 6 shows the drone frame beside the satellite crop with truth and lock marked 51.7 m apart at 50 m scale.

## 8. Observation 4 — Better matching does not remove it (Fig. 7)

Same signature (axis within 3°, hole at zero, coherent tail) under ORB-only, SIFT-only, and SuperPoint+LightGlue; R04 medians 34.2/33.9/26.2 m. Rates are matcher-stable in sign across classical families (learned cells underpowered at 2 fatal frames, reported as such). Dense matching (RoMa, 167 frames, 11 regions) adds a third mode: globally smooth, confidently wrong warps (55 m–11 km) with the largest inlier counts on record — yet the same family reports 15 m at 95% on contemporary matched-modal imagery. Published dense accuracies presume modal proximity. Claim limited to tested matchers and RoMa v1 (adapted variants unrun, stated).

## 9. Observation 5 — Recovery attempts and their bound

Local appearance cannot identify the lock (it is the optimum). A mechanism-motivated mixture filter over lattice hypotheses recovers none of the oracle gap: the lattice is per-field and unobservable in satellite texture (mean −6.1…+0.1 m vs 5.1 m bar; MAP commitment dangerous at 68.4 m). Oracle with known axis recovers 31.1→14.0 m median — the quantified residual, i.e. the boundary between ambiguity and estimator limits.

## 10. Observation 6 — Frame spacing governs operability (Fig. 8)

Identical propagation chains (seed once, KLT-track, re-match on loss) at two strides on 429 video-rate frames: dense (3.8 m) fixes 418/429 at 100% yield@50, p50 21.1 m; coarse (250 m) fixes 4/7 at 25%, p50 275 m. Coverage, not just accuracy: 74%→97% frame coverage at zero accuracy cost. Precision: the metric that moves is availability; within-lock alias offsets remain per-frame unrecoverable (Sec. 9 unchanged). Exploratory regularity over 21 trajectories: dense chains need step ≤~5 m AND solve rate ≥~50% (counterexamples both ways observed; pre-registered validation pending).

## 11. Boundary, dependence, limitations

Terrain: exhaustive 11-region map — class present exactly on repetitive solvable farmland (R04) and whole-tile form on mountain/forest (R06, gated); absent on desert, clean farmland, all ceiling-class regions, and an independent urban dataset (AerialVL, where the protocol instead caught a 16.5 m georeferencing bias — the diagnostic's documented false-positive mode, with a truth-correlation guard). Ceiling class is geometry (9–30% correspondence→inlier conversion vs 39% control), not texture. Matcher: Sec. 8. Dataset: source GPS bounds absolute numbers (~10 m class); R03 floor 11–14 m reproduced by two independent classical matchers (11.4/11.7 m) — dataset-side until RTK says otherwise; spacing experiment uses non-RTK GPS and a pure-vision chain; propagation showcase is one trajectory; dense runs are RoMa v1. ViLD (access-gated) is the designated external replicate with protocol ready.

## 12. Discussion

Established: (1) aliases cohere spatially; (2) coherent offsets preserve relative motion; (3) temporal consistency is therefore insufficient against them — measured backwards/neutral; (4) occurrence follows scene structure; (5) better matching preserves the ambiguity; (6) spacing controls operability. Implications: pooled A@X m hides the class (report signed offsets); robust-estimation defaults need cross-view rate tables before deployment on repetitive terrain; one alias class is separable (prior-ratio), the other currently only survivable (adaptive weighting, odometry coast). Future systems: absolute spatial priors, terrain-aware matching, explicit alias hypotheses, additional sensing — and capture regimes that preserve the continuity their filters assume. What would fix the sub-tile class itself: per-field lattice annotation (17.1 m recoverable), video-rate capture (availability), RTK truth (floor audit).

## 13. Conclusion

Wrong matches in UAV-to-satellite geo-localization can be spatially coherent: stable offsets of tens to hundreds of metres with full geometric and appearance support. Because a persistent offset preserves relative motion exactly, temporal-consistency rejection observes agreement where it should observe disagreement — and does, backwards, at measured rates. The class is terrain-specific, matcher-independent in signature, partly separable (whole-tile) and partly unrecoverable per-frame (sub-tile, 14.0 m oracle residual). Frame spacing decides whether the failure matters operationally: metre spacing contains it through propagation, 250 m stride does not. Design outward from these measurements: report signed errors, gate what is separable, survive what is not, and capture at the rate the filter assumes.

## Supplement

**S1. Field-standard fixes, measured.** PnP+DSM (fewer solves than homography everywhere incl. control), GNC (empty inlier set, 0–7% kept), robust smoother (needs trusted odometry; synthetic-validated, real-degraded), mixture details + gauge-symmetry analysis. Pre-registered kill criteria honoured throughout.
**S2. Retrieval, tuning, weighting negatives.** Zero-shot retrieval floor absent (GT rank 53–1556), homographic fine-tune bottleneck in matcher not detector, per-terrain NCC adoption killed (fatal added), DEM-variance weighting r=−0.21, moment pre-gate AUC 0.52.
**S3. Deployment quantifications.** Fix-averaging bound 21.8→8.0 m at k=10 with R06 non-monotone exception (k5 42.8 vs k1 23.3 m); fail-open gate curve; difficulty decomposition (tile-matched 40/40 at 0.9 m); estimator receipt (weak filter 215.7 m vs ESKF 12.5 m; adaptive-R 40× conservative); R03 matcher pair.
**S4. Replication protocol.** Five steps, exact commands, kill criteria; AerialVL executed, TEMPO-VINE rejected on structure, ViLD pending access.

## Claim–Evidence Map (main claims)

| Claim                                | Evidence                                                                      | Status    |
| ------------------------------------ | ----------------------------------------------------------------------------- | --------- |
| Coherent alias modes exist           | R04 signed axis 167°, hole at zero n=610; R06 bimodal 40–150 m gap            | supported |
| Magnitudes hide the class            | folded R04 continuous (31.1 m) vs signed bimodal                              | supported |
| Relative motion preserved            | model Sec. 3.3; lag-1 alias 2.55× below null, good at null                    | supported |
| Consistency fails backwards/neutral  | ratios ≤0.97 all cells; 100% fatal at tol=100; PCM/align coverage destruction | supported |
| Whole-tile separable                 | prior-ratio 0/7 fatal per drift, 100% good; fail-open curve                   | supported |
| Sub-tile unrecoverable per-frame     | NCC 32/32; mixture −6.1…+0.1; oracle 14.0 m                                   | supported |
| Terrain-specific                     | 11-region map; AerialVL absent (+bias find)                                   | supported |
| Matcher-independent signature        | axis ±3°, hole, tail under 4 families; RoMa third mode 0% A@50                | supported |
| Dense accuracy needs modal proximity | RoMav2 15 m@95% vs 0% vintage-mismatched; LoRetta/Sat-RoMa corroborate        | supported |
| Spacing governs operability          | 97%/21.1 m dense vs 25%/275 m coarse, identical chain                         | supported |
| R03 floor dataset-side               | ORB 11.4 / SIFT 11.7 vs 13.9; Xian05 8.6 below                                | supported |

## Self-Review (five dimensions)

**Contribution.** Mechanism-first failure analysis with rates: taxonomy, backwards tables, matcher independence, diagnostic, falsified countermeasure + oracle bound, spacing isolation, boundary map, protocol. Narrowed vs v6 (supplement split); concurrent systems cited as regime assumers, not competitors.
**Clarity.** One message per section; model in Sec. 3 before evidence; terms fixed (whole/sub-tile, backwards rate, fatal/good/mid, lattice); rhetoric softened to observed/measured/suggests throughout.
**Experiments.** Fixed seeds, denominators inline, oracle + null controls, pre-registered kills; exploratory items (21-traj gate) labelled as such.
**Evaluation.** AerialVL executed, TEMPO-VINE rejected, ViLD pending; 4 matchers + dense; learned rates honestly underpowered; 7 XIAN trajectories unrun, stated.
**Soundness.** Mixture analysis predicts its failure; small-cell rule honoured (LightGlue rates declined); dense verdict has two discriminators + analytic bound; averaging bound labelled unreachable-without-odometry.

## References

Same 29 as v6 (no new citations required). Bib: `latex/refs.bib` unchanged.
