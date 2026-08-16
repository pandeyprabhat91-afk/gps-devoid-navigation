# Research Paper 1 — Strengthening C1: "Coherent-Offset Aliasing in UAV-vs-Satellite Geo-Localization"

**Created:** 2026-08-15
**Source plan:** 21st-iteration novelty audit, claim C1. Goal: turn C1 from
"narrowly novel" into a strong, publishable paper.

## The claim (C1, as graded in the 21st iteration)

Temporally-coherent, constant-offset aliases: on repetitive terrain, a
perceptually aliased map fix sits on the _correct tile_ but displaced by one
period of a repeating structure (furrows, canopy), the displacement is
_constant across frames_ (translates with the aircraft), the wrong lock is the
_appearance optimum_ (NCC selects k=0 on 16/16), and every consistency-based
rejection method discriminates _backwards_ (good-kept/fatal-kept ratio < 1 in
all 9 tested cells, 100% fatal survival at tol=100 m).

**Novelty threats:** Lajoie et al. RA-L 2019 (coherent outliers, indoor SLAM),
Vineyard SLAM 2026 trio (row-level aliasing, ground LiDAR). Both treat the
phenomenon as known; neither has: cross-view (UAV nadir ↔ satellite) domain,
appearance-optimality measurement, backwards-rate tables, sign-folding
methodology, or the whole-tile/sub-tile taxonomy.

## Evidence base (from iterations 1–21)

Core measurements to reproduce/extend at paper grade:

- **Finding T** (10th iter, Step 2): R04 sub-tile aliasing; sign-folded
  magnitude histograms hide bimodality. n=16 R04, n=14 R03 control.
- **Finding U** (10th iter, Step 3): sequential-consistency filter retains
  fatal fixes at a _higher_ rate than good fixes. n=55 pooled fixes.
- **Gate 2** (10th iter, Step 4.2): NCC selects k=0 on 16/16 R04 frames.
- **Gate 3** (10th iter, Step 4.3): robust back-end clique ratio 1.33–1.80×.
- **Gate 1** (10th iter, Step 4.1): sub-tile offsets exist; oracle 41.3 →
  12.7 m, 2.39× over null.
- **Finding V** (10th iter): tail unreachable by any in-pipeline signal.
- **Prior-ratio gate** (11th iter): whole-tile aliases separable; 7/7 fatal
  rejected, 14/14 good kept, 0 collateral.
- **Finding K** (7th iter): R06 bimodal (whole-tile aliases), R04 "continuous".
- **Findings P/Q/R** (8th iter): homography saturates ~15 inliers; error
  common-mode per frame, not constant offset; per-region oracle ceilings.

## The five actions

### Action 1 — Re-run T/U/V at paper-grade n

Re-measure Findings T, U and Gates 1–3 with n=40 per region (multiple drifts
where applicable), reporting denominators inline per project rules.
**Success:** T (hole at zero, 3.4× anisotropy), U (ratio < 1 in all cells),
Gates 1–3 reproduce at n=40 with same sign.

### Action 2 — Backwards-rate benchmark vs published rejectors

Run published rejection methods over the same fix pool: PCM-style pairwise
consistency (Kimera-RPGO), GNC-style graduated rejection, ORB-SLAM-style
3-consecutive-keyframe rule, margin gate, inlier-threshold family. Metric:
good-kept/fatal-kept ratio per method. **Success:** the _family_ fails
backwards, not just our gate — a rate table no published work reports.

### Action 3 — Temporal coherence curve

Direct measurement: alias displacement as function of frame lag; does the
alias track aircraft motion? Null control = shuffled frames. **Success:**
alias offset constant across lags (variance ≪ displacement), null destroys it.

### Action 4 — The countermeasure: multi-hypothesis filtering

(a) Estimate furrow period from tile FFT at drone-footprint native resolution
(sharper redo of measure_furrow_axis). (b) Represent map fixes as Gaussian
mixtures over k·p hypotheses along the dominant axis; run a multi-hypothesis
filter over the R04 fix stream; compare against baseline (30.9 m) and oracle
(12.7 m). **Success:** mixture filter recovers a material fraction of the
oracle gap that rejection cannot touch.

### Action 5 — Cross-domain replication

Run the T/U analysis on an independent repetitive-terrain source: Vineyard
SLAM dataset (if obtainable) or UAV-VisLoc held-out regions (R05, R11) as
partial replication. **Success:** backwards discrimination replicates outside
R04/R06.

## Reporting rules (inherited, project-wide)

- Report fatal50/CEP90/yield, never CEP50 alone; denominators inline.
- Never quote numbers measured with the prior = ground truth without labelling.
- Never cross-quote between harnesses; state harness per table.
- n ≥ 40 attempted per region for adoption claims; matched-frame denominators
  inline.
- Kill criteria stated before running; honoured.
- Monotone-to-the-edge sweeps are unfinished work, not results.
- Cross-validate any fitted correction (split-half).

## Deliverables

Each action gets `<NN>_action_<k>_<slug>.md` with: hypothesis, method,
kill criteria, exact commands, results tables, verdict, artifacts. Final
paper (if strong) at `paper.md` per the research-paper-writing skill.

## Status log

- 2026-08-15: folder created; plan written; harness exploration begun.
- 2026-08-15: Action 1 complete (T revised to per-field axes; U reproduced at
  3 drifts; Gate 2 unanimity at n=32; Gate 1 single-axis oracle degraded
  2.39→1.72×). See `01_action1_paper_grade_n.md`.
- 2026-08-15: Action 2 complete (backwards-rate tables for 4 published
  rejectors + prior-ratio in two forms; per-region taxonomy table).
  See `02_action2_rejector_benchmark.md`.
- 2026-08-15: Action 3 complete (alias offsets locally coherent, 2.55× below
  null at lag 1, decaying to ~1.1× at lag 5; correct fixes at null).
  See `03_action3_coherence_curve.md`.
- 2026-08-15: Action 4 complete — both countermeasure routes KILLED with
  mechanisms (tile periodicity absent; mixture blocked by gauge symmetry +
  per-field lattice). Finding V strengthened. See
  `04_action4_countermeasure.md`.
- 2026-08-15: Action 5 complete — replication not achievable on this dataset
  (R05 unsolvable-class 5% ceiling; R11 clean, 4% alias tail incoherent).
  External vineyard dataset = stated future work with ready protocol.
  See `05_action5_cross_domain.md`.
- 2026-08-15: Paper draft written (`06_paper_draft.md`) with five-dimension
  self-review and claim-evidence map. Result artifacts copied to
  `artifacts/`.
- 2026-08-15: External replication executed. TEMPO-VINE rejected on
  structure (ground-only imagery; `08b_TEMPO_VINE_recon.md`). AerialVL
  replication run (5.1 GB, 1,423 frames, two sequences): alias class
  ABSENT; 16.5 m constant georeferencing bias + truth-correlation guard
  fired (`08_replication_AerialVL.md`). Held-out R02/R10 probed:
  unsolvable-class (1/40, 0/40 usable GT-tile frames).
- 2026-08-15: Paper v2 (`06_paper_draft_v2.md`) + compilable LaTeX
  (`latex/paper.tex`, `latex/refs.bib`, 6 pages, MiKTeX-clean) with all
  review corrections: abstract overclaim fixed, 0/7 per drift, fatal
  thresholds defined, rich-grid oracle dropped (unartifacted), NGPS
  removed, AnyVisLoc 18.5% verified, replication section added. Figures
  generated from artifacts (`artifacts/figs/`, `make_paper_figs.py`).
- 2026-08-15: Action 6 complete — second-matcher replication (ORB-only,
  SIFT-only, SuperPoint+LightGlue: signature reproduces, rate structure
  matcher-stable, LightGlue rates underpowered at n=2 fatal), boundary map
  complete at 11/11 regions (R07 0/100, R09 12/100 ceiling), split-half
  internal replication. See `09_action6_second_matcher_boundary.md`.
- 2026-08-15: Paper v3 (`06_paper_draft_v3.md`): matcher-independence
  section added, exhaustive boundary table, constructive deployment
  section, limitations rewritten (single-matcher weakness closed;
  single-region weakness bounded with full-dataset boundary map).
- 2026-08-15: Forensic probe of ceiling class (`probe_regions_forensic.py`,
  `fx_sweep.py`, artifacts `forensic_probe.json`, `pairs/`): unsolvable
  regions fail on planar-homography geometry (corr→inlier conversion
  9–30% vs 39% control), not texture/scale/camera — Sec 4.5 v3 rewritten
  per-region. R07 = 30-frame flight; R09 partial tile coverage; R02/R07/
  R10 DEM grids built (raw-height AGL error 2.7–4.6×).
- 2026-08-16: Action 7 complete — the field's standard fixes measured
  (`gate_pnp_ceiling.py`, `gnc_and_smoother.py`, Sec 4.8 v3): PnP+DSM
  KILLED on ceiling class (correspondence-limited, solves fewer than
  homography everywhere); GNC KILLED (empty inlier set, 0–7% kept);
  robust smoother S4 KILLED with mechanism (trusted motion carries
  drift+aliases at 7 s spacing; synthetic-validated). DEM rebuilt for
  R05/R10 at 90 m. See `10_action7_field_standard_fixes.md`.
