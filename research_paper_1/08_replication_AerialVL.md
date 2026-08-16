# 08 — Cross-Domain Replication: AerialVL (hmf21/AerialVL)

**Date:** 2026-08-15
**Method:** External-dataset replication of the coherent-offset alias class per
`07_replication_protocol.md`. Target: AerialVL (HuggingFace `hmf21/AerialVL`,
claimed MIT / actual **cc-by-4.0**; card has no paper, README is license-only).
Downloaded two flight sequences by ranged-HTTP extraction from the dataset's
monolithic split ZIP64 archives, ingested per-frame GPS (altitude absent →
empirical GSD), built the reference tile DB from the dataset's own georeferenced
ortho, and ran protocol Steps 1–3 on both sequences (Step 4 needs a deployed
MapMatcher + retrieval index; not run — see §7).

---

## 1. Recon (what the dataset actually is)

`hmf21/AerialVL` stores everything in three monolithic split archives, not
per-sequence files:

| Archive                          | Parts       | Compressed | Contents                |
| -------------------------------- | ----------- | ---------- | ----------------------- |
| `images/VAL/VAL.zip`             | 27 × ~2 GiB | ~54 GB     | validation split        |
| `images/VPR/VPR.zip`             | 36 × ~2 GiB | ~71 GB     | place-recognition split |
| `vpr_training_data/images_2.zip` | 6 × ~2 GiB  | ~11 GB     | training split          |

Total repo `usedStorage` = 145.7 GB. `README.md` is 30 bytes (license line only);
`cardData.license = cc-by-4.0` (the task's "MIT" claim is wrong). `gated=false`.

Internal structure (recovered by parsing the ZIP64 central directory of
`VAL.zip.027` — 15,152 entries, no download of the 54 GB archive):

```
geo_referenced_map/
  @large_map@<lon0>@<lat0>@<lon1>@<lat1>@.tif   5888×3584  0.959 m/px
  @small_map@<lon0>@<lat0>@<lon1>@<lat1>@.tif   3328×2048  0.959 m/px
long_trajtr/<date-time>/@<utc_ms>@<lon>@<lat>@.png    5 seqs, 10,487 frames
short_trajtr/<date-time>/@<utc_ms>@<lon>@<lat>@.png   6 seqs,  4,662 frames
```

11 sequences total (matches the task's "11 sequences"). Per-frame longitude and
latitude are in the filename (`@1678957367781@120.44068666666666@36.599158333333335@.png`);
**no altitude** anywhere. Coordinates ~120.44°E / 36.60°N = Qingdao, China.
The task's "He et al. IEEE RA-L 2024" attribution and "NovAtel OEM718D" spec are
**unverified** — arxiv full-text search for `AerialVL` returns 0 results.

There is no per-sequence download path and no `allow_patterns` hook: images are
_inside_ split ZIP64 archives, so the only repo files are `.zip.00X` parts. A
single sequence cannot be obtained without the whole 54 GB archive — except by
ranged-HTTP extraction, which this run did (§2).

## 2. Download (ranged ZIP64 extraction)

A `HTTPConcatFile` (seekable file object over the 27 concatenated parts, chunk
cache) feeds Python `zipfile`, which handles the ZIP64 extra fields (CD offset
57.77 GB, 15,152 entries). Selected the two smallest sequences:

| Sequence                           | Frames    | Size        |
| ---------------------------------- | --------- | ----------- |
| `short_trajtr/2023-03-11-11-48-35` | 922       | 3.32 GB     |
| `short_trajtr/2023-03-16-16-58-43` | 501       | 2.00 GB     |
| **total**                          | **1,423** | **5.32 GB** |

Plus both map GeoTIFFs. On disk 5.09 GB (within the 15 GB cap).

## 3. Ingest (CSV schema)

`E:\kp_vio\dataset\AerialVL\<seq>\manifest.csv`:

```
filename,timestamp_ms,lon,lat
@1678957367781@120.44068666666666@36.599158333333335@.png,1678957367781,120.44068666666666,36.599158333333335
```

Protocol §2 wants `filename,lat,lon,height`. **Height is unavailable** (not in
filename, no README, no paper). Substituted an empirically measured GSD (§4);
images at `<seq>/drone/<filename>.png` (1,423 files, 1536×2048 RGB, no EXIF).

## 4. Camera / GSD

No intrinsics or altitude in the dataset. Steps 1–3 only use the ratio
`(alt/fx)/tile_gds` = query-GSD ÷ map-GSD, so absolute values are immaterial.
Query GSD measured empirically:

- **Consecutive-frame homographies** (drone↔drone, ~5 m baseline): 90%+ inlier
  rate (992–1982 of ~1,000–2,000 correspondences), near-identity transforms
  (`h20 ≈ h21 ≈ 0`, scale 0.98–1.014) → imagery is **nadir** and self-consistent.
- **Query GSD** = frame displacement ÷ ground displacement: **median 0.115 m/px**
  (p25 0.092, p75 0.139) over 200 pairs.

Map GSD = 0.959 m/px (GeoTIFF `ModelPixelScaleTag`, matches filename bbox ÷
pixel count). Query→map scale ≈ 0.12.

## 5. Reference map

Both sources prepared (protocol §1 "map tiles or orthophoto ≤1.5 m/px"):

1. **Dataset ortho** — `large_map` GeoTIFF sliced to slippy tiles at zoom 17
   (78 tiles) and zoom 19 (5,301 tiles) into `tiles.sqlite`. Georeferencing
   verified: `ModelTiepoint (0,0) = (120.42114, 36.60450)` NW corner,
   `ModelPixelScale = 0.959 m/px`, EPSG:4326, no `ModelTransformation`
   (north-up, no rotation).
2. **Esri World Imagery** — 192 tiles at zoom 18 into `tiles_esri.sqlite`.

Matching quality was strongly zoom-dependent: at zoom 17 the pooled matcher
returned 9–76 correspondences (too coarse), at zoom 19 it returned 93–271 with
usable inliers. Zoom 19 + patch radius 2 (query footprint 236 m fits inside a
307 m patch) was adopted for the protocol run.

## 6. Result

### Sequence 03-11 — clean terrain + a common-mode georeferencing bias

| Step | Metric                      | Value                                              |
| ---- | --------------------------- | -------------------------------------------------- |
| 1    | solved frames (≥15 inliers) | **94 / 200 (47%)**                                 |
| 2    | hole at zero                | **5.3%**                                           |
| 2    | axial resultant R(180°)     | **0.70**                                           |
| 2    | anisotropy (along / perp)   | **9.7×** (16.3 m / 1.7 m)                          |
| 2    | median error                | 17.1 m                                             |
| —    | median offset vector        | **(-16.0 N, +4.1 E) = 16.5 m**                     |
| —    | spread about that offset    | 3.1 m                                              |
| —    | split-half CV (bias fit)    | **17.3 m → 3.3 m (+14 m)**                         |
| 3    | good-group lag-1 coherence  | **2.2 / 3.7 = 0.59×** (constant to lag 8: 2.8/3.7) |
| 3    | error groups                | good 75, mid 15, **alias 4**                       |

### Sequence 03-16 — unsolvable-class

| Metric        | Value            |
| ------------- | ---------------- |
| solved frames | **0 / 200 (0%)** |

The two sequences are opposites: 03-11 localizes cleanly at 47%, 03-16 never
clears 15 inliers (the R01/R08 unsolvable class).

_Caveat on the bias source:_ the ortho's own geotags are internally consistent
(tiepoint = NW corner, pixel scale = 0.959 m/px, no rotation), and the offset is
constant across ~1 km of flight (spread 3.1 m) — a translation, not a scale
error, so it is the map's registration versus the drone GPS datum, not a
tile-slicing artifact. The absolute magnitude (~16.5 m) is the same order as the
project's own R03/R04 common-mode finding (23.5 m), which is expected for
ortho↔RTK-GPS registration at this GSD.

## 7. Kill criteria (pre-registered in the protocol)

| Measurement              | Replicate if                 | Observed                                  | Verdict                                                   |
| ------------------------ | ---------------------------- | ----------------------------------------- | --------------------------------------------------------- |
| Hole at zero             | < 20%                        | 5.3%                                      | _would_ pass — but bias-driven, not alias (§8)            |
| Axial R vs control       | ≥ 2× control                 | 0.70, no clean control (03-16 unsolvable) | n/a                                                       |
| Lag-1 alias coherence    | ≤ 0.7× null                  | alias group = 4 frames, 0–1 pairs         | class absent                                              |
| **Good-group lag-1**     | **0.8–1.25× (else invalid)** | **0.59× (coherent)**                      | **dataset truth temporally correlated → report and stop** |
| Seq-consistency ratio    | ≤ 1.0                        | not run (Step 4)                          | —                                                         |
| Prior-ratio oracle ratio | ≥ 1.5                        | not run (Step 4)                          | —                                                         |

Step 4 (`bench_rejectors.py`) was not run: it requires the deployed
`MapMatcher` with a DINOv2 retrieval index built over the AerialVL tiles, and it
measures the alias-class _rate_ — meaningless once the good group is coherent
bias and the alias group is 4 frames.

## Verdict

**The coherent-offset alias class is absent in AerialVL.** The class that _is_
present is a different, already-understood phenomenon: a **~16.5 m common-mode
georeferencing offset** between the dataset's reference ortho and the drone GPS
truth (median (-16.0 N, +4.1 E), spread 3.1 m, cross-validated 14 m correction).
This is exactly what `smoke_georef_bias.py` measures, and it explains the
sign-folding "replicate" signatures (hole 5.3%, R(180°) 0.70, anisotropy 9.7×)
without any sub-tile alias: a constant offset vector is perfectly axial and
perfectly temporally coherent.

The protocol's own control guard fires: the **good group is coherent (0.59× of
null at lag 1), so the dataset's truth is temporally correlated — report and
stop.** The alias tail is 4 frames (4.3%), too thin to carry a coherence
measurement, so the class is recorded **absent**, with AerialVL functioning as a
clean-terrain control plus a georeferencing-bias case study.

Provenance notes for the paper: the task's dataset description is wrong in three
places — license is **cc-by-4.0** (not MIT), the README/paper link is empty, and
the "He et al. RA-L 2024 / NovAtel OEM718D" attribution could not be confirmed.

## Artifacts

All new; no primary-study artifacts (R03/R04/R06 results, `datasets/uav_visloc/*`)
touched or overwritten.

- `E:\kp_vio\dataset\AerialVL\short_trajtr_2023-03-11-11-48-35\` — 922 frames + `manifest.csv`
- `E:\kp_vio\dataset\AerialVL\short_trajtr_2023-03-16-16-58-43\` — 501 frames + `manifest.csv`
- `E:\kp_vio\dataset\AerialVL\geo_referenced_map__*.tif` — large_map + small_map orthos
- `E:\kp_vio\dataset\AerialVL\tiles.sqlite` — z17 (78) + z19 (5,301) tiles from large_map
- `E:\kp_vio\dataset\AerialVL\tiles_esri.sqlite` — Esri World Imagery, z18 (192 tiles)
- `E:\kp_vio\kp_vio_py\scripts\repl_aerialvl_run.py` — Steps 1–3 runner (copy-adapted; no originals edited)
- `E:\kp_vio\kp_vio_py\scripts\repl_aerialvl_probe.py` — GT-tile matcher / scale / NCC diagnostics
- `E:\kp_vio\kp_vio_py\results\repl_aerialvl.json` — per-frame signed offsets + sign-folding + lag curve
- `C:\Users\lonew\AppData\Local\Temp\opencode\aerialvl_{peek,analyze,extract,download,scalesweep,esri_probe,ncc_check}.py` — recon/extraction tools
