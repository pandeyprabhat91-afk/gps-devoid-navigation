# 16th Iteration — The RDK X5 BPU: What It Is, What Should Run On It

**Date:** 2026-08-11
**Context:** the user asked: "we have not used the BPU on the X5?" —
correct. After 16 iterations there is **zero BPU usage**. This document
states what the BPU is, what belongs on it, what does not, and the
concrete first deployment.

---

## What the BPU is (hardware fact)

The RDK X5's BPU (Horizon Robotics "Bernoulli" class) is a **neural
network inference accelerator**: it runs **quantised (INT8) CNN/transformer
inference** compiled with Horizon's `hbdk`/`onnxruntime` toolchain. It
does NOT run:
- classical OpenCV (ORB/AKAZE/SIFT, homography, CLAHE) — CPU (A55)
- the EKF/ESKF math — CPU (tiny, and needs float precision)
- MAVLink, tile I/O, logging — CPU

So the question is not "should we use the BPU" but **"which learned
model in the pipeline, if any, is worth deploying"**.

---

## What the pipeline has that could use the BPU

| Component | Where | BPU candidate? | Worth it? |
|---|---|---|---|
| ORB/AKAZE/SIFT matching | sat_matcher, map_matcher | No (classical) | CPU stays |
| DINOv2 global retrieval | retrieval.py | Yes (ViT-S, 21M params) | **Weak: 5.4% match rate measured (5th iter)** — BPU won't fix a bad signal |
| SuperPoint+LightGlue | learned matcher | Yes | **Weak: ground-trained, domain gap killed it; also RoMa/DKM ranked above** |
| YOLO building detection | OSM matcher `BuildingDetector` ABC | **Yes — designed for exactly this** | **The right first BPU target** |
| Semantic segmentation (water/vegetation/built) | semantic_matcher.py | Yes (lightweight encoder) | Second candidate — targets R01 (water), R08/R09 (built) |
| learned abstraction net | abstraction_net.py | Yes | Not validated; skip |

---

## The honest BPU assessment

**1. The OSM structural matcher is the best BPU fit — and it is the
only component that sidesteps the projection-mismatch that killed every
other matcher.**

The OSM matcher (P3, committed) matches a **numeric pose** (compass+AGL
locked) to a **geographic reference** (OSM building corners), so the only
projection is the pinhole camera — exact. Its weak link is the drone-side
building detector: `ContourBuildingDetector` (classical OpenCV) fails on
texture-rich/complex scenes. A YOLO detector on the BPU is the designed
upgrade (the ABC comment says exactly this).

**Expected value:** OSM building detection directly targets the
project's worst regions (R08 suburban, R09 mixed — 5% and 10% match).
It does NOT compete with the satellite ORB matcher — it is a second,
orthogonal signal that only helps.

**2. DINOv2/SuperPoint on BPU would be a deployment of a dead signal.**

The 5th iteration measured DINOv2 retrieval at 5.4% match and LightGlue
at ground-trained domain-gap failure. Putting them on the BPU makes a
failed algorithm faster, not better. Do not.

**3. The EKF/ORB/homography stays on CPU by design.**

---

## The concrete first BPU deployment (recommended)

**Target: YOLOv8n-seg (or YOLOv8n-detect) → INT8 → BPU, feeding the OSM
matcher's `BuildingDetector`.**

Steps:
1. Train/fine-tune YOLOv8n on nadir drone building detection (the
   dataset has UAV-VisLoc nadir frames; OSM gives free labels for R08's
   buildings via the tile DB).
2. Export to ONNX, compile with Horizon RDK X5 toolchain (hbdk) to
   INT8 `.bin`.
3. Implement `YoloBpuBuildingDetector(BuildingDetector)` calling the BPU
   runtime (`dnn`/`hbrt` on the X5).
4. Benchmark: detection latency, and the OSM matcher's match rate on
   R08/R09 vs the contour detector.

**Feasibility check on X5:** YOLOv8n is ~3.2M params, ~8.7 GMACs; the
X5 BPU is rated ~10-30 TOPS INT8, so a 640×640 nadir frame is
single-digit milliseconds — negligible next to the 0.5-2 s/frame
matching budget. This is well within the board's capability.

---

## Honest limits of this plan

- No X5 hardware on this machine — the deployment itself (toolchain
  install, INT8 compile, runtime bring-up) cannot be done here. What is
  done here: the code hook (`BuildingDetector` ABC), the model choice,
  and the evaluation protocol.
- The OSM matcher needs OSM data for the operating area (available for
  India via the OSM API — Rajasthan/Punjab/MP all have building data).
- R08/R09's low match is partly imagery staleness, not only detection
  — YOLO-BPU raises the ceiling but does not remove it.

---

## Decision

- **BPU use #1: YOLO building detection → OSM matcher.** Orthogonal
  signal, targets the worst regions, fits the ABC, hardware-feasible.
- **BPU use #2 (later): lightweight semantic segmentation** for the
  semantic matcher (water/vegetation) — only after #1 is proven.
- **Do NOT deploy DINOv2/SuperPoint/LightGlue on the BPU** — dead
  signals, and the RDK X5 BPU is the one compute resource that should
  not be wasted on them.

*This is analysis and a plan; the BPU itself is not on this machine.
The `BuildingDetector` ABC already exists at
`kp_vio_py/kp_vio/map_matching/osm_matcher.py:68`.*
