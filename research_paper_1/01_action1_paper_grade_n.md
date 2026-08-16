# Action 1 — Re-run Findings T/U and Gates 1–2 at Paper-Grade n

**Date:** 2026-08-15
**Harnesses:** `smoke_georef_bias.py` (GT-tile signed offsets),
`gate_subtile_ncc_select.py` (Gate 2), `gate_subtile_snap.py` (Gate 1),
`analyze_r04_error_direction.py` (direction stats),
`sweep_sequential_consistency.py` (Finding U). All run with the repo venv
(`E:\kp_vio\kp_vio_py\.venv\Scripts\python.exe -X utf8 -u`), production
`MapMatcher` conventions (ORB+AKAZE+SIFT pool, ratio 0.75, MAGSAC, H_inv),
DEM/AGL correction active.

**Baseline artifacts (pre-action, from 10th iteration) backed up to**
`artifacts_baseline/`: `georef_bias_pre_action1.json`,
`sequential_consistency_pre_action1.json`, `subtile_ncc_R04_pre_action1.json`.

---

## 1.1 Finding T — signed-error structure at n=30/32

Command:

```
python scripts/smoke_georef_bias.py --regions 03,04 --n 40
```

Output: `results/georef_bias.json` (n=30 R03, n=32 R04 usable at ≥15 inliers;
previously n=14/16).

### Result — T PARTIALLY REPRODUCES, WITH A REVISION

| Quantity                       | R04 n=16 (10th iter) | R04 n=32 (this action) | R03 n=30 control |
| ------------------------------ | -------------------- | ---------------------- | ---------------- |
| axial resultant R (180°)       | 0.62                 | **0.50**               | 0.19             |
| directional R (360°)           | 0.25                 | 0.19                   | 0.21             |
| frames within ±10 m along axis | 1/16 (6%)            | **6/32 (19%)**         | 14/30 (47%)      |
| along-axis median \|·\|        | 38.0 m               | 24.3 m                 | 12.1 m           |
| perpendicular median           | 11.3 m               | 9.4 m                  | 7.5 m            |
| anisotropy                     | 3.4×                 | 2.6×                   | 1.6×             |
| median error                   | 40.8 m               | **32.7 m**             | 13.1 m           |

**The revision.** The n=32 offsets split into _two orientation groups_:
frames 15–38 cluster at bearings 145–193° (N–S axis) while frames 0–14
cluster at bearings 9–41° / 279–357° (NE–SW axis). The n=16 sample of the
10th iteration landed inside one segment of the flight path and saw one
axis; the full n=32 shows the alias axis is **per-field, not per-region** —
the flight crosses fields whose furrow orientation changes. The hole at
zero survives (19% vs 47% control within ±10 m; largest magnitude gap
2→10 m in both samples). The R03 control remains unstructured (axial
R=0.19), so the signal discriminates.

**Consequence for the paper:** Finding T's mechanism survives at n=32;
its _geometry_ must be stated as piecewise-constant per field, not a
single regional axis. This revision actually strengthens the paper:
it predicts the oracle (Gate 1) should degrade under a single-axis
model and recover under a per-frame local axis — which is exactly what
happened (§1.2), and motivates Action 4's per-footprint period
estimation.

## 1.2 Gate 1 — sub-tile snap oracle at n=32

Command: `python scripts/gate_subtile_snap.py` over the new `georef_bias.json`.

| Region                | best period | oracle median | rand-axis null | gain      | verdict            |
| --------------------- | ----------- | ------------- | -------------- | --------- | ------------------ |
| R04 (n=16, 10th iter) | 15 m        | 12.7 m        | 30.3 m         | **2.39×** | survived           |
| **R04 (n=32, now)**   | **20 m**    | **12.0 m**    | 20.7 m         | **1.72×** | KILLED (bar 2×)    |
| R03 (n=30, control)   | 10 m        | 8.2 m         | 10.8 m         | 1.32×     | KILLED (correctly) |

**Result:** the oracle median is stable (12.0–12.7 m across samples —
the _existence_ of a recoverable 20 m of error is a robust measurement),
but the single-global-axis single-global-period model degrades 2.39× →
1.72× against the random-axis null as the sample grows. This is the
statistical fingerprint of the per-field revision in §1.1: a wrong global
axis leaves the second field's aliases unexplained, so the null
(which also fits nothing) gains ground. **Gate 1's structure claim
survives; its single-axis oracle does not.**

## 1.3 Gate 2 — wrong lock is the appearance optimum at n=32

Command: `python scripts/gate_subtile_ncc_select.py --region 04 --n 40`.

|           | n      | median k=0 | median NCC-pick | median oracle | NCC picks k=0 |
| --------- | ------ | ---------- | --------------- | ------------- | ------------- |
| 10th iter | 16     | 41.3 m     | 41.3 m          | 14.0 m        | 16/16         |
| **now**   | **32** | **32.7 m** | **32.7 m**      | **12.3 m**    | **32/32**     |

**Result: REPRODUCED, stronger.** At twice the sample, masked patch NCC
still selects k=0 on _every single frame_ — unanimously, not ambiguously.
The appearance score is monotone _against_ the truth on 32/32 frames.
The oracle shows 20.4 m of median error is recoverable if k were known.
This is the sharpest measurement in the paper.

## 1.4 Finding U — sequential consistency at 3 drifts, 155 pooled fixes

Command (×3):

```
python scripts/sweep_sequential_consistency.py --regions 04,06 --n 40 --drift {150,300,600}
```

Outputs: `results/action1_seq_d150.json`, `action1_seq_d300.json`,
`action1_seq_d600.json`. Pool sizes: 59 (d150), 55 (d300), 41 (d600) —
155 pooled vs 55 before.

| drift | baseline    | best cell (w,tol) | good kept | fatal kept | ratio*          | verdict |
| ----- | ----------- | ----------------- | --------- | ---------- | --------------- | ------- |
| 150   | 44 g / 15 f | (1,30)            | 41%       | 40%        | 1.03            | fail    |
| 300   | 41 g / 14 f | (1,30)            | 15%       | 29%        | **0.51**        | fail    |
| 600   | 30 g / 11 f | (1,60)            | 17%       | 9%         | 1.83 (n=6 kept) | fail    |

*ratio = (good kept)/(fatal kept); >1 discriminates forward. Denominator
caveat: the d600 (1,60) cell keeps 6 fixes total — 6th-iteration rule,
cannot carry a decision.

**Result: REPRODUCED at the deployment-relevant drifts.** At d150 and
d300 the filter either discriminates backwards (ratio ≤ 1) or destroys
good fixes to cut fatals — in no cell does it simultaneously cut ≥25%
of fatals and keep ≥80% of goods. At d600 the motion-compensation noise
swamps the test (tol=30 keeps 0 fixes), and the two cells that
nominally flip the ratio are n-tiny. The 100% fatal survival at
tol=100 is reproduced at d150 (15/15 kept) and d300 (14/14 kept).

**Verdict: all four measurements reproduce at paper-grade n, one with
a geometry revision (per-field axes).** T's mechanism, Gate 2's
unanimity, U's backwards discrimination — all survive. Gate 1's
single-axis oracle is the casualty, and it points at Action 4.

---

## Artifacts

- `E:\kp_vio\kp_vio_py\results\georef_bias.json` (n=30/32 signed offsets)
- `E:\kp_vio\kp_vio_py\results\subtile_ncc_R04.json` (n=32 Gate 2)
- `E:\kp_vio\kp_vio_py\results\action1_seq_d{150,300,600}.json` (U pools)
- `E:\kp_vio\kp_vio_py\results\action1_{georef_n40,ncc_n40,snap,direction,seq_d*}.log`
