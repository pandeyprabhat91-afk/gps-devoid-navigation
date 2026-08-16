# 22nd Iteration — newpapers Review → Executed Gates (Dense Matcher, Per-Terrain NCC, DEM Weighting, IME Pre-gate)

**Date:** 2026-08-16
**Plan:** `summary/22nd_iteration_plan_newpapers_gates.md`
**Constraint honoured:** existing datasets only (UAV-VisLoc tiles DB, forensic
probe artifacts); no new downloads. pdftoppm installed per user directive.

---

## Headline

| Gate | Question                                        | Result                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ---- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A0   | P1 RoMa probe valid?                            | **NO — H-direction bug found and fixed.** `probe_roma._recover_position` applied H⁻¹ (tile→drone) to a drone-space point. Same frame: through H → 4.3 m (matches forensic probe 3.5 m), through H⁻¹ → 893.8 m. All P1 RoMa position numbers void.                                                                                                                                                                                                                                                                                                 |
| A    | Dense matcher (RoMa) rescue ceiling/alias?      | **CLOSED with mechanism.** 0% A@50 across **167 frames, all 11 regions** (second run added R02/R05/R07/R10/R11; R11 = clean control where ORB holds A@25 27%, RoMa wrong 118–912 m on every frame), 1000+ inliers per frame. Fails via _dense-prior hallucination_: globally smooth, self-consistent, confident warp displaced 55–626 m (up to 11 km on R02); not periphery-dominance (centre-restricted fit 0% A@25; correspondences uniform) and not the appearance optimum (gradient NCC at dense lock never beats correct sparse lock, 0/20). |
| B1   | Per-terrain ncc_verify adoption (R09 0.30→0.10) | **KILLED under pre-registered criterion.** Match rate 2.5→7.5% confirmed, but the 2 extra solves include a fatal (91.1 m; fatal50 0→33.3%, yield 5.0%). Strict side is the safe side (21st side-finding holds). 0.30 stays production.                                                                                                                                                                                                                                                                                                            |
| B2   | DEM-variance fix weighting (Yao 2024 β)         | **CLOSED.** DEM elevation std (750 m window) does not predict match-rate ceiling: r = −0.21 over 8 regions (flat R03 1.9 m → 85%; flat R09 1.7 m → 15.4%). ASTER 30 m bare-earth cannot represent the built/canopy geometry that actually gates matching.                                                                                                                                                                                                                                                                                         |
| C    | IME-style moments pre-gate (Qiu 2025)           | **KILLED.** Hu moments AUC 0.52 (noise) on 310 forensic frames. Only matcher-internal signals predict solvability (log corr_orb AUC 0.89) — no pre-match gate can skip the 84% of frames that fail corr→inlier conversion.                                                                                                                                                                                                                                                                                                                        |

## Paper verdicts (from the 10 newpapers) — what transferred, what didn't

- **Bi, XIAN-Visloc (ISPRS 2026)** — the one that triggered Gate A: their
  RoMav2 15.07 m @ 95.24% (vs LightGlue 27.24 m @ 63.1%) does NOT transfer.
  Their reference imagery is contemporary Level-19 Google; UAV-VisLoc's
  drone↔satellite pairs carry a ~6-year vintage gap + cross-sensor modality.
  Dense matcher priors (trained on natural near-modal pairs) do not survive
  that regime. **Published dense-matcher numbers presume modal proximity —
  a literature-level caveat now measured, not assumed.** Dataset itself
  still deferred (existing-data rule).
- **Yao (JAG 2024)** terrain-weighted window — β weighting measured above
  (Gate B2): closed. Their "velocity-model coasting" re-localization matches
  the project's VIO-drift regime — consistent, not new.
- **Qiu (ESWA 2025)** IME frame selection — measured above (Gate C): closed.
  Their 83.99→22.33 m was on matched-modal self-collected data.
- **VecMapLocNet (ISPRS 2025)** — vector maps remain the only paper idea not
  yet measured; deferred (new modality/data). Strongest future direction for
  paper 2 / thesis chapter: texture-free reference, alias class cannot exist.
- NavCLIP, Cui, MuSe-Net, Fattah, Wang, Ye — related-work only.

## Paper v3 implications

1. **Matcher-independence section extends to dense matchers** — RoMa adds a
   THIRD failure mode beside alias-lock (R04/R06, sparse matchers) and
   correspondence starvation (ceiling class): smooth-warp hallucination.
   1000+ inliers, tight RMSE, 0% A@50 everywhere including control R03 where
   ORB holds 50% A@25. Reviewer-proof: "your signature is matcher-specific"
   is now answerable across sparse AND dense families.
2. **XIAN-Visloc Table 14 is citable as the modal-proximity contrast**: same
   pipeline class, contemporary imagery → dense wins; 6-year vintage → dense
   collapses. Supports the vintage-ablation framing (C6, farmland-scoped).
3. Gate B1 supplies the measured no-fix/wrong-fix boundary for per-terrain
   thresholds — the paper already makes this claim; now it has the R09
   adoption-benchmark table.

## Corrections to prior records

- `docs/P1_ROMA_PROBE_VERDICT.md` — errata appended (mechanism wrong,
  magnitudes inflated ~4× by H-direction bug; qualitative "RoMa does not
  recover position" survives).
- `scripts/probe_roma.py` — `_recover_position` fixed (H, not H⁻¹) with
  inline note.
- 21st-iteration "honest limit" — the dense-matcher arm ("not excluded") is
  now excluded on this data.

## Scripts and artifacts

| File                                                                                                                                        | Purpose                                                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `scripts/gate_roma_alias.py`                                                                                                                | Gate A: RoMa vs ORB pool on GT tile, translation field + NCC discriminators, corrected recovery |
| `scripts/gate_roma_center.py`                                                                                                               | Gate A2: centre-restricted H fit + gradient NCC                                                 |
| `scripts/verify_roma_recover_bug.py`                                                                                                        | A0: minimal H vs H⁻¹ verification (4.3 vs 893.8 m)                                              |
| `scripts/gate_ime_pregate.py`                                                                                                               | Gates B2 + C: DEM-variance diagnostic + moments AUC                                             |
| `comprehensive_scene_test.py`                                                                                                               | `--per-terrain-ncc` CLI + `region_id` plumbing (P4 config now benchmarkable)                    |
| `results/gate_roma_alias_fixed.json`, `results/gate_roma_center.json`, `results/gate_ime_dem_22.json`, `results/comprehensive/` (pt009 run) | artifacts                                                                                       |

## What remains genuinely open (unchanged except where noted)

1. Video-rate capture / continuous-sequence dataset (S2/S4 retest needs
   odometry the 7 s spacing cannot provide) — XIAN-Visloc download is the
   designated dataset when the user approves new data.
2. R03 ~13.9 m floor — GT audit / RTK (unchanged).
3. VecMapLocNet vector-map probe (new modality).
4. LaTeX sync + figures + adversarial review for paper v3.
5. R09 per-terrain relaxation closed; strict 0.30 remains production.

## Honest limits

- Gate A n = 10–20 per region, 167 frames total, all 11 regions (not 40):
  adoption-grade n was not the goal; the gates were discriminators, not
  production adoptions.
- RoMa = CVPR-2024 `roma_outdoor`, not XIAN-Visloc's RoMav2 (2025): the
  family argument holds (both dense, same objective class), but the specific
  model used by Bi et al. was not run — flagged, not hidden.
- RoMa inputs are anisotropically resized by the model API (aspect squeeze
  to 864×1152); standard usage, noted as a protocol caveat.
- Gate C labels come from forensic_probe.json's GT-tile protocol; a
  production-prior protocol could shift AUCs slightly.
