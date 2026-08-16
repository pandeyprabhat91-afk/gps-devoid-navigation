# 07 — Cross-Domain Replication Protocol (vineyard / orchard / crop-field datasets)

**Purpose.** The single mechanical recipe for testing whether the
coherent-offset alias class (this folder's core claim) generalizes beyond
UAV-VisLoc R04. Follow this on any dataset with repetitive crop structure,
nadir drone imagery, a georeferenced map, and per-frame GPS truth.

**Status:** protocol defined; not yet executed (no external dataset obtained).

---

## 1. Data requirements (hard)

| Requirement                   | Minimum                                    | Why                                                                         |
| ----------------------------- | ------------------------------------------ | --------------------------------------------------------------------------- |
| Nadir/near-nadir drone images | ≥100 frames, contiguous flight order       | lag curve needs adjacent pairs                                              |
| Solved GT-tile matches        | ≥30 with ≥15 inliers                       | direction stats need denominators                                           |
| Alias frames (err ≥ 50 m)     | ≥10                                        | coherence curve needs pairs; <10 = "class absent", a valid but weak outcome |
| Per-frame GPS truth           | dataset-provided                           | all offsets are truth-referenced                                            |
| Repetitive structure in view  | furrows/rows/canopy                        | the mechanism is period-quantized locking                                   |
| Map tiles or orthophoto       | zoom-17 slippy tiles OR ortho at ≤1.5 m/px | matcher GSD matching                                                        |

## 2. Data ingest adapter (one-time, per dataset)

Scripts hardcode UAV-VisLoc layout. Adapt via a thin loader:

1. **CSV per region:** columns `filename`, `lat`, `lon`, `height` (absolute
   altitude, m). If no height, fix `alt` at the dataset's stated flight AGL.
2. **Images:** `<region>/drone/<filename>`.
3. **Tiles:** any source producing zoom-17 x/y tiles. Load into
   `tiles.sqlite` (`z, x, y, data`) with `build_tile_db.py` or an equivalent.
4. **DEM:** only needed if the region's ground elevation varies by >5% of
   flight altitude within a footprint. Flat farmland: skip (set `dem=None`).
5. **Constants to re-derive:** `CAMERA_K` (fx from image EXIF or
   `calibrate_fx.py`), `QUERY_SCALE`, `MIN_INLIERS` (keep 15), error-group
   boundaries (keep 20/50 m unless the dataset's noise floor differs).

## 3. The protocol (5 steps, in order)

### Step 1 — Signed GT-tile offsets

```
python scripts/coherence_curve.py --regions <r> --n 0 --lags 1,2,3,5,8
```

Produces per-frame signed (north, east) offsets vs the GT tile + the lag
curve. This is the master artifact; Steps 2–3 read from it.

### Step 2 — Direction structure (sign-folding diagnostic)

On the offsets from Step 1:

- **Hole at zero:** fraction of frames with |projection along dominant axis|
  < 10 m. **Replicates if < 20%** (R04: 19%; control R03: 47%).
- **Axial resultant** R(180°): **replicates if ≥ 0.4** and ≥ 2× the clean
  control region of the same dataset (R04: 0.50; R03: 0.19).
- **Anisotropy** (along-axis / perpendicular median): **replicates if ≥ 2×**
  (R04: 2.6×).
- **Per-field check:** if R(180°) < 0.4 but a 2-cluster bearing split exists
  (as at R04 n=32), record the cluster bearings — the class is per-field,
  not per-region. This is still a replicate.

### Step 3 — Coherence curve (the mechanism)

From Step 1's lag table, alias group (err ≥ 50 m):

- **Replicates if** alias median/nulled-median ≤ 0.7 at lag 1 (R04: 2.55×
  below null) AND the advantage decays toward ~1.0× by lag 5–8.
- **Control must hold:** good group (err < 20 m) within 0.8–1.25× of its
  null at every lag (independence). If the good group is also coherent, the
  dataset's truth itself is temporally correlated — report and stop.
- If the alias group sits at its null (≥ 0.9×): the class is absent; the
  dataset is a clean-terrain control.

### Step 4 — Backwards-rate table (the rate claim)

```
python scripts/bench_rejectors.py --collect --drift 300 --regions <alias_region,control> --n 40 --out results/rp_pool_d300.json
python scripts/bench_rejectors.py --analyze --pools d300
```

**Replicates if**, on the alias region's sub-tile fatal fixes: sequential
consistency and 3-consecutive ratio ≤ 1.0 at tol=100 (backwards), and the
prior-ratio gate (oracle uncertainty) ratio ≥ 1.5 — i.e., the whole-tile
class is separable and the sub-tile class is not. Report denominators
inline; cells with <10 kept fixes cannot carry a decision.

### Step 5 (optional, matcher-specific) — appearance optimality

```
python scripts/gate_subtile_ncc_select.py --region <r> --n 40 --axis-deg <from Step 2> --period <from Step 2 or 15-25 m>
```

Replicates if NCC selects k=0 on ≥ 90% of frames while the oracle k recovers
≥ 10 m of median error.

## 4. Kill criteria (pre-registered, do not move them after running)

| Measurement                     | Kill (class absent)                               | Replicate (class present) |
| ------------------------------- | ------------------------------------------------- | ------------------------- |
| Hole at zero                    | > 40%                                             | < 20%                     |
| Axial R vs control              | < 1.5×                                            | ≥ 2×                      |
| Lag-1 alias coherence           | ≥ 0.9× of null                                    | ≤ 0.7× of null            |
| Good-group lag-1                | coherent (< 0.8×) → dataset invalid for this test | 0.8–1.25×                 |
| Seq-consistency ratio (tol=100) | > 1.2                                             | ≤ 1.0                     |
| Prior-ratio oracle ratio        | < 1.2                                             | ≥ 1.5                     |

## 5. Effort estimate

- Ingest adapter: half a day (tile download dominates).
- Step 1: ~4 s/frame × n (n=200 ≈ 15 min; n=600 ≈ 40 min).
- Step 4: ~4 s/frame × 80 (two regions, n=40) ≈ 5 min + analysis.
- Total: 1–2 days per dataset including debugging.

## 6. Candidate datasets (to check, in order)

1. Vineyard SLAM 2026 trio — if their row-aliasing data (ground LiDAR or
   drone) is public; note: ground-level imagery changes the cross-view
   premise, prefer aerial.
2. Crop-field VPR/geo-localization sets: check UAVD4L (has farmland scenes
   - better GPS), University-1652 (drone-view, satellite refs).
3. Any ArduPilot-logged farmland flight with camera (like the project's
   Bhopal corridor: tiles on disk, camera absent — unusable until imagery
   exists).
4. Self-collected flight over Indian farmland (R04-class terrain predicted
   by the 12th-iteration matchability probe).

## 7. Reporting

Write `08_replication_<dataset>.md` with: dataset provenance, ingest
decisions (K, alt, DEM), each step's table with denominators, verdict per
kill criteria, artifacts. Update the paper's Limitations (Sec. 5) and the
claim-evidence map.
