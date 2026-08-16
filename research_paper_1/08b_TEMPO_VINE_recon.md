# 08b — TEMPO-VINE Reconstruction (documented attempted replication)

**Date:** 2026-08-15
**Status:** Rejected before download — fails replication-protocol requirement #1
(`07_replication_protocol.md` §1): _nadir/near-nadir aerial imagery_. The paper's
own sensor specification makes this disqualification verifiable from the text.

## The finding

TEMPO-VINE (arXiv 2512.04772) is a **ground-robot** dataset, not an aerial one.
Its platform and sensor config are documented in the paper (§II-A, §III):

- **Platform:** ClearPath Husky ground rover (a wheeled UGV), not a UAV.
- **Camera:** Intel RealSense D435 RGB-D, **forward-oblique** 640×480. Mounted
  at **~1 m** height, facing the horizon — the opposite of nadir down-looking
  aerial capture.
- **Ground truth:** RTK-GPS (Swift Duro, 5 Hz), georeferenced lat/lon/alt per
  frame.
- **Location:** Agliè, Italy.
- **Access:** email-gated (`pic4ser.polito@gmail.com`); GitHub repository not
  live.

## Why it fails the protocol

The replication protocol's target is a coherent-offset alias class in
_repetitive crop structure_ imaged from a **nadir** aerial viewpoint against a
georeferenced map. Two requirements are violated:

1. **Viewpoint** — oblique RGB-D at ~1 m height is ground-level, not
   nadir/near-nadir aerial. The cross-view geometry, footprint, and occlusion
   regime are unrelated to the R04 (drone-over-furrows) claim under test.
2. **Repetitive-structure premise** — a forward-oblique vineyard view from
   wheel height presents rows as converging perspective, not as the
   period-quantized top-down pattern the alias mechanism depends on.

Ground truth _is_ per-frame GPS (satisfies one requirement), but that alone is
insufficient.

## Sources

- Sensor spec: `https://arxiv.org/html/2512.04772v2` §II-A (RealSense D435,
  640×480, oblique), §III (platform: ClearPath Husky).
- Data format: §IV-B; ground-truth format: §IV-C (georeferenced lat/lon/alt).
- Access: §(data availability) — email-gated `pic4ser.polito@gmail.com`; repo
  not live.

## Verdict

TEMPO-VINE is recorded as an **attempted but rejected** external replication
target: it is ground-robot imagery and cannot test the aerial coherent-offset
claim. It is cited in the paper's Limitations only as a documented
_negative-provenance_ entry (checked, not run), alongside the AerialVL attempt
(`08_replication_AerialVL.md`).
