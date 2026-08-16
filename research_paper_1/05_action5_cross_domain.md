# Action 5 — Cross-Domain Replication: Held-Out Regions

**Date:** 2026-08-15
**Method:** UAV-VisLoc regions never used in the 6-region study — R05 (mountain
plateau, 1894–2331 m elevation) and R11 (desert, 1699–2497 m). DEM grids
built this session (spacing 500 m), tile DB confirmed to cover both. Same
production protocol (multi-feature + NCC 0.30 + DEM/AGL, drift 300 m, n=40)
plus contiguous GT-tile probes (coherence protocol).

## Result

### R05 mountain plateau — unsolvable-class confirmed

| Probe                       | Matched     |
| --------------------------- | ----------- |
| production, drift 300, n=40 | 1/40 (2.5%) |
| GT tile, contiguous, n=100  | 5/100 (5%)  |

Even against its own ground-truth tile with AGL correction, the mountain
plateau clears the inlier floor on 5% of frames — the same ceiling class as
R01 (10%) and R08 (7.5%). No alias structure is measurable because there is
nothing to measure: the scene produces almost no fixes.

### R11 desert — clean terrain, alias class absent

| Probe                             | Result                                                             |
| --------------------------------- | ------------------------------------------------------------------ |
| production, drift 300, n=40       | 34/40 matched, 33 good, **1 fatal**                                |
| GT tile, contiguous, n=199 solved | good=91, mid=100, **alias=8 (4%)**                                 |
| coherence, good group             | at null at every lag (0.85–1.25×) — independent errors, like R03   |
| coherence, mid group              | weakly structured (1.05–1.5× below null), no hole-at-zero evidence |

Desert is an R03-class scene: high match rate, ~15–20 m median, and a thin
alias tail (4%) with no measurable coherence. The sub-tile alias class does
not appear.

## Verdict

**Cross-domain replication is NOT achievable within this dataset.** The
coherent-offset alias class is specific to R04 (repetitive furrow farmland):
the only other repetitive-terrain region, R06 (forest canopy), exhibits the
whole-tile class (Action 2: fully separated by prior-ratio) rather than the
sub-tile class. R05/R11/R03 are negative controls — respectively unmatchable,
clean, and clean. Replication on independent repetitive-crop data (vineyard /
orchard datasets) requires an external dataset outside this project's scope;
this is now stated as the paper's primary limitation and as future work with
the exact protocol in **`07_replication_protocol.md`** (data requirements,
ingest adapter, 5 steps with exact commands, pre-registered kill criteria,
effort estimate, candidate datasets).

Note: an external-vineyard-dataset check was not performed this session
(network/data availability); the protocol in `07_replication_protocol.md`
makes it a mechanical follow-up.

## Artifacts

- `results/action5_coherence_R{05,11}.json`, `results/action5_dem.log`,
  `results/action5_collect.log`
- `datasets/uav_visloc/dem_cache.json` extended with R05/R11 grids
