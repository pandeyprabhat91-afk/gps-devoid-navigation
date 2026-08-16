# 22nd Iteration — newpapers Review → Map-Matching Gates (Plan)

**Date:** 2026-08-16
**Trigger:** user added 10 papers (`newpapers/`), asked: can any resolve the map
matching problems? Constraint: plan then execute immediately; use EXISTING
datasets only (consistent benchmarking vs 10th/11th-iteration numbers); install
missing tools (pdftoppm done).

---

## Part 1 — Paper verdicts (all 10 read via pdftotext)

| #   | Paper                           | Core claim                                                                                                                                                        | Verdict vs open problems                                                                                                                                                                                                          |
| --- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | NavCLIP (Lin, IEEE Access 2026) | CLIP retrieval + homography + yaw                                                                                                                                 | Same architecture class as project; real flights show larger errors (corroborates). Related-work only.                                                                                                                            |
| 2   | VecMapLocNet (ISPRS 2025)       | UAV img ↔ VECTOR map, Fourier matching, 84.5% R@5m, 25 ms Jetson Orin                                                                                             | New reference modality — texture-free, alias class may not exist in vector space. HIGH novelty. **Deferred**: needs their nets + vector maps over our regions (new data).                                                         |
| 3   | Fattah (IEEE Access 2025)       | Autoencoder + HPO, RMSE 1.1 m sim                                                                                                                                 | Route-taught, tiny scale. Citation only.                                                                                                                                                                                          |
| 4   | Cui (Remote Sens. 2023)         | Transformer retrieval, Univ-1652 SOTA                                                                                                                             | Retrieval-level; project's retrieval isn't the bottleneck. No.                                                                                                                                                                    |
| 5   | MuSe-Net (PR 2024)              | Weather domain shift at retrieval                                                                                                                                 | Not current problem. No.                                                                                                                                                                                                          |
| 6   | Qiu (ESWA 2025)                 | Retrieval + match + PnP; SRA (resolution equalization) + IME (image-moment FRAME SELECTION), 83.99→22.33 m                                                        | IME = online frame-selection gate — project has none; ceiling regions waste 0.5–7.4 s/frame on no-fix frames. → **Gate C**                                                                                                        |
| 7   | Yao (JAG 2024)                  | VO + matching + sliding-window TERRAIN-WEIGHTED optimization (β from DEM elevation variance), MAE <7 m, no loop closure                                           | β = DEM-variance-driven fix weighting = principled online form of the project's per-region ncc thresholds + LOOP-3 adaptive covariance. → **Gate B**. Not an alias rejection family (assumes fixes are good).                     |
| 8   | Wang (CJA 2024)                 | vMF pose regression, forward-facing                                                                                                                               | Different regime. No.                                                                                                                                                                                                             |
| 9   | Ye (ISPRS 2024)                 | Oblique-view SuperPoint+DGPM + resection                                                                                                                          | Oblique ≠ nadir; sparse matcher (matcher-independence already proven). Citation only.                                                                                                                                             |
| 10  | Bi, XIAN-Visloc (ISPRS 2026)    | 81 km continuous dataset + coarse-to-fine UCVL. **Table 14: RoMav2 dense matching 15.07 m @ 95.24% vs SuperPoint+LightGlue 27.24 m @ 63.1%, LoFTR 28.30 @ 61.9%** | (a) Strongest external evidence dense matchers rescue position where sparse fails → tests project's last open arm (21st honest limit: dense matcher never installed/measured). (b) Dataset itself: DEFERRED (existing-data rule). |

**Net:** one executable lever per gate — A (Bi's RoMav2 result → re-open P1), B (Yao's β → per-terrain/DEM weighting), C (Qiu's IME → frame pre-gate). VecMapLocNet + XIAN-Visloc dataset = future work, gated on "specifically required".

---

## Gate A — Dense matcher alias forensics (RoMa, existing data)

### Background

`docs/P1_ROMA_PROBE_VERDICT.md` (2026-08-10) closed dense matchers as
"projection-model-limited": RoMa got 700–2000 inliers, RMSE 0.4–2.7 px,
yet 569 m (R03 control), 1079–1684 m (R01/R08/R09) position errors.
Mechanism claimed: no true homography exists between Mercator tile and
nadir photo; MAGSAC's H is periphery-dominated; centre projection inherits
the average of off-nadir distortion.

### Why re-open

The claimed mechanism is quantitatively impossible at the reported scale:
Mercator scale-factor variation across a 774 m (3×3, zoom-17) patch at
~30–40°N is ≈ 0.05% ⇒ **~0.4 m** distortion, not 569 m. The observed
signature — 100× inliers, tight RMSE, 40× position error on the CONTROL
region where ORB reaches 13.9 m — is exactly C4's "wrong lock is the
appearance optimum": a dense matcher maximises photometric consistency,
so on periodic farmland (furrows, field boundaries) its globally smooth
warp locks a phase-shifted, photometrically near-perfect solution.

### Hypothesis

RoMa's dense warp on R03/R04 locks photometrically-optimal ALIASES
(constant-offset, coherent), not a broken projection model. If true:
(a) P1's "projection-model-limited" verdict is refuted and must be
corrected in docs/memory; (b) the paper's alias class EXTENDS to dense
matchers — a strong v3 addendum (current matcher-independence covers
ORB/SIFT/LightGlue only).

### Measurements (per frame, GT-tile protocol identical to probe_roma)

1. RoMa position error (H-centre projection, probe's method — decode
   VERIFIED against romatch source: symmetric warp `[y,x<W]=(A_coords,
A_to_B)` in normalized coords; probe decode correct).
2. Implied-translation field over confident correspondences (cert>0.5):
   mean |t|, std |t|, direction — in tile metres. **Discriminator:** alias
   ⇒ coherent constant shift (std ≪ mean). Projection mismatch ⇒ small
   mean with radial/scale residual pattern.
3. NCC at RoMa-lock vs NCC at ORB-lock: warp tile into drone frame with
   each H, NCC vs drone. C4 test: does the wrong dense lock score HIGHER
   than the correct sparse lock?
4. Periodicity check: is the recovered offset a multiple of the dominant
   texture period (FFT of the tile patch, `measure_furrow_axis.py`)?

### Regions and n

- R03 control n=20, R04 alias n=20, R06 whole-tile-alias n=12,
  R01/R08/R09 ceiling n=15 each (matches P1 denominators).
- ~82 pairs ≈ 30–60 min on RTX 3060.

### Kill criteria (pre-registered)

- **Alias confirmed** if on R03/R04 the confident implied-translation
  field has std/mean < 0.5 AND NCC(RoMa lock) ≥ NCC(ORB lock) on ≥ 50%
  of frames where ORB is right and RoMa is wrong.
- **P1 vindicated** if implied translation is small (< 1 tile GSD × 10)
  with strong radial residual pattern while position still errs — then
  the centre-projection mechanism needs re-investigation (and we measure
  the Mercator term analytically in the doc either way).
- **Matcher rescue** if RoMa A@25m ≥ 50% on any ceiling region (re-opens
  the matcher-limited story for that region).

### Commands

```
E:\kp_vio\kp_vio_py\.venv\Scripts\python.exe -X utf8 -u scripts/gate_roma_alias.py --regions 03,04,06,01,08,09 --n 20,20,12,15,15,15 --device cuda
```

---

## Gate B — Per-terrain ncc_verify adoption + DEM-variance fix weighting

### Background

- 21st-iter P4 fix made `ncc_verify_per_terrain` real in `map_matcher.py`
  (`region_id` param); the adoption benchmark has NEVER run (documented
  since 5th iter). Measured: R09 match rate 2.5% @ ncc 0.30 → 7.5% @
  ncc ≤ 0.10.
- Yao 2024's β: weight fixes by DEM elevation variance — flat ⇒ trust
  odometry, relief ⇒ trust map fix. Principled online replacement for
  per-region tuned thresholds.

### Steps

1. **Per-terrain adoption (R09):** run production harness
   (`comprehensive_scene_test.py --select-by ncc`, n=40, drift 300 m,
   DEM on) with `ncc_verify_per_terrain={"09": 0.10}` vs baseline 0.30.
   Report match rate, median err, fatal rate. **Kill:** any fatal/wrong
   fix introduced at the relaxed threshold (21st side-finding: strict
   side is the safe side) ⇒ keep 0.30, close relaxation with mechanism.
2. **DEM-variance weighting:** use existing `dem_cache.json`/DEM grids:
   compute per-frame local elevation variance at the prior; map to
   adaptive covariance multiplier in the ESKF-style scoring (LOOP-3
   machinery), replacing flat NCC-only weighting. Validate on R05/R10
   (relief) + R03 control. **Kill:** if pooled p50 error not reduced vs
   flat weighting on the Bhopal-style replay or region benches.

### Commands

```
... python -u scripts/comprehensive_scene_test.py --regions 09 --n 40 --drift 300 --select-by ncc --dem --per-terrain-ncc "09:0.10"
... python -u scripts/gate_dem_weighting.py   # new, uses dem_cache.json
```

---

## Gate C — IME-style matchability pre-gate (frame selection)

### Background

Qiu 2025 selects frames whose projection has good
rotation/translation/scale behaviour (image moments) BEFORE matching.
Project runs the matcher on every frame; ceiling regions convert 9–30%
(corr→inlier) vs 39% control (forensic probe). A cheap pre-gate skips
unwinnable frames → latency win on X5, no-fix suppression.

### Steps

1. Fit: features = Hu moments of drone frame + tile-patch stats
   (edge/furrow/self-similarity, 12th-iter probe) + GSD ratio; label =
   inliers ≥ 10 given corr > 0, from `forensic_probe.json` (n≈270 frames,
   11 regions). Split-half validation.
2. **Kill:** test-half AUC < 0.7 ⇒ moments don't carry convertibility
   signal; close.
3. If pass: report gate at 95% recall of convertible frames; measure
   fraction of matcher time saved per region (bench_latency-style).

---

## Out of scope (explicitly deferred)

- XIAN-Visloc download (new data — only when specifically required)
- VecMapLocNet vector-map probe (new modality/data)
- LaTeX sync, figures, adversarial review (paper track, not map matching)
- ViLD replication (access-gated)

## Reporting rules (inherited)

Denominators inline; fatal50/CEP90/yield never CEP50 alone; kill criteria
honoured; harnesses not cross-quoted; n≥40 attempted for adoption claims.

## Deliverables

- `summary/22nd_iteration_*.md` (this plan + results)
- `scripts/gate_roma_alias.py`, `scripts/gate_dem_weighting.py`,
  `scripts/gate_ime_pregate.py`
- `results/gate_roma_alias_*.json`, `results/gate_dem_weighting_*.json`,
  `results/gate_ime_pregate_*.json`
- Corrections to `docs/P1_ROMA_PROBE_VERDICT.md` if Gate A refutes it
