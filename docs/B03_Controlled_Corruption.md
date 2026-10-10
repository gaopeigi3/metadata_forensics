# B03 — Controlled Data Corruption

**Objective:** quantify how different kinds of dirty laboratory records degrade the **frozen B02a temporal-only matcher**. Run top to bottom.

- Reuse B02 synthetic generator (seed 42; N=4000).
- Modify **laboratory observations only**, never the canonical crosswalk.
- Rates: 0%, 5%, 10%, 20% of **original sample rows** (not patients).
- Rebuild timelines, ranges, candidates and rankings after each perturbation.
- Distinguish **no observed lab identity** from **true pair excluded by blocking**.
- Fragmentation changes the identity representation; evaluate it separately using an alias-aware metric.

**Dependencies:** `pandas`, `numpy`, `matplotlib`. B03 runs independently of B02; the generator cells below are copied from the uploaded B02.

## 1. Reproduce the B02 synthetic data (same generator, same seed)

## 2. Load data and freeze the B02a matching logic

### Evaluation populations

- **All-GT end-to-end**: every canonical clinical patient in the denominator, including patients without a sample. Comparable with B02's official metric.
- **Lab-observable**: the canonical laboratory ID still has ≥1 event after corruption.
- **Blocking recall given observable**: fraction of lab-observable true pairs surviving blocking.
- **Ranking Top-1 given retrieved**: fraction of retrieved true pairs ranked first.

These distinctions prevent incorrectly attributing missing laboratory observations to blocking.

## 3. Corruption operators and audit manifest

## 4. Integrity checks (run before the benchmark)

## 5. Run B03: fixed B02a matcher, 13 independent conditions

This is the **main computational cell**; N=4000 and the original B02 nested-loop blocking may take several minutes per condition. Each condition starts from the original clean table. Results are saved as they finish.

**Important:** the deterministic `lab_id` tie-breaker is an explicit reproducibility improvement over B02's implicit tie order. Verify the clean Top-1 against 0.84825; if it differs, report the difference rather than silently claiming exact comparability.

## 6. Compare degradation against the clean control

## 7. ID fragmentation: separate alias-aware diagnostic

Fragmentation **changes the target identity space**. The original canonical lab ID may retain some samples, while an alias contains the rest. Therefore, evaluating only against the original lab ID is not sufficient.

We report two explicitly different metrics:

1. **Exact-ID Top-1**: original B02 definition (strict; treats an alias as wrong).
2. **Alias-aware Top-1**: top-ranked ID maps to the correct canonical lab identity using an **evaluation-only** alias map.

The alias map is never used in matching. Alias-aware success measures recovery of the underlying person, **not** whether the system has actually discovered and merged the fragmented identifiers. This is a diagnostic, not an end-to-end fragmentation-resolution solution.

## 8. Interpretation / limitations

Fill in after execution:

- Which corruption causes the largest **end-to-end Top-1** loss at 10%?
- Does loss come from unobservability, blocking exclusion, or ranking?
- Does the ranking degrade even when true pairs survive blocking?
- How much of fragmentation loss is strict-ID scoring versus actual wrong-person selection?

**Limitations:** This is a single synthetic generator with a single seed and one draw per corruption rate; estimates have not been averaged over repeated seeds. Sample-level rates do not equal patient-level rates. Date shifts are intentionally large (7–90 days); smaller shifts may behave differently. The matcher uses only temporal evidence. Tie-breaking may change exact Top-1 relative to the original B02 notebook. Do not interpret alias-aware metrics as a deployed crosswalk repair method.

**Next:** B04 adds evidence-aware robustness and review/abstention, evaluated on the same frozen B03 conditions.