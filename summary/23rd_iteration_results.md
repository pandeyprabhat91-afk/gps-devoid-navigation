# 23rd Iteration — Fix Propagation, Retrieval Floor, Fine-Tuned Matcher: Results

**Date:** 2026-08-16
**Plan:** `summary/23rd_iteration_plan.md`
**Assumption (user):** GPS available at flight start → initial fix always
available. Autonomous execution, gates A → D → B, kill criteria honoured.

---

## Headline

| Gate | Question                                                                       | Result                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ---- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A    | Does one good fix carry forward (KLT + PnP, satellite re-match on track loss)? | **KILLED at 7 s spacing.** Only 8/120 propagated frames (1 R03, 7 R04, 0 R06); track survival ≥20 across a 7 s gap is rare. When chains survive, PnP drifts: R03 p50(prop) 151 m vs 13.9 m rematch baseline. Mechanism: coarse temporal spacing + planar-z=0 map points + alias-contaminated seeds (R04). Concept unmeasurable on this dataset — video-rate data-gated, NOT design-refuted.                                                            |
| D    | Does DINOv2 retrieval give a coarse fix everywhere (fallback floor)?           | **KILLED.** GT tile ranks 53–1556 of 5234 on R03 control. Top-5 oracle p50 per region: 250 m (R06) – 950 km (R10); R03 itself 1774 m. DINOv2-zero-shot has no discriminating power on cross-season farmland/built imagery. Floor concept survives only with a TRAINED retrieval model.                                                                                                                                                                 |
| B    | Does fine-tuning SuperPoint on own cross-modal pairs lift R09?                 | **KILLED with mechanism.** Homographic adaptation degenerates: stock CE floor 0.058, 90.5% label self-consistency — the pretrained detector is already converged for this task; no training signal. Stock SP+LightGlue solves 0/8 R03 held-out (where ORB pool solves) and 1/14 R09: the bottleneck is the LightGlue MATCHER's cross-modal domain gap, not the detector. Right target = correspondence-supervised matcher fine-tune (multi-day build). |

## What this closes and opens

- **Closed:** fix propagation at coarse rate; zero-shot retrieval floor;
  detector fine-tune as a shortcut.
- **Still open, now precisely data-gated:** (1) video-rate imagery — the
  ONLY blocker for propagation + tight-prior matching (S2 direction); the
  user's "GPS at start" assumption makes propagation the highest-value
  next move once video-rate data exists. (2) Matcher fine-tune with GT
  correspondence supervision (LightGlue or LoFTR head) — right design
  identified, build not started. (3) Trained retrieval model (GeoCLIP/
  CAMP-class) — needed for any coarse-floor fallback.
- **XIAN-Visloc** (ISPRS 2026, 81 km, ~1 Hz nadir, public) is the natural
  video-rate surrogate if the user approves a new download — it would
  un-gate A and give the smoother/odometry regime its missing half.

## Scripts and artifacts

| File                                                                                                                      | Purpose                                                        |
| ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `scripts/gate_fix_propagation.py`                                                                                         | Gate A: KLT chain + EPnP propagation with re-match triggers    |
| `scripts/gate_retrieval_floor.py`                                                                                         | Gate D: DINOv2 top-k per-region error tables                   |
| `scripts/gate_finetune_sp.py`                                                                                             | Gate B: homographic adaptation fine-tune + stock-vs-tuned eval |
| `results/gate_fix_propagation.json`, `gate_retrieval_floor.json`, `gate_finetune_sp.json`, `superpoint_finetuned_r03.pth` | artifacts                                                      |

## Honest limits

- Gate A rematch path used the GT-tile protocol (no drift injection):
  R06 GT-tile solves are rarer than production drift-300 numbers — noted,
  does not change the propagation verdict.
- Gate D used the existing 5th-iteration DINOv2 index (5234 tiles); a
  stronger retrieval model was not trained.
- Gate B trained 80 steps on ≤80 R03 pairs, detector-only objective;
  eval n=14 (R09) / 8 (R03) — discriminator-grade, not adoption-grade.
- All three kills are mechanism-bearing, not underpowered nulls: each
  measurement explains WHY the direction fails on this data.
