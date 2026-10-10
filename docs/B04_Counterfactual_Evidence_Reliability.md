# B04 — Counterfactual Evidence Reliability & Investigation

**Question:** Can we identify fragile identity decisions and suspicious laboratory events **without using corruption manifests or ground truth at inference time**?

Self-contained notebook based on B03's **same seed-42 synthetic generator and frozen B02a matcher**. B04 does not retrain a model. It separates: (1) ranking, (2) leave-one-event-out stability, (3) selective review, (4) corruption localization. **Important:** stability measures sensitivity, not factual truth; temporal-only evidence cannot reliably detect all wrong assignments.

**Runtime:** N=4000 candidate scoring is expensive. `QUICK=True` evaluates clean + 10% shifts + 10% wrong assignment; switch to `False` for all 10 conditions. The original B03 corruption operators use row-level rates.

## 1. Reproduce B03 data and freeze B02a

## 2. Counterfactual decision stability

For each clinical ID, take the **top two candidates from the original B02 ranking**. Delete each **unique sample date** from the current top candidate's timeline, rescore those two hypotheses and check whether the winner flips. This is **conditional top-two stability**, not full-global leave-one-out ranking. Missing evidence can cause low stability even when no record is corrupt. Scores are recomputed using the frozen B02a scoring and its tie rules. Do not interpret `stability` as a probability of correctness.

`margin` is the B02 hit-rate difference between top two, with zero when there is no second candidate; it is not calibrated.

## 3. Suspicious-event localization (no labels in scoring)

For every laboratory row belonging to the **current top-1 laboratory ID**, compute the distance to its nearest visit of the proposed clinical identity. Rank by this disagreement distance (larger = more suspicious), breaking ties by `Sample_ID`. We also flag dates whose deletion flips the top-two decision. The date-level counterfactual result is joined to sample rows, but **not** used as a corruption label. PB/BM records on the same day share evidence and are not independent.

**Evaluation scope:** This detects corruption *among observed rows in proposed top-1 pairings only*. Missing rows cannot be localized, and wrong-assigned rows outside proposed pairs are outside the inspected population. Precision@K is conditional on that scope and should be compared with its **within-scope prevalence**, not global corruption rate.

## 4. Run frozen B02a + B04 diagnostics

The corruption manifest is used **only for retrospective localization evaluation**, never in ranking, features, or review decisions. `ground_truth` is used only for correctness metrics. Review thresholds below are fixed heuristics for an MVP, not fitted/calibrated probabilities.

## 5. H2: Does instability predict wrong identity decisions?

Compare error rates in **stable** and **unstable** groups, and measure precision of review flags. This is an association test; a strong review rule is not necessarily a better matcher. `coverage_all_gt` counts unobservable identities as not auto-matched.

## 6. H3: Is event localization better than random review?

Plot `Precision@K` against the corruption prevalence among inspectable rows. Note that large date shifts are directly visible to a temporal disagreement detector, so this is a **limited synthetic benchmark**, not general corruption detection.

## 7. B05-ready investigation report: competing hypotheses and counterfactuals

Generate a **traceable, non-LLM JSON report** for selected clinical IDs. Supporting and contradicting evidence is computed from observed dates; the hidden crosswalk is not included. Suggested review steps are operational, not claims that an event is actually wrong.

## 8. Interpretation and stop criteria

**H1 (robust Top-1 improvement)** is **not tested** here: the ranking is deliberately frozen. B04 tests **H2** (whether stability flags correlate with errors) and **H3** (whether temporal disagreement localizes known corrupt observed rows better than a random within-scope baseline). This distinction prevents claiming a robust-matcher accuracy gain without changing the matcher.

**Caveats:** single generator/seed; no train/test calibration; conditional top-two perturbation only; leave-one-*unique-date*-out but row-level localization; no global one-to-one identity constraint; no independent demographic evidence; top-1-only inspection scope; `wrong_assignment` can produce coherent false histories; missing events are unobservable. Report review coverage alongside conditional accuracy. The optional fragmentation experiment remains outside B04 because entity-level alias resolution requires a different target definition.

**Finish:** If the review rule separates errors and the event ranking beats random prevalence, save the outputs and stop. If not, report negative results; do not silently tune thresholds on the same corruption draws.