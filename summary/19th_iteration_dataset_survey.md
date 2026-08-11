# 19th Iteration — Dataset Survey: Outdoor UAV + IMU + Camera + RTK Ground Truth

**Date:** 2026-08-11
**Task:** extensive web search for a dataset matching the deployment
stack — outdoor drone flights with IMU + camera + ground truth — to get
REAL numbers for the VIO + map-matching system (the ArduPilot logs have
IMU+GPS but no camera; UAV-VisLoc has images+GPS but no IMU).

**Requirement match:** outdoor UAV · monocular camera (nadir) · IMU ·
RTK-grade ground truth · baro/mag · long flights (km) · ideally
satellite-reference compatible.

---

## The winner: ctu-mrs/coop_uav_dataset (secondary UAV)

**github.com/ctu-mrs/coop_uav_dataset** — Heterogeneous UAV dataset for
relative localization, IEEE Access 2026 (Pritzl et al., CTU Prague).

The **secondary UAV** (DJI F330) carries EXACTLY the deployment stack:

| Sensor | Spec | Rate |
|---|---|---|
| Monocular camera | mvBlueFOX-MLC200wG, fisheye DSL217 | 30 Hz |
| IMU | ICM-42688-P | **1000 Hz** |
| **RTK ground truth** | Emlid Reach, **cm-level** | 10 Hz |
| Pixhawk | IMU, mag, baro | 100 Hz |
| **VINS-Mono odometry included** | `/odom_vio` | 100 Hz |

Also included: camera-IMU **calibration in VINS-Mono format**, two
outdoor flights (circular 317 s, figure-eight 512 s), ROS bags
(1.0 + 1.6 GB for the secondary UAV), `download.sh` works.

**Why this is the best fit:**
1. **RTK ground truth (cm)** — 10× better than our Bhopal log's
   HDop-0.5 GPS and 100× better than UAV-VisLoc's ~10 m GPS. Real
   sub-metre validation is finally possible.
2. **Camera + IMU both present** — the full VIO stack, so the 18th
   iteration's vision-velocity simulation becomes REAL camera data.
3. **VINS-Mono odometry ships in the bag** — we can compare our fixed
   ESKF against the reference VINS-Mono output directly on the same
   data (the exact comparison the user has been asking for).
4. **Outdoor, 5-8 min flights** — long enough for drift measurement,
   short enough to process.
5. Baro + mag present → altitude + yaw fusion testable.

**Caveats:** fisheye (not nadir) camera → satellite matching must use
the primary UAV's LiDAR-VIO frame or be validated on the camera's
forward view; the flight is a small area (not km-scale corridors).

---

## Strong alternatives

| Dataset | Stack | GT | Verdict |
|---|---|---|---|
| **MUN-FRL** (arXiv 2310.08435, readthedocs `mun-frl-vil-dataset`) | monocular + IMU + LiDAR, DJI M600 + Bell 412 heli | **RTK-GNSS** | **300 m – 5 km flights**, 100 min, urban/highway/hillside/prairie/waterfront. Best for **long-range** VIO drift + the satellite-matching terrain range. Two global-shutter cameras. LiDAR-heavy but the monocular+IMU+RTK is there. |
| **Low Altitude UAV Dataset (IEEE Sensors J, 2024-11, Pin Lyu)** | stereo + IMU + laser rangefinder | **RTK** | Altitude 50-500 m (matches our flight envelope), calibrated & synchronized. Stereo (not mono). Paywalled; download channel unclear. |
| **ctu-mrs/mas_datasets** | IMU + LiDAR + RTK (Emlid Reach) | **RTK cm** | **No camera** ("connected to camera which was not recorded") — VIO half unusable. |
| **ALTO** (MetaSLAM, 2207.12317) | GPS-INS + accel + laser altimeter + **down-facing RGB** + reference imagery | high-precision GPS-INS | Down-view + reference imagery is the map-matching ideal, but **no IMU-camera pair for VIO**, full dataset still "coming soon" (only ICRA'22 GPR subsets live). |
| **UZH-FPV** (fpv.ifi.uzh.ch) | camera + IMU | motion-capture | Aggressive VIO stress test, but **indoor/outdoor with mocap, no GPS**, no satellite relevance. |
| **NTU VIRAL** | 2× cam + multi-IMU + LiDAR + UWB | | Sensor-rich but UWB-anchor based, not outdoor-satellite. |

---

## What we already have vs what these add

| Capability | Bhopal log (ours) | UAV-VisLoc (ours) | coop_uav_dataset |
|---|---|---|---|
| IMU | 25 Hz logged | ❌ | **1000 Hz** |
| Camera | ❌ | ✅ (drone images) | ✅ 30 Hz |
| Ground truth | HDop 0.5 (~1-2 m) | ~10 m GPS | **RTK cm** |
| Baro/Mag | ✅ | ❌ | ✅ |
| VIO reference | ❌ | ❌ | **VINS-Mono bagged** |
| Nadir for satellite matching | n/a | ✅ | fisheye (forward) |

**The coop_uav_dataset closes the one gap that has blocked real
validation since iteration 12: a camera + IMU pair with cm ground
truth.** The Bhopal log validated the estimator physics; this dataset
would validate the FULL VIO + map-matching loop with real numbers.

---

## Recommended next steps

1. **Download coop_uav_dataset secondary bags** (~2.6 GB, wget script
   works) — gives: ESKF-vs-VINS-Mono comparison on identical data,
   real-camera vision velocity, RTK-scored position error.
2. **MUN-FRL long sequences** — for the 1-5 km VIO drift + terrain
   diversity (the satellite-tile matchability probes from the 10th
   iteration can be re-run over its prairie/hillside areas).
3. The satellite-matching half still needs nadir imagery — combine:
   coop/MUN camera data for VIO, and the Indian tile downloader +
   UAV-VisLoc imagery for matching (or fly the X5 over IIT-M fields).

---

*Search method: GitHub API + DuckDuckGo HTML + arxiv abstract reads.
All links verified accessible 2026-08-11.*
