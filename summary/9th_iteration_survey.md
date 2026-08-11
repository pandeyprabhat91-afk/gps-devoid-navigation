# GPS-Denied UAV Navigation — 9th Iteration: External Literature Survey

**Project:** MTech Final Year Project, IIT Madras
**Date:** 2026-08-09
**Status:** Survey pass plus one experiment the survey directly caused. The 8th
iteration closed every internal direction it could reach; this iteration goes
outside the project for input. The survey's structural finding is §1. **The
experiment it produced (§9) retracts 7th-iteration Finding N for R06 and is the
largest single coverage gain measured in this project.**

> **Scope.** Eighteen searches across arXiv, ISPRS Journal, IEEE Xplore, MDPI
> Remote Sensing / Drones / Sensors, Science Robotics, ScienceDirect and GitHub.
> Five papers read in full (OrthoLoC, OrthoTrack, UAV-AVL/AnyVisLoc, SPRIN-D
> heightmap system, NGPS). Numbers below are attributed; where a figure comes
> from a search summary rather than a full read, it is marked *(snippet)* and
> should be verified before it is quoted in the thesis.

---

## 0. Headline

| | |
|---|---|
| **What every competitive system does that this project does not** | **lift 2D matches to 3D with an elevation model, then solve PnP** |
| This project's geometry | flat-ground homography, no elevation, image-centre projection |
| AnyVisLoc satellite row — the 18.5 % A@5m this project benchmarks against | measured **with a 30 m DSM and PnP+RANSAC**, not with a homography |
| Best matchers on that benchmark | **RoMa 70.1 %** > DKM 65.6 % > LoFTR 59.5 % > **SP+LG+GIM 57.0 %** |
| Which of those this project has tested | **only the last** (plus LoFTR crippled at 640×480) |
| OrthoTrack (RoMa-v2 + DSM + PnP + flow) | **ATE 0.67 m**, 30× better than single-frame OrthoLoC |
| NGPS (IROS 2026) — closest architecture to this project | **2.94 m RMSE** vs 10.37 m VIO-only |
| Alternative reference modalities found | vector maps, heightmap gradients, semantic maps, season-invariant transforms |

---

## 1. The Structural Finding — Everyone Else Solves PnP Against 2.5D Geodata

This project recovers position by fitting a **homography** between the drone
image and a satellite patch, inverting it, and projecting the image centre
through it (`map_matcher.py:435-445`). There is no elevation model anywhere in
the chain. The 4th iteration recorded that the CSV `height` column is absolute
rather than AGL and moved on; no iteration has ever used terrain or surface
elevation.

Every competitive system found in this survey does the same three things
instead:

1. Match the UAV frame against a georeferenced orthophoto (DOP) or satellite
   tile.
2. **Lift each 2D match to a 3D point using a DSM/DEM.**
3. Solve **PnP + RANSAC** for full 6-DoF pose.

| System | Reference data | Matcher | Geometry | Result |
|---|---|---|---|---|
| **AnyVisLoc / UAV-AVL** (CVPR 2026 Findings) | satellite 0.197 m + **30 m DSM** | CAMP retrieval → RoMa | **PnP+RANSAC** | **18.5 % A@5m**, 38.7 % A@10m, 58.5 % A@20m |
| same, aerial reference | aerial 0.070 m + DSM | CAMP → RoMa | PnP+RANSAC | 74.1 % A@5m |
| **OrthoLoC** (arXiv 2509.18350) | DOP + DSM | **GIM+DKM** | **PnP** | **0.32 m** translation, 75.4 % R@1m-1° |
| **OrthoTrack** (arXiv 2606.25245) | DOP + DSM | **RoMa-v2** | **PnP-RANSAC** + LK flow between keyframes | **ATE 0.67 m**, median TE 0.33 m |
| **Terrain-weighted optimization** (ISPRS/IJAEOG, [code on GitHub](https://github.com/YFS90/GNSS-Denied-UAV-Geolocalization)) | public satellite + **DEM** | — | orthorectify UAV image via camera model + DEM, then scene-match | **MAE < 7 m** *(snippet)* |
| **This project** | satellite 0.3 m, **no elevation** | ORB+AKAZE+SIFT | **flat homography** | R03 oracle 11.9 m / R04 40.8 m |

The field states the trade-off explicitly:

> *"PnP-based raytracing is more suitable for complex terrain because it
> explicitly uses camera pose and DSM geometry, while homography-based
> approaches are better for simpler scenarios."* — SkyPin / UAV-AVL discussion *(snippet)*

> *"Visual localization algorithms based on homography transformation make it
> difficult to locate UAVs in non-planar scenes."* *(snippet)*

The AnyVisLoc paper "bypasses affine/homography assumptions entirely, treating
low-altitude multi-view as fundamentally non-planar and requiring full 3D
PnP+RANSAC."

### 1.1 Why this lands exactly on 8th-iteration Finding Q

The 8th iteration measured that the residual error against the **correct tile**
is:

- **common-mode** — ORB pool and GIM agree to a median 0.17 m at a 7.4× inlier
  ratio, while both sit ~23.5 m from truth;
- **not a constant** — the spread of per-frame offsets exceeds the median
  offset, and a split-half-fitted correction failed to generalise.

A frame-specific offset that any matcher reproduces identically is precisely
what a **wrong geometric model** produces. Relief displacement is the textbook
case: a point at height `h` above the fitted plane, seen at off-nadir ray angle
`θ`, lands `h·tan(θ)` away on the ground plane. With this project's
`CAMERA_K` (fx = 950, cx = 684, cy = 456 at `QUERY_SCALE=0.25`), the image
half-diagonal is 822 px, so `tan(θ_max) = 822/950 = 0.87` — **θ_max ≈ 41°**.

| feature height above local plane | displacement at frame corner |
|---|---|
| 5 m (crop rows, embankments) | 4.3 m |
| 10 m (hedgerows, low buildings) | 8.7 m |
| 15 m (mature tree line) | 13.0 m |
| 20 m (buildings) | 17.3 m |

Correspondences at different radii and different heights each get a different
displacement, and a single homography fitted over all of them lands on a
best-fit plane that is offset by a frame-specific amount — **identically for
every matcher**, because the correspondences themselves are correct. This
reproduces Finding Q's signature exactly, and note the displacement is
**independent of flight altitude** (it depends on ray angle and object height,
not on `H`), which matches the 8th iteration's observation that R03's A@5m is
7.5 % at every drift level and the 7th iteration's finding that altitude/GSD
scaling was already optimal at factor 1.00.

**Honest caveat, and it matters.** This arithmetic accounts for R03's 11.9 m
oracle median comfortably. It does **not** obviously account for R04's 40.8 m —
that would need ~46 m of relief at the frame corner, which flat Jiangsu farmland
does not have. So R04 likely has a second mechanism, and the most plausible one
given 7th-iteration Finding K (continuous error distribution, no gap) is
**sub-tile furrow aliasing**: both matchers lock onto the same wrong period of a
repetitive furrow pattern *within* the correct tile. That is consistent with
common-mode agreement and with a continuous error distribution, and it is a
different problem from relief. §6 gives a test that separates them.

### 1.2 Practical: elevation data is free and covers the dataset

UAV-VisLoc is 11 locations in China. Free global coverage exists:

| DEM | resolution | vertical RMSE | note |
|---|---|---|---|
| **Copernicus GLO-30** | 30 m | ~2–6 m; 6.73 m on China terrains vs ICESat-2 | best over flat/bare terrain, most detail *(snippet)* |
| **ALOS AW3D30** | 30 m | 6.63 m on the same China evaluation | JAXA, free *(snippet)* |
| NASADEM / SRTM | 30 m | 6.59 m | older |

AnyVisLoc warns a 30 m DSM is "inadequate for low-altitude precision" and calls
for **<1 m DSM**. That warning is aimed at low-altitude oblique flight over
buildings. This project flies at **450–550 m** over farmland, where 30 m
posting is a far better match to the scene's spatial scale — but 30 m posting
also cannot represent a 15 m tree line, which is exactly the feature that
generates the displacement above. **Expect partial correction, not a fix.** That
is precisely why this needs a cheap gate rather than a build.

---

## 2. The Matcher Landscape — This Project Tested The Weakest Options

AnyVisLoc's ranked matcher table, with CAMP retrieval, on the satellite task:

| matcher | A@5m | tested in this project? |
|---|---|---|
| **RoMa** | **70.1 %** | **no** |
| **DKM** | 65.6 % | **no** |
| LoFTR | 59.5 % | yes — but at 640×480, which the 7th iteration itself flagged as crippling |
| SP+LG+GIM+k2s | 57.0 % | yes — this is the one the project built its GIM conclusions on |
| SIFT / ORB | far below | yes (production) |

So the 7th iteration's "GIM is a much better matcher that selects no better" and
the 8th's "GIM adds 7× inliers and moves the fix 0.17 m" were both measured on
**the weakest learned matcher in the published ranking**, and under a homography
that Finding P showed is saturated anyway.

**This does not invalidate Findings I or P.** Both are statements about
saturation under a flat homography, and they will hold for RoMa too. What it
changes is the *combination* worth testing: dense matchers matter for PnP
because PnP needs correspondences **well distributed over varied terrain
height**, not merely numerous. A dense matcher plus a DSM is a different
experiment from a sparse matcher plus a homography, and only the former has ever
produced the published numbers.

Relevant recent matchers:

- **RoMa v2** (arXiv 2511.15706, Nov 2025) — frozen DINOv3 ViT-L coarse stage,
  custom CUDA kernels, **1.7× faster than RoMa** at similar memory. Trained on a
  distribution that includes **AerialMegaDepth**. This is what OrthoTrack uses.
- **DKM** (CVPR 2023) — OrthoLoC's best when paired with GIM weights. Dense,
  slower, more parameters.
- **MINIMA** (CVPR 2025) — modality-invariant matching; MINIMA-RoMa tops CM-Bench
  cross-modal evaluations *(snippet)*. Relevant if RGB↔satellite is treated as a
  modality gap.
- **LiteSAM** ([Remote Sensing 17(19):3349](https://www.mdpi.com/2072-4292/17/19/3349), [code](https://github.com/boyagesmile/LiteSAM)) — explicitly
  a *lightweight satellite–aerial* matcher for UAV AVL on **edge devices**.
  This is the one to look at for the RDK X5 target.
- **AerialMegaDepth** (CVPR 2025) — the training data that fixed aerial↔ground
  transfer for DUSt3R/MASt3R. Explains why stock ground-trained matchers failed
  in the 5th iteration and why retrained ones do better.
- **MASt3R** — explicitly reported as struggling on aerial-to-satellite domain
  gaps ("high median errors and low recall"). Deprioritise.

---

## 3. Architecture — The E2E Cascade Failure Has A Published Answer

The 5th iteration's end-to-end test found R03/R06/R08 diverge irrecoverably when
frame 0 fails to match, and R04 succeeded with 57.5 % drift reduction. Two
systems solve exactly this.

### 3.1 NGPS (IROS 2026) — closest published analogue to this project

Downward gimbal camera + satellite base map at 0.3 m/px, SuperPoint+LightGlue,
RANSAC **homography**, fused with VIO.

- **Asynchronous time-priority queue** feeding a UKF: visual geo 1–2 Hz,
  VIO 10–20 Hz, IMU 100–200 Hz.
- **Velocity-predicted search window** — crop the reference using the UKF
  velocity estimate rather than searching a fixed radius. At 4 m/s this raised
  matching success **64.3 % → 84.7 %**.
- **Adaptive measurement covariance** from RANSAC inlier ratio + reprojection
  error + match confidence: **11 % further RMSE reduction** over fixed noise.

| | RMSE | max error |
|---|---|---|
| monocular VIO only | 10.37 m | 31.40 m |
| visual geo only | 4.46 m | 9.84 m |
| **adaptive NGPS** | **2.94 m** | **6.87 m** |

Altitude dependence: 1.82–2.06 m at 80–100 m, 2.73 m at 60 m, **6.04 m at 150 m**
with match success dropping to 78.3 %. Jetson Orin NX; LightGlue is 318 ms of a
386 ms pipeline; GPU mandatory (CPU-only ≈ 0.5 Hz). Ground truth was RTK at
~2 cm.

**Two things to take from this.** The adaptive-covariance trick maps directly
onto this project's per-candidate signals and is cheap. And NGPS gets 2.94 m
*with a homography and no DSM* — but at 80–100 m altitude, where relief
displacement at the frame corner is the same as at 500 m for a given object
height, yet the *scene* seen from 100 m contains far less height variation
within the footprint. Its degradation to 6.04 m at 150 m is consistent with
footprint growth bringing in more relief.

### 3.2 OrthoTrack — the anti-cascade-failure design

- **Optical flow (Lucas–Kanade) propagates anchored 2D–3D correspondences
  between keyframes**; keyframes trigger full dense re-matching. Keyframes are
  only ~1 % of frames.
- **Adaptive keyframe triggering** when (a) tracked point count drops below
  threshold, (b) spatial spread of points collapses, or (c) reprojection error
  breaches an adaptive bound that relaxes right after a keyframe and decays over
  ~100 frames.
- Because all 3D points come from the georeferenced DSM, "the resulting pose is
  metric and globally anchored by construction" — there is no odometry drift to
  accumulate between anchors.
- ATE **0.67 m** (MovingDrone), **1.51 m** on real UAVScenes vs 104 m for
  DROID-SLAM with oracle alignment.
- **Robust across 14 orthophoto vintages (2011–2025)**, median TE 0.33–2.28 m —
  directly addresses the temporal-staleness worry.
- Failures "concentrate in sequences with extreme tilt or low-texture areas" and
  on "repetitive lane markings" — the same failure modes this project sees.
- Cost: 23.8 FPS on an L40S, ~11 GB peak GPU during keyframes. **Not edge-ready
  as published**; RoMa-v2 Base/Fast cuts keyframe cost to 0.4–0.5 s.

The triggering rule is the direct fix for the 5th-iteration cascade failure:
re-anchor on *evidence that tracking is degrading*, rather than on a fixed
schedule, and never let the prior wander outside the search window.

---

## 4. Alternative Reference Modalities — For The Regions Matching Cannot Open

The 7th iteration closed R01/R06/R08 with strong evidence: four matcher families
converge on a 3–7 inlier noise floor against the correct tile, so the satellite
reference does not share recoverable *appearance* with the drone imagery. That
argument is specific to appearance. Three other modalities exist.

**Heightmap gradients** — [SPRIN-D Challenge winner](https://arxiv.org/html/2510.01348), kilometre-scale
GNSS-denied navigation. Builds a local heightmap from LiDAR, thresholds
gradients above 5 m into a binary edge map, template-matches against binary edge
maps from public DEM (Bavarian geodata, 1 m bins), fuses with OpenVINS odometry
in a **particle filter with K-means clustering to handle perceptual aliasing**
(largest cluster's centroid wins).

- **RMSE < 11 m over 9 km missions** vs up to 53 m for compass-aligned odometry.
- Forest flight 239: **8 m RMSE over 1371 m**. Urban flight 206: 6 m.
- Runs **CPU-only on an Intel NUC i7** — no GPU.
- Fails in open fields with no vertical structure (falls back to odometry).
- Note the practical detail: they mechanically decoupled IMU and camera with
  printed silent blocks, stating VIO reliability "critically depends on
  isolating the IMU from high-frequency vibrations."

This works in **forest** — R06's terrain — where appearance matching is dead.
The catch is it needs LiDAR to build the local heightmap; a monocular version
would need dense depth, which is a research problem in itself.

**Vector maps** — [VecMapLocNet, ISPRS J. P&RS 2025](https://www.sciencedirect.com/science/article/abs/pii/S0924271625001455). Matches UAV
imagery against **OpenStreetMap vector data** for 3-DoF pose (lat, lon, yaw).

- **84.45 % Recall@5 m**, 88.61 % Recall@5°, **25.23 ms on Jetson Orin**.
- Real-world generalisation: **16.7 m localization error, 3.1° orientation**.
- Vector maps are tiny to store and **visually consistent across seasons** —
  they cannot go stale the way a satellite raster does.

This is the direct answer to "the satellite reference for R01/R06/R08 does not
share content with the drone imagery": *change the reference*. OSM coverage in
rural China is the open question and is checkable for free in an afternoon.

**Season-invariant transforms** — [Science Robotics 6(55), Fragoso et al.](https://www.science.org/doi/10.1126/scirobotics.abf3320),
[code](https://github.com/connorlee77/seasonally-invariant-image-transform). A learned
preprocessing transform that makes imagery seasonally invariant, applied
*upstream* of an unmodified registration algorithm. Also
[LSVL](https://www.sciencedirect.com/science/article/pii/S0921889023001367): global
localization over 100 km² at **12.6–18.7 m lateral error** from an uninformed
start in 23–44 updates, under winter↔summer change *(snippet)*.

The upstream-preprocessing design is attractive here precisely because it does
not require touching the matcher — it is testable against this project's
existing pipeline as a drop-in image transform.

**Semantic / structural** — [Hierarchical Image Matching for UAV AVL (arXiv 2506.09748)](https://arxiv.org/abs/2506.09748)
trains on **UAV-VisLoc** and evaluates on AerialVL and a new CS-UAV set covering
"urban, rural, and mountainous forest". Closest published work to this project's
exact dataset; worth reading in full for its UAV-VisLoc numbers.
[SASGeo](https://arxiv.org/html/2607.07737) does stability-aware semantic map
localization — selecting map elements unlikely to change.

---

## 5. VIO Side

The 5th-iteration E2E test found the VIO reduced to pure IMU dead-reckoning
after frame 1 because `OrbKltTracker` cannot bridge 7-second frame gaps
(tracked features: 197–288 → 0–14 → 0–7). Literature confirms this is a real,
named limitation, not an implementation defect: methods "frequently fail to
initialize or lose tracking under large inter-frame gaps"; "when the camera
moves too fast, visual-only odometry often results in too little overlap."

**High-altitude monocular VIO is specifically known to be weak.** Above ~100 m,
"large scene depth causes visual motion constraints to be significantly less
informative than in near-sighted scenarios", and both VINS-Fusion and OKVIS
"suffer from increased scale errors with increasing altitude and scene depth"
*(snippet)*. At 450–550 m this project is deep into that regime. Documented
mitigations:

- **1D laser rangefinder aided VIO** (LRF-VIO, MSCKF-based) — a single ranging
  beam disambiguates scale during feature tracking at high altitude.
- **Barometer for scale** — with the caveat that aerodynamic disturbance at the
  static port produces **>15 m altitude error at high airspeed** *(snippet)*,
  so it is not a free fix.
- **Mechanical IMU isolation** — the SPRIN-D team's silent blocks, stated as
  critical to practical VIO reliability.

**The architectural point is more important than the VIO choice.** OrthoTrack
does not run VIO at all between anchors — it propagates *anchored 2D–3D
correspondences* with Lucas–Kanade. NGPS runs VIO at 10–20 Hz but its accuracy
comes from 1–2 Hz absolute fixes. Both make the map the primary position source
and the odometry a short-horizon interpolator, which is the 4th iteration's
"loop closure" mandate inverted: **at 7-second frame spacing the odometry cannot
be primary, so it should not be asked to be.**

Current VIO/VO options if the odometry does get revisited: OpenVINS (used by the
SPRIN-D winner, CPU-capable), VINS-Fusion, DPVO / Deep Patch VSLAM (DROID-SLAM
accuracy at ~2× speed and ⅓ the VRAM), DINO-VO (foundation-model features),
VGGT and its 2026 derivatives. Note OrthoTrack measured **DROID-SLAM at 104 m
ATE** on real UAV data even with oracle Sim(3) alignment — learned VO is not a
shortcut here.

**Edge target.** RDK X5 / RK3588-class NPUs are ~6 TOPS. NGPS needs a Jetson
Orin NX for 2.6 Hz. OrthoTrack needs ≥12 GB VRAM. The realistic edge paths are
**LiteSAM** (designed for it), **VecMapLocNet** (25 ms on Orin), or the SPRIN-D
**CPU-only heightmap** approach — not RoMa v2.

---

## 6. Ranked Directions, With Gates

Stated in the project's own gate-before-sweep format. Kill criteria are
proposed, not yet run.

### D1 — PnP against a free 30 m DSM, replacing the homography **[highest value]**

*Rationale:* §1. The single structural difference between this project and every
competitive system, and it lands exactly on the mechanism 8th-iteration
Finding Q identified.

*Cheapest possible gate, before any pipeline work:* download Copernicus GLO-30
for the R03 and R04 footprints and simply **measure the terrain/surface relief
inside each frame's ground footprint**. If the relief within a footprint is
under ~3 m, relief displacement cannot explain an 11.9 m residual and D1 is dead
for that region before a line of matching code is written. Cost: no matching at
all.

*If relief survives that check:* on the 14 R03 / 16 R04 GT-tile frames already
collected, lift the existing ORB-pool correspondences to 3D via the DSM and
solve PnP instead of the homography. **Kill unless the paired median error
improves ≥ 5 m.**

*Honest expectation:* partial. A 30 m DSM cannot represent the 10–15 m tree
lines and embankments that generate most of the displacement, and it will do
nothing for the R04 furrow-aliasing hypothesis.

### D2 — Separate R04's two candidate mechanisms **[cheapest, do first]**

*Rationale:* §1.1 leaves R04 with two live explanations — relief displacement
and sub-tile furrow aliasing — that call for completely different work.

*Gate:* for the R04 GT-tile frames, plot the **direction** of the position
error. Furrow aliasing predicts errors quantised along the furrow-normal
direction at multiples of the furrow period; relief predicts errors oriented by
the local height distribution with no periodicity. This is a histogram over data
already on disk (`results/georef_bias.json` holds signed north/east offsets per
frame). **Zero compute.** Do this before D1.

### D3 — RoMa v2 or DKM *with* PnP, not instead of the homography

*Rationale:* §2. The two top-ranked matchers on the benchmark this project cites
have never been tested, and dense correspondence matters for PnP in a way it
provably does not for a saturated homography (Finding P).

*Gate:* only meaningful **after** D1 shows PnP helps. Testing RoMa under the
existing homography would reproduce Finding P and waste the run.

### D4 — Adaptive covariance + velocity-predicted search window in the E2E loop

*Rationale:* §3.1/§3.2. NGPS gets 64.3 % → 84.7 % match success from the search
window and 11 % RMSE from adaptive covariance; OrthoTrack's adaptive keyframe
triggering is the direct fix for the 5th-iteration cascade failure. All three
are cheap, use signals this pipeline already computes, and are independent of
the geometry question.

*Gate:* re-run `e2e_loop_closure_test.py` on R03 with adaptive triggering.
**Kill unless R03 stops cascade-failing** (currently 0/20 matched).

### D5 — Vector maps (OSM) as reference for R01 / R06 / R08

*Rationale:* §4. The 7th iteration closed these regions against *appearance*
references. A vector map is not an appearance reference and cannot go stale.

*Gate:* check OSM coverage density over the R01/R06/R08 footprints. **Kill if
coverage is sparse** — VecMapLocNet's results depend on the detailed annotation
found in developed areas, and rural China is the open question. Free, one
afternoon.

### D6 — Season-invariant preprocessing transform

*Rationale:* §4. Drop-in upstream of the existing matcher, public code, and the
7th iteration's "seasonally divergent satellite reference" diagnosis for
R01/R06/R08 is exactly what it targets.

*Gate:* apply the transform to R06 GT-tile pairs and re-measure inliers.
**Kill unless the 5.0-inlier noise floor moves above `min_inliers=10`.**

### Deprioritised

- **MASt3R / DUSt3R** — explicitly reported to struggle on aerial↔satellite.
- **Heightmap gradients (SPRIN-D)** — excellent results in forest, but needs
  LiDAR the project does not have.
- **Learned VO (DROID-SLAM etc.)** — 104 m ATE on real UAV data with oracle
  alignment. Not a shortcut.
- **Cross-view retrieval training (Sample4Geo etc.)** — the 7th iteration's
  oracle test already showed generation is not the bottleneck.

---

## 7. What This Survey Does And Does Not Change

**Does not change.** Finding P (homography saturates), Finding Q (residual is
common-mode and non-constant), Finding R (oracle ceilings), the 7th iteration's
noise-floor closure of R01/R06/R08 under appearance matching. All were measured,
and nothing here contradicts them.

**Changes the interpretation of Finding R.** The 8th iteration reported R03's
oracle ceiling at 14.3 % A@5m and R04's at 0 % and called them hard limits. They
are hard limits **for a flat-ground homography with no elevation model**. The
literature shows the geometry is the binding constraint in a way this project
has never tested, so "ceiling" should be read as "ceiling of the current
geometric model", not "ceiling of the data". That is a materially weaker and
more honest claim, and D1/D2 are what settle it.

**Changes the benchmark framing again.** The 18.5 % A@5m the 7th and 8th
iterations benchmark against was measured with **PnP on a 30 m DSM**. Comparing
a homography pipeline to it is not like-for-like — the same direction of error
as 7th-iteration Finding M and 8th-iteration Finding O, one level deeper. Until
D1 runs, the honest statement is: *this project has not yet implemented the
geometry that the published number was produced with.*

---

## 8. Sources

**Read in full:**
[OrthoLoC](https://arxiv.org/html/2509.18350v2) ·
[OrthoTrack](https://arxiv.org/html/2606.25245) ·
[UAV-AVL / AnyVisLoc benchmark](https://arxiv.org/html/2503.10692v2) ·
[SPRIN-D heightmap-gradient system](https://arxiv.org/html/2510.01348) ·
[NGPS (IROS 2026) summary](https://www.aomway.com/post/2300.html)

**Matching:**
[RoMa v2](https://arxiv.org/abs/2511.15706) ·
[DKM](https://arxiv.org/abs/2202.00667) ·
[LiteSAM (RS 17(19):3349)](https://www.mdpi.com/2072-4292/17/19/3349) + [code](https://github.com/boyagesmile/LiteSAM) ·
[AerialMegaDepth (CVPR 2025)](https://arxiv.org/abs/2504.13157) ·
[GIM](https://github.com/xuelunshen/gim)

**Alternative modalities:**
[VecMapLocNet (ISPRS J. P&RS 2025)](https://www.sciencedirect.com/science/article/abs/pii/S0924271625001455) ·
[Seasonally invariant deep transform (Science Robotics)](https://www.science.org/doi/10.1126/scirobotics.abf3320) + [code](https://github.com/connorlee77/seasonally-invariant-image-transform) ·
[LSVL](https://www.sciencedirect.com/science/article/pii/S0921889023001367) ·
[Season-invariant GNSS-denied VL](https://arxiv.org/abs/2110.01967) ·
[SASGeo](https://arxiv.org/html/2607.07737) ·
[Hierarchical Image Matching for UAV AVL](https://arxiv.org/abs/2506.09748)

**Terrain / geometry:**
[Terrain-weighted constraint optimization](https://www.sciencedirect.com/science/article/pii/S1569843224006332) + [code](https://github.com/YFS90/GNSS-Denied-UAV-Geolocalization) ·
[Georeferenced UAV Localization in Mountainous Terrain (Drones 9(10):709)](https://doi.org/10.3390/drones9100709) ·
[SkyPin 2.5D benchmark (Drones 10(7):500)](https://doi.org/10.3390/drones10070500) ·
[Copernicus/NASA/AW3D30 evaluation over China](https://www.tandfonline.com/doi/full/10.1080/17538947.2022.2094002)

**Datasets:**
[UAV-VisLoc](https://arxiv.org/abs/2405.11936) + [repo](https://github.com/IntelliSensing/UAV-VisLoc) ·
[UAVD4L](https://arxiv.org/pdf/2401.05971)

**VIO / VO:**
[Deep Patch Visual SLAM (ECCV 2024)](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/00272.pdf) ·
[DINO-VO](https://arxiv.org/pdf/2507.13145) ·
[DROID-SLAM](https://arxiv.org/pdf/2108.10869) ·
[1D-LRF aided VIO for high-altitude MAV](https://ieeexplore.ieee.org/document/9811757/) ·
[VIO deployment on real UAVs](https://arxiv.org/pdf/2302.01867)

**Other open-source:**
[hmgoforth/gps-denied-uav-localization](https://github.com/hmgoforth/gps-denied-uav-localization) ·
[OSUPCVLab/PCVLabDrone2021](https://github.com/OSUPCVLab/PCVLabDrone2021) ·
[VisionUAV-Navigation](https://github.com/sidharthmohannair/VisionUAV-Navigation)

---

---

## 9. Result — R06's "Data Limit" Was A 2.5× Scale Error

The survey's DSM thread had an immediate, cheaper consequence than D1. Getting a
DEM to lift correspondences into 3D also gives **ground elevation**, and the
production GSD chain uses the dataset's `height` column, which the 4th iteration
established is **absolute, not AGL**:

```
drone_gsd = pred_alt_m / fx
gsd_ratio = drone_gsd / tile_ground_resolution(...)
```

Ground elevation from two independent public DEMs (ASTER30m and SRTM30m, queried
2026-08-09, agreeing to within 6 m everywhere):

| Region | `height` | ground elev | **true AGL** | **AGL/height** |
|---|---|---|---|---|
| R01 riverside | 405.8 | 10 | 395.8 | 0.98 |
| R03 farmland | 466.1 | 11 / 6 | 455.1 | 0.98 |
| R04 repetitive | 543.5 | 16 | 527.5 | 0.97 |
| **R06 mountain/forest** | **839.5** | **502 / 508** | **337.5** | **0.40** |
| R08 non-planar | 551.5 | 10 | 541.5 | 0.98 |
| R09 suburban | 546.5 | 59 / 62 | 487.5 | 0.89 |

Five of six regions sit on the Yangtze/Jiangsu delta at 6–16 m elevation, so
absolute height ≈ AGL and the chain is harmless. **R06 is in the Qinba mountains
at ~505 m**, so its assumed altitude is 2.5× too high and its query and reference
are matched at ~2.5× different ground scales. R06 is also the only region with
any altitude spread at all (min 498.6, max 841.6 — a 343 m range against
1–8 m for every other region), which is the terrain showing through.

### 9.1 Why six iterations missed it

The 7th iteration tested exactly this hypothesis and killed it. Its script
`diag_altitude_scale.py` states in its own docstring: *"Run on a region that
MATCHES well (R03), so errors are measurable rather than dominated by match
failures."* R03's true factor is 0.98, so **factor 1.00 genuinely is optimal
there** and the flat curve was a correct measurement. The default sweep range is
`0.6,0.8,0.9,1.0,1.1,1.2,1.4` — it does not reach 0.40. The conclusion "the GSD
chain is sound" was right for R03 and generalised to all six regions on one
region's evidence.

### 9.2 The decisive test

`scripts/smoke_agl_inlier_floor.py`. Ground-truth tile only (selection removed),
production ORB+AKAZE+SIFT pool (the matcher Finding N measured), n=8, the sole
variable being the altitude factor. **Kill criterion stated before running:**
correcting AGL must lift mean inliers above `min_inliers=10` with a peak near the
DEM-predicted factor.

| factor | R06 assumed alt | R06 mean raw | **R06 mean inliers** | ≥10 | | R03 assumed alt | **R03 mean inliers** |
|---|---|---|---|---|---|---|---|
| 0.30 | 252 m | 22.4 | 9.9 | 3/8 | | 140 m | 2.5 |
| **0.40** | 336 m | 33.1 | **10.6** | **4/8** | | 186 m | 3.5 |
| 0.50 | 420 m | 38.5 | 9.4 | 3/8 | | 233 m | 5.4 |
| 0.60 | 504 m | 45.1 | 9.4 | 2/8 | | 280 m | 6.9 |
| 0.80 | 672 m | 57.6 | 6.6 | 1/8 | | 373 m | 9.5 |
| **1.00** *(production)* | 839 m | 82.8 | **5.1** | **0/8** | | 466 m | **9.6** |

R06 peaks at **0.40 — exactly its DEM-predicted factor** — and collapses at 1.00.
R03 peaks at **1.00 — its DEM-predicted 0.98** — and collapses at 0.40. The two
curves are mirror images, each maximised at its own predicted value. **The effect
is an altitude correction, not an artifact of the rescale code.**

**Finding S — R06's inlier noise floor was a scale error, not a data limit.**
7th-iteration Finding N recorded R06's ORB pool at 5.0 mean inliers against the
correct tile; this reproduces that exactly at factor 1.00 (5.1) and doubles it at
the corrected factor. Four architecturally independent matchers converged on the
same floor because **all four were handed the same 2.5× mis-scaled pair.** The
convergence was evidence of a common input defect, not of a common data limit.

The 7th iteration's supporting observation now reads the other way round. It
noted: *"on R06, ORB finds 52–130 descriptor matches and only 4–6 survive the
homography... the matches are spurious and geometry rejects them."* The table
above shows raw matches *falling* (82.8 → 33.1) while inliers *rise* (5.1 → 10.6)
as the scale is corrected. At the wrong scale the descriptors still match —
forest texture is self-similar — but no single homography can explain them,
because the scale is wrong. Geometry was rejecting them for the right reason and
the wrong cause.

### 9.3 End-to-end effect

`diag_altitude_scale.py --region 06 --n 20 --drift 300`, production `MapMatcher`,
sweeping the factor:

| factor | assumed alt | **match%** | CEP50 | CEP90 | fatal50 | **yield%** |
|---|---|---|---|---|---|---|
| 0.30 | 252 m | 35.0 | 15.4 | 155.5 | 14.3 (2/7) | 30.0 |
| **0.35** | 294 m | **50.0** | 20.2 | 358.4 | 20.0 (2/10) | **40.0** |
| 0.40 | 336 m | 45.0 | 19.2 | 358.4 | 22.2 (2/9) | 35.0 |
| 0.50 | 420 m | **50.0** | 19.2 | 354.8 | 20.0 (2/10) | **40.0** |
| 0.60 | 504 m | 40.0 | 19.9 | 126.2 | 12.5 (1/8) | 35.0 |
| 0.80 | 672 m | 20.0 | 16.3 | 258.1 | 25.0 (1/4) | 15.0 |
| **1.00** *(production)* | 839 m | **10.0** | 14.0 | 15.1 | 0.0 (0/2) | 10.0 |

**Match rate 10 % → 50 %, yield 10 % → 40 %.** R06 has been at 0–10 % match for
the entire history of this project; this is the largest coverage change ever
measured on it, and the plateau (0.35–0.50) brackets the predicted 0.40.

**Two honest qualifications.**

*The script's own verdict line says "no meaningful interior optimum: GSD chain
sound".* That line ranks configurations on **CEP50 alone**, which the project has
forbidden since the 3rd iteration, and the 14.0 m it prefers is computed over
**2 accepted fixes**. This is 6th-iteration Finding G exactly — a per-region
metric resting on a denominator too small to carry a decision. The verdict logic
in `diag_altitude_scale.py` should be changed to rank on yield and report
denominators; until then its printed conclusion should not be quoted.

*The tail gets worse.* CEP90 rises to ~355 m and fatal50 to ~20 %. That is
expected and does not undo the result: R06 is the region 7th-iteration Finding K
showed is **genuinely bimodal** (true perceptual aliasing, clean 40–150 m gap).
Admitting five times as many matches on an aliasing-prone forest region admits
aliases too. The correction fixes *matching*; selection on R06 remains the known
hard problem. All fatal counts here are 1–2 frames — reported with denominators
inline, and none of them can carry a decision either.

*Cross-script inlier magnitudes are not comparable.* This script reports R03 at
9.6 mean inliers where `diag_gim_probe.py` reported 128.3 and the 7th
iteration's detector-free smoke test reported 54.8 — three different frame
samples of the same region and matcher, disagreeing by more than 10×. That
variance is pre-existing, not introduced here. Only the **paired, same-frames,
within-script** comparison across factors is valid, which is what the conclusion
rests on.

### 9.4 What this changes

- **Finding N is retracted for R06.** It stands for R01 and R08, whose AGL ratios
  are 0.98 — their floors are not explained by scale.
- **R09 is off by 11 %** (AGL 487.5 vs assumed 546.5). Small, but R09 has never
  been properly measured (8th iteration §5) and this should be part of measuring
  it.
- **The 8th iteration's oracle ceilings are unaffected** — they were computed on
  R03 and R04, whose AGL ratios are 0.98 and 0.97.
- **The barometer becomes load-bearing.** On the real vehicle,
  `AGL = baro_altitude − DEM(estimated position)`. The DEM fetched for D1 pays
  for itself twice, and this needs no sensor the platform does not already have.
- **Priority change.** Applying the AGL correction across all regions is now
  cheaper and better-evidenced than D1, and should run first. D2 (zero compute)
  still runs before both.

---

## 10. Ideas From Open-Source SLAM/VIO Codebases

§1–8 surveyed the computer-vision literature. This section surveys **shipped,
maintained SLAM and VIO software** instead. It is a materially different well,
and it turns out to be the better-matched one, for two reasons.

**First, this project has been solving a SLAM problem as a computer-vision
problem.** Every one of the six rejection signals tested across iterations 3–6
was a per-frame, per-candidate scoring function. Mature SLAM stacks abandoned
that framing years ago: they treat wrong loop closures as an *estimation*
problem to be handled by the back-end, not a *perception* problem to be filtered
at the front-end.

**Second, everything here runs on a CPU.** GTSAM, DBoW3, PCM/GNC and ECC are all
C++/CPU and fit an 8× Cortex-A55 comfortably. That is the opposite of §2's
conclusion, where the winning matchers (RoMa v2, DKM) are undeployable on the
RDK X5. For a fixed sensor stack of barometer + IMU + global-shutter camera on a
10-TOPS edge SoC, **this section is the more realistic source of gains.**

### 10.1 The fatal-error metric exists because the estimator is a filter

`fatal50` has organised six iterations of work. It matters because in an ESKF a
wrong map fix is **permanent** — it corrupts the state and there is no mechanism
to undo it later. That is a property of the estimator, not of the problem.

Modern SLAM back-ends do not accept that. GTSAM ships:

- **Robust noise models** — `noiseModel::mEstimator::Huber`, `Cauchy`, `Tukey`,
  `GemanMcClure`, wrapped around any factor.
- **`GncOptimizer`** — Graduated Non-Convexity. Starts convex, gradually
  sharpens the loss, letting the optimiser escape the influence of outliers.
- **`IncrementalFixedLagSmoother`** — a sliding window over recent states with
  older ones marginalised. For nonlinear problems like VIO, fixed-lag smoothing
  is generally more accurate than filtering, and is more robust to outliers
  precisely because outlier rejection can happen *after* optimisation.

Consequence for this project: with a smoother plus a robust kernel on the map-fix
factors, a wrong fix is **down-weighted retroactively** once later fixes
contradict it. The trajectory heals. A 20 % fatal rate on R06 is catastrophic in
an ESKF and merely expensive in a robust smoother.

**This reframes the project's central metric.** Six iterations tried to drive
fatal50 down by rejecting bad matches before they enter. The back-end alternative
is to let them in and make them survivable. Neither has been tried here, and the
second is standard practice.

### 10.2 PCM — the mature version of the 7th iteration's trajectory gate

**Kimera-RPGO** implements *Pairwise Consistency Maximization*. The principle:
for any two inlier loop closures, composing the transforms around the cycle they
form with the odometry must return the identity. Build a graph whose nodes are
candidate loop closures and whose edges join mutually consistent pairs, then take
the **maximum clique** as the inlier set. Kimera-RPGO stores odometry edges and
loop closures separately, selects the consistent set, then optimises. It now also
offers **GNC**, reported to outperform PCM.

The 7th iteration's Finding J tested "trajectory clustering" — offset clustering
over collected candidates — and got fatal 31.2 % → 26.7 % against an oracle of
25 %. That was a hand-rolled, single-shot approximation of this idea. PCM is the
maintained version, it uses the odometry cycle rather than raw offsets, and it is
exactly aimed at NaviLoc's stated problem, which is this project's problem:
*high-similarity matches that are geographically inconsistent.*

### 10.3 Sequential consistency — the cheapest alias filter, never tested

Original **ORB-SLAM** required a loop candidate to be consistent across **three
consecutive keyframes** before accepting it. **ORB-SLAM3** replaced that with
geometric verification against *covisible* keyframes already in the map, and
reports this **raises** recall rather than costing it.

This project accepts or rejects every frame independently. It has never required
that a tile choice be corroborated by neighbouring frames. Given that R06 is
bimodal with a clean 40–150 m gap (7th-iteration Finding K), an alias that jumps
150 m will not be corroborated by the next frame's candidate set, while a correct
tile will. This is a few lines of bookkeeping over the existing candidate list.

Note it is *not* the same as the 3rd iteration's rejected temporal-deviation gate
(S9), which compared a match against a VIO prediction. This compares matches
against *each other*, which does not require the VIO to be trustworthy — and at
7-second frame spacing it is not.

### 10.4 Train a DBoW vocabulary on your own tiles

Retrieval failed twice here: DINOv2 global (5.4 % match, 4th iteration) and
CosPlace (4.2 %, 5th iteration). The diagnosis in both cases was correct and the
same: **both are trained on ground-level imagery** and do not transfer to
aerial↔satellite.

**DBoW2/DBoW3 has no such problem, because the vocabulary is trained offline on
whatever images you give it.** ORB-SLAM's vocabulary is k=10, depth 6 → ~1M
words, built from ORB descriptors over a large image set. Train it on this
project's own satellite tile pyramid (and drone frames), and the domain gap is
gone by construction — there is no pretrained prior to transfer badly.

This is the cheapest untried retrieval option in the project's history, it
sidesteps the exact documented failure mode, it is CPU-only, and DBoW3 handles
both binary and float descriptors so the existing ORB+AKAZE+SIFT pool can feed
it. Tooling exists ([DBoW3](https://github.com/rmsalinas/DBow3),
[vocabulary builder](https://github.com/manthan99/ORB_SLAM_vocab-build)).

*Caveat:* the 7th iteration's oracle test showed candidate **generation** is not
the bottleneck at drift = 300 m, so better retrieval will not by itself move
accuracy. Where it matters is the 5th iteration's **cascade failure** — a global
retrieval that works is what lets the system bootstrap when frame 0 fails and
re-localize after divergence. See §10.6.

### 10.5 Direct alignment — the one algorithm class Finding P cannot touch

8th-iteration Finding P says position is saturated with respect to correspondence
count above ~15 inliers. That statement is about **correspondence-based**
estimation. Every method this project has tried — ORB, AKAZE, SIFT, LightGlue,
GIM, LoFTR, and all six rejection signals — produces discrete correspondences and
fits a model to them.

**Direct alignment does not.** It optimises the warp parameters to minimise a
photometric or feature-map residual over the whole image. No keypoints, no
RANSAC, no inlier count — so saturation in the correspondence count is simply not
a constraint that applies.

Ladder, cheapest first:

1. **OpenCV `findTransformECC`** — Enhanced Correlation Coefficient, classical,
   CPU, illumination-invariant by construction. **No iteration document
   mentions ECC at all** (checked across iterations 1–8).

   *But be precise about what is and is not new here.* The project does have
   `scripts/test_ecc_refine.py` — an orphan of the same vintage as
   `test_bias.py`, hardcoded paths, result never published. Its docstring reads
   *"ORB for coarse alignment, then dense ECC for sub-pixel refinement"*, i.e.
   **ECC as post-hoc refinement of an already-chosen tile**. That is the same
   family as the phase-correlation refinement the 4th and 5th iterations killed
   hard (P1 phase-inside: 62 % fatal in isolation, 87.5 % on R03 in the 5th
   iteration's grid). Running it is nearly free and closes an open loose end,
   but it should be expected to reproduce that negative.

   **The untested variant is ECC as the candidate *scorer* or as the primary
   estimator** — replacing the homography-from-correspondences entirely, not
   polishing its output. That is the form Finding P does not constrain, and it
   is the one worth gating.
2. **[hmgoforth/gps-denied-uav-localization](https://github.com/hmgoforth/gps-denied-uav-localization)**
   — fine-tunes VGG16 conv3 features and runs sliding-window pose optimisation
   against satellite imagery. Public code, this exact problem.
3. **DeepLK / DLKFM** ([CVPR 2021](https://ieeexplore.ieee.org/document/9577303/)),
   building on [CLKN (CVPR 2017)](https://openaccess.thecvf.com/content_cvpr_2017/papers/Chang_CLKN_Cascaded_Lucas-Kanade_CVPR_2017_paper.pdf)
   and [PRISE (CVPR 2023)](https://openaccess.thecvf.com/content/CVPR2023/papers/Zhang_PRISE_Demystifying_Deep_Lucas-Kanade_With_Strongly_Star-Convex_Constraints_for_Multimodel_CVPR_2023_paper.pdf).
   These learn a feature map with two deliberate properties: brightness
   consistency between template and input, and a **smooth objective landscape
   around the ground-truth homography** so inverse-compositional LK converges.
   Explicitly built for **multimodal** pairs with large appearance change —
   which is what drone↔satellite is. Small CNNs, plausibly BPU-portable.

### 10.6 Atlas — the published fix for the cascade failure

The 5th iteration's end-to-end test found R03/R06/R08 diverge irrecoverably when
frame 0 fails: the prior drifts outside the search radius and no later frame can
recover. It called this "a real deployment finding".

**ORB-SLAM3's Atlas** is the standard answer. Tracking loss is handled in two
stages: short-term (pose from IMU, wide-window re-matching) and long-term
(**start a fresh active map**). The loop-and-merge thread searches the *whole
Atlas* at keyframe rate; a match in the active map is a loop closure, a match in
a different map triggers a **seamless merge**. The system never has to trust a
diverged prior, because it stops maintaining one.

Translated here: when N consecutive frames fail to match, **drop the prior
entirely and switch to global retrieval** (§10.4), then re-anchor and merge. This
is the same conclusion OrthoTrack reaches by a different route (§3.2, adaptive
keyframe triggering on evidence of degradation).

### 10.7 RTAB-Map's virtual place — a principled "I don't know"

**RTAB-Map** evaluates loop-closure probability with a **discrete Bayesian
filter** over all locations in working memory, and includes a **virtual place**
representing the *no-loop-closure* hypothesis, with its own likelihood
(parameter `VirtualPlaceLikelihoodRatio`). Acceptance is a posterior exceeding a
probability, not a feature count exceeding a threshold.

This project's only way to abstain is `min_inliers`, and 8th-iteration Finding P
showed that axis is saturated and uninformative. A posterior over {tile₁ … tileₙ,
nowhere} is a genuinely different decision rule, it composes with the sequential
consistency of §10.3, and it produces the calibrated confidence that §3.1's
adaptive-covariance trick needs as input.

RTAB-Map's **STM/WM/LTM memory management** — only working-memory nodes
participate in loop-closure detection, with the rest paged out to keep real-time
bounds on large maps — is also directly relevant to running a large tile pyramid
on 8 GB.

### 10.8 Smaller items worth stealing

| Source | Mechanism | Why it applies |
|---|---|---|
| **maplab / ROVIOLI** | loop closure is **2D–3D**: query features matched against the prior map's 3D structure, not 2D–2D | same shift as §1's PnP+DSM, arrived at from the SLAM side; ROVIOLI's "localization mode" *is* this project's architecture |
| **OpenVINS** | **FEJ** — without First-Estimate Jacobians, SLAM features *degrade* estimator performance | a consistency defect that silently costs accuracy; cheap to check |
| **OpenVINS** | online **camera–IMU time offset** as an estimated state | this project has `SoftwareSync`; at 7 s spacing a fixed offset error is large |
| **OpenVINS** | **chi-² gating** on every update, `dt_slam_delay` deferred initialisation | more principled than the widened Mahalanobis gate the 5th iteration used |
| **ORB-SLAM3** | geometric verification against **covisible** keyframes raised recall vs. the 3-consecutive rule | corroboration beats thresholds |
| **SPRIN-D team** | mechanically decouple IMU/camera with printed silent blocks | stated as critical to practical VIO reliability; free, and relevant to the real airframe |

### 10.9 Ranked, against the fixed sensor stack

All CPU-friendly. All compatible with barometer + IMU + global-shutter camera +
RDK X5.

| | direction | cost | why now |
|---|---|---|---|
| **S1** | ECC as candidate **scorer** / primary estimator, not refinement | low | direct alignment is the one algorithm class Finding P cannot constrain. (Running the existing `test_ecc_refine.py` closes a loose end but tests the refinement form, which is close to the already-killed phase-correlation result — do it for completeness, not for hope.) |
| **S2** | N-frame sequential consistency on tile choice | very low | cheapest alias filter; not the rejected S9 gate; exploits R06's clean bimodal gap |
| **S3** | DBoW3 vocabulary trained on own tiles | low | sidesteps the exact documented cause of both retrieval failures; enables §10.6 |
| **S4** | Robust kernel / GNC on map-fix factors, fixed-lag smoother | medium | makes fatal errors survivable instead of permanent — reframes the project's central metric |
| **S5** | Atlas-style lost mode: drop prior after N failures, go global, re-anchor | medium | published fix for the 5th iteration's cascade failure |
| **S6** | PCM or GNC over the candidate set | medium | mature version of the 7th iteration's Finding J trajectory gate |
| **S7** | RTAB-Map-style posterior with a no-match hypothesis | medium | principled abstention; feeds adaptive covariance |
| **S8** | DeepLK / DLKFM learned direct alignment | high | only if S1 shows direct alignment has signal |

**Honest framing.** None of these is measured here — §10 is survey, unlike §9.
S1–S3 are cheap enough to gate in an afternoon each. S4 is the one with the
largest conceptual payoff and the largest integration cost, since it means
replacing the ESKF path with a GTSAM smoother.

---

*Document complete — 2026-08-09. §1–8 and §10 are survey; figures marked *(snippet)*
come from search summaries and must be verified against the source before
appearing in the thesis. §9 is measured this session:
`scripts/smoke_agl_inlier_floor.py` (new), `scripts/diag_altitude_scale.py`
(existing, run on R06 for the first time). Artefacts:
`results/agl_inlier_floor_R{03,06}.json`. Ground elevation from
[OpenTopoData](https://www.opentopodata.org/) ASTER30m and SRTM30m.*
