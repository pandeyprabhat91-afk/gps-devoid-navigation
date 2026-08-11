# HANDOVER DOCUMENT — kp_vio GPS-Denied UAV Navigation Project

**Date:** 2026-08-08
**Author:** opencode (glm-5.2) autonomous R&D session
**Git repo:** `E:\kp_vio` (branch `5th-iteration/multi-feature-ncc`)
**For:** next model / developer picking up this project

---

## 1. PROJECT STATE IN ONE PARAGRAPH

GPS-denied UAV navigation by matching nadir drone camera frames to satellite
map tiles. Python VIO (ESKF + ORB-KLT tracker) provides a drifted position
prior; a `MapMatcher` selects candidate tiles around that prior and matches
using ORB+AKAZE+SIFT pooled features + MAGSAC homography + patch-wide NCC
verification; corrections are injected into the ESKF as loop-closure
measurements. The map matcher works on farmland (80-90% match, 0% fatal,
13-24m CEP50) and produces first-ever matches on forest (10%) and non-planar
suburban (7.5%), but a ~11% fatal-error tail remains on repetitive-texture
scenes. End-to-end VIO+loop-closure was validated on R04 (57.5% drift
reduction, 100% match rate, 24m median match error).

---

## 2. GIT REPO

```
E:\kp_vio\  (git repo, initialized this session)
  main branch:
    9ea67c4  Initial commit (337 files: source + configs + docs)
    62047b9  Iteration summaries (1st-5th) + .gitignore
  5th-iteration/multi-feature-ncc branch (current):
    03b6740  E2E loop-closure test + 5th-iter code

  .gitignore excludes: datasets (50GB), venvs (5GB), results, .external/,
    *.sqlite, *.npz, *.pth, *.pdf, *.log

  327 files tracked. Working dir clean.
```

**To push to GitHub**: `git remote add origin <url> && git push -u origin main`

---

## 3. KEY PATHS

| what | path |
|---|---|
| Python venv (torch+CUDA) | `E:\kp_vio\kp_vio_py\.venv\Scripts\python.exe` |
| Production MapMatcher | `kp_vio_py/kp_vio/map_matching/map_matcher.py` |
| Feature matchers (ORB/AKAZE/SIFT/LightGlue) | `kp_vio_py/kp_vio/map_matching/feature_matcher.py` |
| VIO pipeline | `kp_vio_py/pipelines/vio_pipeline.py` |
| VIO+Map integration | `kp_vio_py/pipelines/vio_map_pipeline.py` |
| ESKF backend | `kp_vio_py/kp_vio/backend/eskf.py` |
| Tile DB (117MB, gitignored) | `kp_vio_py/datasets/uav_visloc/tiles.sqlite` |
| Retrieval index (DINOv2) | `kp_vio_py/datasets/uav_visloc/retrieval_index.npz` |
| Tile feature cache (1.4GB) | `kp_vio_py/datasets/uav_visloc/tile_features.sqlite` |
| UAV-VisLoc dataset (10GB) | `kp_vio_py/datasets/uav_visloc/{01,03,04,06,08,09}/` |
| Iteration reports | `summary/1st_iteration.md` through `summary/5th_iteration.md` |
| E2E test results | `kp_vio_py/results/e2e_loop_closure/` |
| Comprehensive bench results | `kp_vio_py/results/comprehensive/` |
| IMU calibration | `config/imu_calib.yaml` |

**IMPORTANT**: Always run scripts with the venv python, NOT system python:
```powershell
& "E:\kp_vio\kp_vio_py\.venv\Scripts\python.exe" -X utf8 scripts/<script>.py
```
System python lacks torch → DINOv2 retrieval and LightGlue silently fail.

---

## 4. WHAT'S BEEN DONE (iterations 1-5 summary)

| iter | what happened | status |
|---|---|---|
| 1st | Architecture proposed (satellite matching) | superseded |
| 2nd | Pivoted to nested-filter research direction | parallel track |
| 3rd | Production bug fixed (H_inv position method), benchmark prior-leak identified, min_inliers raised 8→10 (fatal 35%→10.3%), 4 sequence methods tested (all rejected) | shipped |
| 4th | Parameter axis exhausted (knee at min_inliers=10), 4 pipeline mods tested in isolation (all regressed), 10 strategies proposed | tested |
| 5th | **Multi-feature (ORB+AKAZE+SIFT) pooled matching** adopted (6/6 terrains work, yield 2×, R03 90%@0%fatal). NCC verify (ncc=0.30) adopted. LightGlue rejected (0% match, domain gap). CosPlace rejected (4.2% match). E2E loop-closure validated on R04 (57.5% drift reduction). | shipped |

---

## 5. ADOPTED CONFIGURATION (what ships)

```python
MapMatcher(
    db=db, zoom=17,
    origin_ll=(lat0, lon0, alt0),
    K=CAMERA_K,
    retrieval_index="datasets/uav_visloc/retrieval_index.npz",
    feature_cache="datasets/uav_visloc/tile_features.sqlite",
    min_inliers=10,
    multi_feature=True,     # Method #3: pool ORB+AKAZE+SIFT
    ncc_verify=0.30,         # Method #4: patch-wide NCC verification
    search_radius=3,         # 7×7 = 49 candidate tiles
)
```

Default `multi_feature=False, ncc_verify=0.0` = legacy ORB-only path (unchanged).

**NCC threshold alternatives** (user picks strictness):
- `0.0` — raw Method #3 (6/6 terrains, 30.8% yield, 14% fatal)
- `0.30` — adopted (6/6 terrains, 26.7% yield, 11.1% fatal)
- `0.40` — tighter (5/6 terrains, 20.8% yield, 10.7% fatal)
- `0.50` — strictest (4/6 terrains, 11.7% yield, 9.7% fatal)

---

## 6. CURRENT PERFORMANCE NUMBERS

### 6.1 Standalone MapMatcher (drift=300m, n=40, 6 regions)

| Region | Terrain | Match% | CEP50 | Fatal50 | Yield% |
|---|---|---|---|---|---|
| R03 | farmland | **80%** | **13.3m** | **0%** | **80%** |
| R04 | farmland (repetitive) | 82.5% | 32.9m | 21.2% | 65% |
| R06 | forest | **10%** | 28.1m | 25% | 7.5% |
| R08 | suburban non-planar | **7.5%** | 18.3m | **0%** | 7.5% |
| R01 | riverside | 0% | — | — | 0% |
| R09 | suburban | 0% | — | — | 0% |
| **Aggregate** | | **30.0%** | **20.6m** | **11.1%** | **26.7%** |

### 6.2 End-to-End VIO + Loop Closure (real VIO drift, map every frame)

| Region | Match% | ESKF accepted | VIO raw drift (max) | Post-corr drift (max) | Drift reduction |
|---|---|---|---|---|---|
| **R04** | **100%** | **20/20** | 474m | **201m** | **57.5%** |
| R03 | 0% | 0 | 9,162m | 9,162m | 0% (cascade fail) |
| R06 | 0% | 0 | 27,511m | 27,511m | 0% (cascade fail) |
| R08 | 0% | 0 | 112m | 112m | 0% (cascade fail) |

---

## 7. WHAT FAILED AND WHY (do not repeat)

| method | result | root cause |
|---|---|---|
| LightGlue as primary matcher | 0% match on all 6 regions | SuperPoint trained on ground-level photos; keypoints don't fire on aerial nadir. **Domain gap generalised to ALL ground-trained matchers** (GlueStick, LIMAP, HardNet also retired) |
| CosPlace global retrieval | 4.2% match | ResNet18 trained on street-level; not discriminative for aerial↔satellite cross-view |
| DINOv2 global retrieval (P2) | 5.4% match | CLS-token global descriptor not discriminative enough for tile-level retrieval |
| Fundamental matrix (P4) | 93% fatal | Position recovery from F is ill-conditioned for near-nadir aerial pairs |
| Phase-correlation inside loop (P1) | 87.5% fatal on R03 | Per-candidate crop logic produces wrong NCC windows |
| Parameter tuning (min_inliers sweep) | knee at 10, exhausted | Fatal matches cluster at 8-9 inliers; above 10 only costs yield |
| rmse gate / softvote / margin gate | no improvement | Wrong-tile aliases have low reprojection RMSE — RANSAC self-consistent |
| Particle filter / HMM / multi-frame | no improvement | Matched frames too sparse (7-sec spacing) to chain temporally |
| Gradient template matching (Werner) | 0% match | Scale/perspective mismatch drone↔satellite |
| Semantic/abstraction matching (3 attempts) | 0-5/11 regions | Segmentation quality limiting, not matching algorithm |

---

## 8. WHAT'S NEXT (open items, priority-ordered)

### P1 — FIRST-FRAME BOOTSTRAPPING (critical, blocks deployment)
E2E test showed R03/R06/R08 fail because frame 0 doesn't match → drift cascades
past search radius → unrecoverable. Fix: **global search on first frame only**
(pred_tile=None, no prior-centred restriction), then switch to prior-centred
mode. The `DINOv2Retriever.retrieve()` already supports `pred_tile=None` —
just wire it as a one-shot first-frame mode in `VioMapPipeline`.

### P2 — CROSS-VIEW-TRAINED RETRIEVAL (closes the fatal50<5% gap)
The remaining 11% fatal tail on R04/R06 is perceptual aliasing on repetitive
texture — NCC can't distinguish because the wrong tile's warped content
genuinely looks similar. Needs a trained retriever that knows aerial↔satellite
cross-view correspondence:
- **UAV-AVL/Benchmark** (github.com/UAV-AVL/Benchmark, 188★) — GIM/MINIMA
  modality-invariant LightGlue weights, no training required, drop-in matcher
- **Sample4Geo** (github.com/Skyy93/Sample4Geo, 161★) — pretrained U1652
  weights, cross-view retrieval
- **AnyLoc/AnyLoc** (github.com/AnyLoc/AnyLoc, 633★) — VLAD over DINOv2
  patches (mitigates DINOv2 CLS failure)

### P3 — DEM TERRAIN CONSTRAINTS (for R06 forest / R08 non-planar tail)
YFS90 paper (Yao et al. 2024, doi:10.1016/j.jag.2024.104277) — elevation
profiles discriminate texturally self-similar tiles. Download SRTM/Copernicus
30m DEM for R06/R08 regions, add a DEM-difference gate after NCC verify.
Non-visual signal, immune to textural aliasing.

### P4 — TILE FEATURE CACHE EXTENSION (latency)
Multi-feature matcher takes 4-20 sec/frame (re-extracts AKAZE+SIFT per tile
per frame). `TileFeatureCache` only stores ORB. Extend schema to store 3
descriptor blocks per tile → sub-second latencies. One-day infra work.

### P5 — EKF FUSION ACCURACY TEST (3rd-iter unresolved, now viable)
With yield doubled (26.7%), enough corrections exist to test EKF convergence.
Run `VioMapPipeline` for full 768-frame R03 trajectory with map_interval=5
and measure fused ATE vs GPS. The ESKF's Mahalanobis gate should absorb the
11% fatal tail (wrong corrections rejected by innovation consistency).

### P6 — HIGH-ELEVATION REGIONS (R05 mountain plateau, R11 desert)
Never tested with the corrected pipeline. Status genuinely unknown.

---

## 9. HOW TO RUN THINGS

### Run the E2E loop-closure test
```powershell
& "E:\kp_vio\kp_vio_py\.venv\Scripts\python.exe" -X utf8 `
    scripts/e2e_loop_closure_test.py `
    --region 04 --max-frames 20 --map-interval 1 `
    --multi-feature --ncc-verify 0.30 --search-radius 3
```

### Run the comprehensive multi-drift bench
```powershell
& "E:\kp_vio\kp_vio_py\.venv\Scripts\python.exe" -X utf8 `
    scripts/comprehensive_scene_test.py `
    --drifts 150,300,600 --n 40
```

### Run a single map-match (standalone)
```powershell
& "E:\kp_vio\kp_vio_py\.venv\Scripts\python.exe" -X utf8 `
    scripts/run_map_match_benchmark.py --region 03 --max 40
```

### Run VIO on EuRoC (indoor validation)
```powershell
& "E:\kp_vio\kp_vio_py\.venv\Scripts\python.exe" -X utf8 `
    scripts/run_euroc.py --seq V1_01_easy --mode vio
```

---

## 10. KEY DATA FILES (gitignored, on disk only)

| file | size | what |
|---|---|---|
| `datasets/uav_visloc/tiles.sqlite` | 117 MB | Satellite tiles at zoom 17 (5,234 tiles) |
| `datasets/uav_visloc/tile_features.sqlite` | 1.4 GB | Pre-extracted ORB features per tile |
| `datasets/uav_visloc/retrieval_index.npz` | 7.7 MB | DINOv2 descriptors for all tiles |
| `datasets/uav_visloc/cosplace_index.npz` | 10.8 MB | CosPlace descriptors (failed, kept for reference) |
| `datasets/uav_visloc/03/` | ~1.5 GB | 768 drone images + GPS CSV for region 03 |
| `datasets/uav_visloc/{01,04,06,08,09}/` | ~8 GB | Other regions |
| `.venv/` | 5.1 GB | Python venv with torch 2.2.2+cu121, kornia 0.8.2, cv2 4.13 |

---

## 11. REPORTING RULES (carry forward from 3rd/4th/5th iterations)

1. Report `fatal50 + cep90 + good_yield`, **never `cep50` alone**.
2. Never quote numbers measured with the prior set to ground truth (label as
   upper bounds if you do).
3. Never cross-quote between harnesses (graph_search_papers, comprehensive,
   method3/4, e2e_loop_closure — all use different drift realizations).
4. Treat monotone-to-the-edge sweeps as unfinished, not as results.
5. Require n ≥ 40 per region.
6. Verify negative results with single-frame probe diagnostics.
7. Multi-drift evaluation (150/300/600m) is mandatory for adoption claims.
8. E2E loop-closure tests must report first-frame match success — cascade
   failure is a deployment blocker, not a performance metric.

---

## 12. EXTERNAL REPOS EVALUATED

| repo | verdict | action |
|---|---|---|
| YFS90/GNSS-Denied-UAV-Geolocalization (82★) | README only, no code. DEM constraint idea transferable | Read paper for P3 (DEM gate) |
| sidharthmohannair/VisionUAV-Navigation (51★) | Vaporware (3 files, no src/). Claims hybrid SIFT+ORB+AKAZE+BRISK = your Method #3 | Nothing — your independent result already validates the approach |
| riotu-lab/gps_denied_navigation_sim (17★) | Linux-only (ROS2/Gazebo/PX4), won't run on Windows. Docker image exists but needs ROS bridge | Not viable on Windows; your E2E test is more realistic (real drone photos) |
| UAV-AVL/Benchmark (188★) | Real code. GIM/MINIMA modality-invariant matcher weights | **P2: try GIM as drop-in matcher replacement** |
| Skyy93/Sample4Geo (161★) | Real code, pretrained U1652 weights | P2: try as global retriever |
| TerboucheHacene/visual_localization (154★) | Real code, TMS tiles + SuperGlue, Finnish forest data | Reference architecture |
| AnyLoc/AnyLoc (633★) | Real code, VLAD over DINOv2 patches | P2: mitigates DINOv2 CLS failure |

---

## 13. UNTRIED METHODS STILL ON THE TABLE

From the 5th-iteration research inventory, not yet tested:

| # | method | effort | why it might help |
|---|---|---|---|
| 7 | Multi-resolution ORB pyramid | small | handles GSD mismatch hierarchically |
| 9 | Phase-correlation log-polar FFT | small | classical position recovery, no keypoints needed |
| 10 | AnyLoc-VLAD-DINOv2 | medium | VLAD aggregation of DINOv2 patches (vs failed CLS) |
| — | GIM/MINIMA matcher (from UAV-AVL) | small | modality-invariant LightGlue weights, no training |
| — | DEM terrain constraints (from YFS90 paper) | medium | non-visual signal, immune to textural aliasing |
| — | First-frame global bootstrapping | small | fixes cascade failure (P1 above) |

---

*End of handover. Read `summary/5th_iteration.md` for the full per-scene
multi-drift tables and the E2E loop-closure results.*