# GPS-Denied UAV Navigation — 4th Iteration Strategy

**Project:** MTech Final Year Project, IIT Madras  
**Date:** 2026-08-07  
**Status:** Graph execution tested. S10 (inlier threshold gate) is the best Pareto improvement. Deep matching strategies (gradient templates) do NOT transfer to drone↔satellite due to scale/perspective mismatch. Full results below.

---

## 0. Test Results (2026-08-07, actual runs)

### 0.1 Shallow strategies — post-hoc filters on existing ORB pipeline

Tested on regions 03+04 (farmland), n=20/region, drift=300m, min_inliers=10.

| Strategy | Match% | CEP50 | CEP90 | Fatal50 | Yield% | Verdict |
|----------|--------|-------|-------|---------|--------|---------|
| **baseline** (ORB argmax) | 42.5 | 32.1m | 72.8m | **23.5%** | 32.5 | Reference |
| **S10_hybrid** (min_inliers≥12) | 30.0 | **28.9m** | **47.3m** | **8.3%** | **27.5** | **BEST PARETO** |
| S2_confidence (rule-based) | 22.5 | 39.2m | 49.7m | 11.1% | 20.0 | CEP50 WORSE |
| S9_temporal (150m dev gate) | 5.0 | 27.0m | 28.1m | 0.0% | 5.0 | Too aggressive |
| combined (S2+S9) | 5.0 | 18.1m | 24.1m | 0.0% | 5.0 | Too aggressive |
| S5_global (DINOv2 sim gate) | 42.5 | 32.1m | 72.8m | 23.5% | 32.5 | Pass-through (needs pipeline mod) |
| S7_phase (refinement) | 42.5 | 32.1m | 72.8m | 23.5% | 32.5 | Pass-through (needs pipeline mod) |
| S8_altitude (50-500m gate) | 20.0 | 21.5m | 69.2m | 25.0% | 15.0 | **Killed R04** (heights are absolute, not AGL) |

**Key finding: S10_hybrid (simply raising the inlier threshold to 12) is the only strategy that achieves a genuine Pareto improvement — fatal50 drops 23.5%→8.3%, CEP90 drops 72.8m→47.3m, with only moderate yield loss (32.5%→27.5%).** This is consistent with the 3rd iteration's finding that fatal matches cluster at low inlier counts.

### 0.2 Deep strategies — modified matching pipeline

| Strategy | Result | Root cause |
|----------|--------|------------|
| **D1_gradient** (Werner-style gradient templates) | **0% match rate** | Drone/satellite images have vastly different scales and perspectives. Gradient NCC scores max 0.035 (needs >0.2). Werner uses LiDAR heightmaps at similar resolution — NOT optical images at different GSDs. **Does not transfer.** |
| **D3_expanded** (49-tile search radius=3) | Timeout (>300s) | Without feature cache, 49 ORB extractions per frame is too slow. Would need tile feature cache (exists but not used in deep test). |
| D4_learned (SuperPoint+LightGlue) | Not tested (GPU required) | Kornia LightGlue needs CUDA. Would need to test on GPU machine. |
| D5_coarse_fine (global DINOv2 → ORB) | Not tested | Depends on DINOv2 retriever working as global search. |

### 0.3 What to adopt NOW

1. **min_inliers=10 is confirmed optimal.** Full 6-region sweep (n=40, drift=300m):

   | min_inliers | Match% | CEP50 | CEP90 | Fatal50 | Yield% |
   |-------------|--------|-------|-------|---------|--------|
   | 8 | 25.0 | 34.6m | 336.0m | 35.0% | 16.2% |
   | **10** | **16.2** | **23.1m** | **47.7m** | **10.3%** | **14.6%** |
   | 12 | 12.1 | 23.1m | 47.7m | 10.3% | 10.8% |
   | 14 | 11.7 | 23.1m | 48.0m | 10.7% | 10.4% |

   Going from 10→12→14 reduces match rate but does NOT improve CEP50, CEP90, or fatal50. The knee is firmly at 10. **No change needed.**

2. The S10_hybrid improvement in the shallow test (fatal50 23.5%→8.3%) was an artifact of testing on a small subset (n=20, 2 regions) with a different drift realization. The full 6-region test confirms min_inliers=10 is at the knee.

### 0.4 What NOT to pursue

- **Gradient template matching (Werner-style)** — confirmed non-transferable to drone↔satellite optical imagery. Different scale, different perspective, different modality.
- **Altitude gating based on CSV height field** — heights are absolute (ellipsoidal), not AGL. Would need barometric AGL which is not available in the dataset.
- **Post-hoc DINOv2 similarity gate** — the DINOv2 index is prior-centred (not global), so it cannot distinguish correct from incorrect matches when the prior is wrong.

### 0.5 What still needs real work (pipeline modifications)

- **S7: Phase correlation refinement INSIDE the pipeline** — currently applied AFTER tile selection (map_matcher.py:471-489), so it cannot fix wrong-tile decisions. Needs to be moved into the candidate evaluation loop.
- **D5: Global DINOv2 retrieval** — the `DINOv2Retriever.retrieve()` method already supports global search (pass `pred_tile=None`). Just needs to be wired into MapMatcher as a genuine coarse stage.
- **D3: Expanded search with feature cache** — the `TileFeatureCache` already exists. D3 just needs to use it to avoid re-extracting ORB for 49 tiles per frame.
- **D4: SuperPoint+LightGlue** — needs GPU. Already implemented in `feature_matcher.py`. Just needs testing.

---

## 1. Paradigm Shift: Map Matching as Loop Closure, Not Primary

The 3rd iteration revealed a fundamental architectural problem: **the pipeline treats map matching as the primary position source, not as loop closure.** This creates unrealistic reliability requirements — every frame's match must be correct, because there's no fallback.

**Real-world architecture:**
```
IMU (100 Hz) ──► VIO ──► Relative pose estimates (drift accumulating)
                            │
                            ▼
                    ┌───────────────┐
                    │  DRIFTING     │
                    │  TRAJECTORY   │
                    └───────┬───────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │  MAP MATCHING (0.5-2 Hz)    │
              │  ═══════════════════════    │
              │  Serves as LOOP CLOSURE     │
              │  - Detects when trajectory  │
              │    revisits known area      │
              │  - Corrects accumulated     │
              │    drift, not position      │
              │  - Must be RELIABLE, not    │
              │    frequent                 │
              └─────────────────────────────┘
```

**Key insight:** If VIO is primary and map matching is loop closure:
- Map matching doesn't need to work every frame
- Map matching needs **near-zero false positive rate**
- Map matching can use VIO's relative motion to constrain search
- The system can tolerate long gaps between successful matches
- **Fatal error tolerance is much lower** — a wrong loop closure is catastrophic

**Current baseline (3rd iteration, min_inliers=10):**
| Metric | Value | Verdict |
|--------|-------|---------|
| Match rate | 16.2% | Low but acceptable for loop closure |
| Fatal50 | 10.3% | **Unacceptable** — 1 in 10 corrections is wrong |
| Working terrain | Farmland only | Must expand to all terrains <500m |

**Target for 4th iteration:**
| Metric | Target | Rationale |
|--------|--------|-----------|
| Match rate | 10-20% | Acceptable for loop closure |
| Fatal50 | **< 1%** | Loop closure must be near-perfect |
| Working terrain | **All types** | Farmland, suburban, forest, mountain, riverside |

---

## 2. What Has Been Tried and Failed (Do Not Repeat)

### 2.1 Sequence Filtering Methods (all failed to improve median accuracy)

| Method | Source | Why it failed |
|--------|--------|---------------|
| **Particle filter** | Werner et al. 2025 | Helps only where argmax failed (region 01: 484→269m), hurts where it works (region 03: 21→119m). Tail-taming device that costs median accuracy. |
| **HMM** | Newson & Krumm 2009 | Cannot work: region 01's matched frames are isolated (9, 34, 35, 37 of 40), almost no temporal adjacency to chain. |
| **Multi-frame pooling** | Video2BEV / MuSe-Net | Catastrophic with naive centroid (924m). Fixing to largest-cluster selection gave 145m — still worse than argmax. |
| **More sequence filtering** | §6b summary | Four methods tested; none improved median accuracy. Region 01's matched frames too sparse to chain. |

### 2.2 Semantic/Abstraction Matching (all failed to close gap)

| Attempt | Segmentation | Matching | Result |
|---------|--------------|----------|--------|
| **Classical HSV/edge** | Heuristic | Blob correspondence + RANSAC | **0/11** regions passed inlier threshold |
| **Classical HSV/edge** | Heuristic | Flat-render + NCC template | **4/11** regions weakly beat raw pixel |
| **Trained Firefly** | Real pretrained segmenter (ECCV 2026) | Flat-render + NCC template | **5/11** regions beat baselines, but still below production pipeline |

**Conclusion:** Segmentation quality (not matching algorithm) was the limiting factor. Even best version doesn't approach production accuracy.

### 2.3 Rejection Gates (both failed)

| Gate | Result |
|------|--------|
| **Reprojection-residual gate** | Best case 35.0 → 32.6% fatal, but cost 20% of useful fixes. No Pareto gain. |
| **Margin gate** | Made fatal errors **worse** (35.0 → 40.0%). On repeating terrain, contested frames are disproportionately the correct ones. |

### 2.4 Parameter Tuning (hit the wall)

| Parameter | Finding |
|-----------|---------|
| **min_inliers** | Knee at 10, sharp (9 gives 21.7% fatal). Drift-independent. Cannot improve further by threshold tuning. |
| **features / ratio** | Axis is coverage/accuracy tradeoff, not unexploited optimum. Two graph searches confirmed. |
| **More parameter tuning** | Explicitly not recommended. The knee is reached. |

### 2.5 Other Negative Results

| Result | Root cause |
|--------|------------|
| Particle filter apparent win at zero drift (11.8m CEP50) | **Artifact:** filter initialises particles at prior, at zero drift prior is ground truth. Monotone-to-the-edge sweep with no interior optimum was the tell. **All zero-drift PF numbers void.** |
| Multi-frame catastrophic result (924m CEP50) | **Bug:** naive centroid averaging across spatial modes — the bug the cited paper exists to solve. |
| Region 08 fails at every config | Non-planar scene structure (buildings/elevation) breaking flat-ground homography assumption. Or tile/GT coordinate mismatch. |
| Region 01 "matches but wildly wrong" | **Drift-triggered**, not intrinsic. 72m at 150m drift → 483m at 300m drift. Perceptual aliasing when look-alike tile enters candidate set. |

---

## 3. New Strategies to Test

### Strategy 1: Trajectory-Based Loop Closure

**Core idea:** Instead of matching each frame independently, accumulate VIO trajectory segments and match the trajectory *shape* against the map.

**Why it might work:**
- VIO's relative motion is more reliable than its absolute position
- A trajectory segment has much more structure than a single frame
- Even if individual frames are ambiguous, the trajectory shape is distinctive
- Naturally handles the "loop closure" paradigm

**Implementation:**
```
For each frame t:
  1. Accumulate VIO pose deltas: T_0, T_1, ..., T_t
  2. Extract trajectory segment: [p_0, p_1, ..., p_t] in local frame
  3. Match segment against map:
     - For each candidate location x on map:
       - Render expected trajectory segment if drone were at x
       - Compute similarity: shape matching + feature matching
     - Accept if similarity > threshold AND inlier count > min_inliers
  4. If accepted: correct VIO drift, reset accumulation window
```

**Test nodes:**
- `T1a`: Window size (5, 10, 20, 50 frames)
- `T1b`: Shape descriptor (Hausdorff distance, DTW, FFT)
- `T1c`: Feature matching within trajectory window (ORB, XFeat, gradient)

**Expected benefit:** High for non-planar scenes (region 08), where single-frame homography fails.

**Risk:** VIO drift may corrupt trajectory shape over long windows. Mitigation: use sliding window with exponential decay.

---

### Strategy 2: Confidence-Gated Corrections

**Core idea:** Learn to predict match reliability BEFORE applying correction. Only correct when confidence is high.

**Why it might work:**
- Current system has no confidence signal — all matches treated equally
- A learned confidence predictor can identify "this match is likely wrong"
- Enables the system to say "I don't know" rather than guessing

**Implementation:**
```
For each match attempt:
  1. Extract features: inlier_count, homography_condition, scene_texture,
     view_angle, match_score, margin_to_runner_up, etc.
  2. Feed to confidence predictor: confidence = f(features)
  3. If confidence > threshold:
     - Apply correction
  4. Else:
     - Reject match, continue with VIO-only
```

**Training:**
- Train on labeled data: (features, match_correct: bool)
- Match is "correct" if error < 20m from ground truth
- Use logistic regression, random forest, or small MLP

**Test nodes:**
- `T2a`: Feature set (minimal vs. full)
- `T2b`: Predictor type (logistic, RF, MLP)
- `T2c`: Confidence threshold (0.5, 0.7, 0.9)

**Expected benefit:** Reduces fatal error rate by rejecting low-confidence matches.

**Risk:** May reject good matches if confidence predictor is poorly calibrated.

---

### Strategy 3: Multi-Modal Feature Fusion

**Core idea:** Combine multiple feature types (ORB, XFeat, gradient templates, structural features). Different features work in different terrains.

**Why it might work:**
- ORB works well on farmland (texture-rich)
- Gradient templates work on mountain/forest (Werner won with this)
- Structural features (edges, contours) work on urban
- No single feature type works everywhere

**Implementation:**
```
For each frame:
  1. Extract multiple feature types:
     - ORB keypoints + descriptors
     - XFeat keypoints + descriptors
     - Gradient template (Sobel/Scharr)
     - Structural features (Canny edges, line segments)
  2. For each feature type, compute match score against candidate tiles
  3. Fuse scores: weighted_sum = sum(w_i * score_i)
  4. Accept if weighted_sum > threshold AND consensus > min_consensus
```

**Test nodes:**
- `T3a`: Feature combination (ORB+XFeat, ORB+gradient, all four)
- `T3b`: Fusion method (weighted sum, max vote, learned fusion)
- `T3c`: Terrain-adaptive weighting (fixed vs. scene-class-dependent)

**Expected benefit:** Expands working terrain from farmland-only to all types.

**Risk:** Increased computation. Multiple feature extractions per frame.

---

### Strategy 4: Scene Classification + Specialized Matchers

**Core idea:** Classify scene type (farmland, urban, forest, water, mountain), then route to terrain-specific matching strategy.

**Why it might work:**
- Different terrains have different visual characteristics
- A single matcher cannot be optimal for all terrains
- Specialized matchers can exploit terrain-specific structure

**Implementation:**
```
For each frame:
  1. Classify scene type:
     - Use lightweight CNN (MobileNet) or hand-crafted features
     - Classes: farmland, urban, forest, water, mountain, desert
  2. Route to specialized matcher:
     - Farmland: ORB + homography (current pipeline, works well)
     - Urban: structural features (building footprints, road networks)
     - Forest: gradient templates + texture
     - Water: skip (no reliable features)
     - Mountain: elevation + horizon matching
     - Desert: gradient templates (Werner-style)
  3. Apply matcher-specific thresholds
```

**Test nodes:**
- `T4a`: Classifier type (CNN, SVM on hand-crafted features, rule-based)
- `T4b`: Number of terrain classes (3, 6, 10)
- `T4c`: Matcher specialization (fully separate vs. parameter adaptation)

**Expected benefit:** Each terrain uses its best matcher, improving overall coverage.

**Risk:** Classifier errors propagate. Need high classifier accuracy.

---

### Strategy 5: Global Place Recognition as Trigger

**Core idea:** Use DINOv2 for global place recognition (already in codebase). When place recognition detects a known location, trigger fine map matching.

**Why it might work:**
- DINOv2 retrieval index already exists but is only used to supplement prior-centred candidates
- Running it as a true global search makes drift question moot
- Place recognition is robust to viewpoint/illumination changes
- This is true loop closure: recognize "I've been here before"

**Implementation:**
```
Offline:
  1. Build DINOv2 embedding index over entire map (all tiles)
  2. Store tile embeddings with geographic coordinates

Online (each frame):
  1. Extract DINOv2 embedding from drone image
  2. Query index: find top-k similar tiles (global search)
  3. If top-1 similarity > threshold:
     - Trigger fine map matching: ORB + homography on candidate tiles
     - Accept if fine match confirms global retrieval
  4. Else:
     - No loop closure, continue with VIO
```

**Test nodes:**
- `T5a`: Index size (1k, 10k, 100k tiles)
- `T5b`: Global retrieval threshold (0.7, 0.8, 0.9 cosine similarity)
- `T5c`: Fine match confirmation (ORB, XFeat, both)

**Expected benefit:** Removes prior dependency entirely. Enables global localization.

**Risk:** DINOv2 may not be discriminative enough for global retrieval. False positives.

---

### Strategy 6: Fundamental Matrix for Non-Planar Scenes

**Core idea:** For suburban/mountain where homography fails, use fundamental matrix estimation instead. Handles non-planar scenes with 3D structure.

**Why it might work:**
- Region 08 fails at every config due to non-planar structure
- Homography assumes flat ground — breaks with buildings/elevation
- Fundamental matrix handles 3D structure (epipolar geometry)
- More general, works for both planar and non-planar scenes

**Implementation:**
```
For each frame:
  1. Detect scene planarity:
     - Attempt homography fit
     - If inlier count < threshold OR reprojection error > threshold:
       - Scene is non-planar
  2. If planar:
     - Use homography (current pipeline)
  3. If non-planar:
     - Estimate fundamental matrix F with MAGSAC
     - Decompose F into E (essential matrix) using camera intrinsics
     - Recover relative pose [R|t] up to scale
     - Use VIO altitude to resolve scale ambiguity
     - Triangulate inliers to get 3D points
     - Estimate position from 3D-2D correspondence with map
```

**Test nodes:**
- `T6a`: Planarity threshold (inlier count, reprojection error)
- `T6b`: Fundamental matrix estimator (MAGSAC, RANSAC, DEGENSAC)
- `T6c`: Scale recovery method (VIO altitude, known object size, barometer)

**Expected benefit:** Fixes region 08 and similar non-planar scenes.

**Risk:** More complex, requires camera calibration. Fundamental matrix estimation is less robust than homography for planar scenes.

---

### Strategy 7: Phase Correlation Refinement (Sub-Pixel)

**Core idea:** After initial match, use phase correlation for sub-pixel refinement. Already in codebase but applied after winner chosen — move it INTO the matching pipeline.

**Why it might work:**
- cpvrLab achieves 12.5m radius with coarse-to-fine approach
- Phase correlation provides sub-pixel accuracy
- Current pipeline has phase correlation but it cannot fix a wrong-tile decision
- Moving it into the pipeline enables fine refinement

**Implementation:**
```
Two-stage coarse-to-fine:

Stage 1 (Coarse):
  1. Retrieve candidate tiles (DINOv2 or prior-centred)
  2. ORB matching + homography
  3. Select winner tile

Stage 2 (Fine):
  4. Extract high-resolution crop from winner tile neighbourhood
  5. Apply phase correlation between drone image and crop
  6. Get sub-pixel translation estimate
  7. Refine position: pos_refined = pos_coarse + phase_corr_offset
```

**Test nodes:**
- `T7a`: Crop size (200x200, 400x400, 800x800 pixels)
- `T7b`: Phase correlation parameters (window size, masking)
- `T7c`: Multi-scale refinement (1 pass, 2 passes, 3 passes)

**Expected benefit:** Improves accuracy from 20-40m to <15m.

**Risk:** Phase correlation assumes small translation. If coarse match is wrong, refinement won't help.

---

### Strategy 8: Altitude-Aware Matching

**Core idea:** Use barometric altitude to adjust GSD (ground sample distance) and account for perspective effects. Critical for 0-500m altitude range.

**Why it might work:**
- Current pipeline copies altitude from prior (structurally zero error)
- At different altitudes, the same ground feature appears at different scales
- Perspective distortion changes with altitude
- Altitude awareness enables correct scale matching

**Implementation:**
```
For each frame:
  1. Get altitude from barometer (or VIO if barometer unavailable)
  2. Compute GSD: gsd = sensor_height * altitude / (focal_length * image_height)
  3. Rescale drone image to match satellite GSD:
     - satellite_gsd is known (e.g., 0.3 m/pixel)
     - scale_factor = gsd / satellite_gsd
     - resized_drone = resize(drone_image, scale_factor)
  4. Match resized_drone against satellite tile
  5. Apply perspective correction if altitude > threshold (e.g., 200m)
```

**Test nodes:**
- `T8a`: GSD estimation method (barometer, VIO, known object size)
- `T8b`: Rescaling method (nearest, bilinear, bicubic)
- `T8c`: Perspective correction (none, affine, full homography)

**Expected benefit:** Improves accuracy across altitude range. Reduces scale ambiguity.

**Risk:** Barometer drift. Altitude estimation errors propagate to GSD.

---

### Strategy 9: Temporal Consistency Filter (Lightweight)

**Core idea:** Simple temporal consistency check — if new match is wildly different from recent trajectory, reject. NOT a full particle filter (that failed).

**Why it might work:**
- Full particle filter failed (too complex, hurt median accuracy)
- But simple outlier rejection based on VIO prediction can catch bad matches
- VIO provides relative motion prediction
- If match deviates > threshold from VIO prediction, reject

**Implementation:**
```
For each frame:
  1. VIO predicts position: pred_pos = prev_pos + VIO_delta
  2. Map matching gives: match_pos
  3. Compute deviation: dev = ||match_pos - pred_pos||
  4. If dev < threshold:
     - Accept match, update position
  5. Else:
     - Reject match, use VIO prediction
     - Increment "coasting" counter
  6. If coasting > max_coast:
     - Relax threshold (emergency mode)
```

**Test nodes:**
- `T9a`: Threshold (50m, 100m, 200m)
- `T9b`: Max coasting frames (10, 20, 50)
- `T9c`: Threshold adaptation (fixed vs. VIO-covariance-based)

**Expected benefit:** Catches outlier matches that pass inlier threshold.

**Risk:** May reject good matches if VIO drift is large.

---

### Strategy 10: Hybrid Appearance + Structure

**Core idea:** Combine appearance matching (ORB/DINOv2) with structural matching (edges, contours). Appearance works in farmland, structure works in urban.

**Why it might work:**
- Appearance features (ORB) fail in repetitive/textureless scenes
- Structural features (edges, lines) are more invariant to lighting/season
- Combining both leverages complementary strengths

**Implementation:**
```
For each frame:
  1. Extract appearance features: ORB keypoints + descriptors
  2. Extract structural features:
     - Canny edge detection
     - Line segment detection (LSD)
     - Contour extraction
  3. Compute appearance score: score_app = match(ORB_drone, ORB_tile)
  4. Compute structural score: score_str = match(edges_drone, edges_tile)
  5. Fuse: score = alpha * score_app + (1-alpha) * score_str
  6. Accept if score > threshold AND inlier_count > min_inliers
```

**Test nodes:**
- `T10a`: Structural feature type (edges, lines, contours, all)
- `T10b`: Fusion method (weighted sum, max, learned)
- `T10c`: Alpha (fixed 0.5, terrain-adaptive, learned)

**Expected benefit:** Improves performance in urban/suburban scenes where appearance fails.

**Risk:** Structural features may be less discriminative than appearance. Increased computation.

---

## 4. Graph Execution Framework

### 4.1 Graph Structure

```
ROOT (baseline: argmax, ORB, min_inliers=10)
  │
  ├──► S1: Trajectory-Based Loop Closure
  │      ├── T1a: Window size (5, 10, 20, 50)
  │      ├── T1b: Shape descriptor (Hausdorff, DTW, FFT)
  │      └── T1c: Feature matching (ORB, XFeat, gradient)
  │
  ├──► S2: Confidence-Gated Corrections
  │      ├── T2a: Feature set (minimal, full)
  │      ├── T2b: Predictor (logistic, RF, MLP)
  │      └── T2c: Threshold (0.5, 0.7, 0.9)
  │
  ├──► S3: Multi-Modal Feature Fusion
  │      ├── T3a: Feature combo (ORB+XFeat, ORB+grad, all)
  │      ├── T3b: Fusion (weighted sum, max vote, learned)
  │      └── T3c: Weighting (fixed, terrain-adaptive)
  │
  ├──► S4: Scene Classification + Specialized Matchers
  │      ├── T4a: Classifier (CNN, SVM, rule-based)
  │      ├── T4b: Num classes (3, 6, 10)
  │      └── T4c: Matcher spec (separate, parameter adapt)
  │
  ├──► S5: Global Place Recognition Trigger
  │      ├── T5a: Index size (1k, 10k, 100k)
  │      ├── T5b: Retrieval threshold (0.7, 0.8, 0.9)
  │      └── T5c: Fine match (ORB, XFeat, both)
  │
  ├──► S6: Fundamental Matrix (Non-Planar)
  │      ├── T6a: Planarity threshold
  │      ├── T6b: F estimator (MAGSAC, RANSAC, DEGENSAC)
  │      └── T6c: Scale recovery (VIO alt, known size, baro)
  │
  ├──► S7: Phase Correlation Refinement
  │      ├── T7a: Crop size (200, 400, 800)
  │      ├── T7b: Phase corr params (window, mask)
  │      └── T7c: Multi-scale (1, 2, 3 passes)
  │
  ├──► S8: Altitude-Aware Matching
  │      ├── T8a: GSD estimation (baro, VIO, known size)
  │      ├── T8b: Rescaling (nearest, bilinear, bicubic)
  │      └── T8c: Perspective correction (none, affine, full)
  │
  ├──► S9: Temporal Consistency Filter
  │      ├── T9a: Threshold (50m, 100m, 200m)
  │      ├── T9b: Max coast (10, 20, 50)
  │      └── T9c: Threshold adapt (fixed, VIO-cov-based)
  │
  └──► S10: Hybrid Appearance + Structure
         ├── T10a: Structural feature (edges, lines, contours, all)
         ├── T10b: Fusion (weighted sum, max, learned)
         └── T10c: Alpha (fixed, terrain-adaptive, learned)
```

### 4.2 Execution Protocol

**For each strategy node:**

1. **Isolate from production pipeline.** Test in standalone harness (like `graph_search_config.py`), not production DINOv2 retrieval + multi-tile competition.

2. **Inject realistic prior drift.** Never use ground truth as prior. Test at drift = 150m, 300m, 600m.

3. **Report correct metrics.** Never report CEP50 alone. Always report:
   - Match rate (%)
   - CEP50 (m)
   - CEP90 (m)
   - **Fatal50 (%)** — primary metric
   - Good yield (%)

4. **Test on all 6 regions.** Do not cherry-pick. Report per-region AND aggregate.

5. **Check for harness-to-production transfer.** If isolated harness shows promise, test in full production pipeline before adopting.

6. **Check for monotone-to-the-edge sweeps.** If parameter sweep shows monotonic improvement to edge, result is suspicious. Require interior optimum.

7. **Adequate sample size.** Minimum n=40 per region (like 3rd iteration). Do not let n≈12 smoke test set direction.

### 4.3 Decision Criteria

**Adopt a strategy if:**
- Fatal50 < 5% (vs. baseline 10.3%)
- Match rate > 10% (acceptable for loop closure)
- Works on >= 4 of 6 regions (vs. baseline 2 of 6)
- No monotone-to-the-edge artifact
- Transfers from harness to production

**Reject a strategy if:**
- Fatal50 >= 10% (no improvement over baseline)
- Works on <= 2 regions (no terrain expansion)
- Monotone-to-the-edge sweep
- Does not transfer to production
- Incompatible with real-time constraint (<100ms per frame)

### 4.4 Testing Priority Order

Ranked by expected benefit per unit of effort:

| Priority | Strategy | Rationale |
|----------|----------|-----------|
| **1** | S5: Global Place Recognition | DINOv2 index already exists. Removes prior dependency entirely. Addresses P3 from 3rd iteration. |
| **2** | S7: Phase Correlation Refinement | Already in codebase, just needs to be moved into pipeline. Addresses P2 from 3rd iteration. Low effort. |
| **3** | S2: Confidence-Gated Corrections | Directly attacks fatal error rate. Learnable from existing data. |
| **4** | S3: Multi-Modal Fusion | Werner won with gradient templates. Combining with ORB should help. |
| **5** | S9: Temporal Consistency Filter | Simple, lightweight, catches outliers. Easy to implement. |
| **6** | S8: Altitude-Aware Matching | Barometer already available. Fixes scale ambiguity. |
| **7** | S6: Fundamental Matrix | Fixes region 08 (non-planar). More complex but targeted. |
| **8** | S10: Hybrid Appearance + Structure | Combines strengths. Moderate effort. |
| **9** | S1: Trajectory-Based Loop Closure | High potential but complex. Requires careful VIO integration. |
| **10** | S4: Scene Classification | Requires training data for classifier. Higher effort. |

---

## 5. Revised Implementation Plan (after testing)

Based on the graph execution results (Section 0), the implementation plan is revised. The parameter tuning axis is **exhausted** (knee at min_inliers=10). The only remaining improvements come from pipeline modifications.

### Phase 1: Quick Pipeline Fixes (Week 1)

**P1: Move phase correlation INSIDE the candidate evaluation loop**
- Currently: phase correlation is applied AFTER the winner is chosen (map_matcher.py:471-489)
- Fix: apply phase correlation to each candidate's crop, use it as a refinement signal BEFORE selecting the winner
- Expected: sub-pixel accuracy improvement, especially on farmland (regions 03, 04)
- Effort: 1-2 hours of code changes

**P2: Wire global DINOv2 retrieval as coarse stage**
- Currently: DINOv2 retrieval is prior-centred (tile_radius=5)
- Fix: run DINOv2 as a true global search (pred_tile=None), then ORB-fine-match the top-k results
- Expected: removes prior dependency, enables global localization
- Effort: 2-3 hours of code changes
- Risk: DINOv2 may not be discriminative enough for global retrieval

**P3: Enable tile feature cache in expanded search**
- Currently: MapMatcher only evaluates 5+4 tiles (centre + cardinal + corners)
- Fix: use the existing TileFeatureCache to evaluate up to 49 tiles (radius=3) without re-extracting ORB
- Expected: helps when drift > 200m pushes correct tile outside 5+4 set
- Effort: 1-2 hours

### Phase 2: Terrain-Specific Testing (Week 2)

**Test the above 3 fixes on all 6 regions under drift=150m, 300m, 600m**
- Report per-region AND aggregate metrics
- Key question: do the pipeline fixes expand working terrain beyond farmland?

**If P2 (global DINOv2) works:**
- This is the single biggest potential win — removes prior dependency entirely
- Test recall@k for k=1,5,10 against ground truth

**If fixes don't help broken regions (01, 06, 08):**
- Region 08 needs fundamental matrix (non-planar geometry)
- Region 06 (mountain/forest) needs structural features
- Region 01 (riverside) needs perceptual aliasing protection

### Phase 3: Advanced (Week 3-4, only if Phase 1-2 succeed)

**P4: Fundamental matrix for non-planar scenes**
- Detect non-planar scenes (reprojection error > threshold)
- Switch from homography to fundamental matrix estimation
- Expected: fixes region 08 (suburban with buildings)
- Effort: 1-2 days

**P5: SuperPoint+LightGlue as alternative matcher**
- Already implemented in feature_matcher.py (lines 204-280)
- Test as primary matcher (replacing ORB) on GPU machine
- Expected: more robust features, especially in low-texture scenes
- Effort: 1 day (needs GPU access)

### NOT pursuing (confirmed non-viable)

- **Gradient template matching (Werner-style)** — confirmed non-transferable (scale/perspective mismatch)
- **More parameter tuning** — knee at min_inliers=10, confirmed with full sweep
- **Altitude gating** — dataset heights are absolute, not AGL
- **Post-hoc DINOv2 similarity gate** — index is prior-centred, not global

---

## 6. Reporting Rules (Carry Forward from 3rd Iteration)

1. **Report fatal-error rate and yield, not CEP50 alone.** The median is blind to the failure mode that matters.

2. **Never quote a number measured with the prior set to ground truth** without labelling it an upper bound.

3. **Never cross-quote between benchmark harnesses.** Different harnesses give different numbers.

4. **Treat a monotone-to-the-edge parameter sweep as unfinished, not as a result.**

5. **Do not let an n≈12 smoke test set search direction.** Require n>=40.

6. **Check harness-to-production transfer** before adopting any result.

---

## 7. Expected Outcomes (Revised After Testing)

**What was confirmed:**
- min_inliers=10 is the optimal threshold. Full sweep (8/10/12/14) confirms knee at 10.
- Post-hoc filtering strategies (S2, S9, S10) reduce fatal errors but at extreme yield cost.
- Gradient template matching (Werner-style) does NOT transfer to drone↔satellite imagery.
- The parameter tuning axis is exhausted.

**What the pipeline modifications (Phase 1) can realistically achieve:**
- P1 (phase correlation inside loop): CEP50 improvement from ~23m to ~15m on farmland
- P2 (global DINOv2): if it works, removes prior dependency entirely — the biggest potential win
- P3 (expanded search with cache): helps when drift > 200m, modest improvement

**What will NOT close the terrain gap:**
- Region 06 (mountain/forest) and 08 (suburban) still fail because the homography model is wrong for non-planar scenes. This requires fundamental matrix (P4) or a different geometric model.
- Region 01 (riverside) fails from perceptual aliasing. Only global retrieval (P2) or trajectory-based methods can address this.

**Realistic target after Phase 1:**
| Metric | Current | Target | Depends on |
|--------|---------|--------|------------|
| Fatal50 | 10.3% | < 5% | P1, P2 |
| Match rate | 16.2% | 15-20% | P3 |
| Working terrain | 2/6 regions | 3-4/6 | P2, P4 |
| CEP50 | 23.1m | < 20m | P1 |

**If P2 (global DINOv2 retrieval) fails:**
- The system remains prior-dependent and cannot localize without a prior good to ~1 tile.
- The remaining path is trajectory-based loop closure (S1) or fundamental matrix (P4).

---

## 8. Open Questions (Updated)

1. **DINOv2 index size:** 5,234 tiles at zoom 17 (7.7 MB). Tile range: X=[102313, 109318], Y=[49451, 56270]. Suitable for global search — the entire indexed area is ~7000×6800 tiles = ~1800km×1700km at zoom 17 (each tile ≈ 256m at equator, but these are clustered around the flight regions).

2. **Global DINOv2 recall:** When run as true global search (pred_tile=None), what is recall@1? If > 70%, P2 is viable.

3. **GPU availability:** SuperPoint+LightGlue (P5) needs CUDA. Is there a GPU machine for testing?

4. **Camera intrinsics for fundamental matrix:** CAMERA_K is hardcoded as fx=950, cx=684, cy=456. Is this calibrated correctly for region 08?

---

*Document generated: 2026-08-07 | Version: 4th Iteration Strategy (revised, after graph execution) | Status: **Tested** — parameter axis exhausted (knee at min_inliers=10 confirmed), shallow strategies mapped, deep strategies partially tested (gradient N/A), pipeline modifications identified as only remaining path. Test scripts shipped: `scripts/graph_search_4th_iteration.py` (shallow), `scripts/graph_search_deep.py` (deep).*

---

> **Follow-up — 5th Iteration (2026-08-08) addressed these open questions:**
>
> - **Q3 (GPU availability): RESOLVED.** `kp_vio_py\.venv` ships torch 2.2.2+cu121
>   with CUDA available + kornia 0.8.2 — SuperPoint+LightGlue ran successfully
>   on this machine. **But LightGlue returned 0 matches on every drone↔satellite
>   pair** (single-frame probe confirmed) — a domain-gap failure generalising
>   the gradient-template finding: *learned matchers trained on ground-level
>   imagery do not transfer to aerial↔satellite*. LightGlue / GlueStick / LIMAP
>   / HardNet retired from the candidate pool.
> - **Q4 (camera intrinsics for fundamental matrix on R08): RENDERED MOOT.**
>   Multi-feature pooled matching (ORB+AKAZE+SIFT) now produces enough inliers
>   on R08 to pass `min_inliers=10` with the flat-ground homography — R08 was
>   never a non-planar-geometry problem, it was an **inlier-count problem
>   masquerading as a geometry problem**. R08 now matches at 7.5% @ 0% fatal
>   (300 m drift) and 5% @ 0% fatal (600 m drift) without any fundamental-matrix
>   work. **The 3rd/4th-iter diagnosis was wrong.**
> - **Q1/Q2 (DINOv2 global recall): CONFIRMED NON-VIABLE** — 5.4% match in 4th-iter
>   was reproduced by CosPlace (4.2% match @ n=40 in 5th-iter), another
>   ground-trained retriever. Neither DINOv2 CLS nor CosPlace is discriminative
>   enough for aerial↔satellite cross-view retrieval. Closing the remaining
>   `fatal50<5%` gap requires cross-view-TRAINED retrieval (Sample4Geo /
>   AnyLoc-VLAD-DINOv2), flagged as next iteration.
> - **Adoption:** 5th iteration shipped a **multi-feature fusion + patch-wide
>   NCC verify** mode (`multi_feature=True, ncc_verify=0.30`) on production
>   `MapMatcher`. 5/6 terrains now produce matches at every drift (vs 2/6);
>   yield roughly doubled at every drift (150m: 13.3→27.1%, 300m: 14.6→26.7%,
>   600m: 9.2→18.3%); R03 farmland 0% fatal at 80% match; R06 forest first-ever
>   matches (10% at 150/300/600 m, **drift-independent** — first such result
>   in this project). R04 repetitive-furrow and R06 repetitive-canopy tails
>   (~21/25% fatal) remain — flagged as needing cross-view-trained retrieval.
>   See `5th_iteration.md` for the full per-scene tables at three drifts.
