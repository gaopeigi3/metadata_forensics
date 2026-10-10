import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import binom

def build_timelines(df, id_col, date_col):
    return (df.groupby(id_col)[date_col]
              .apply(lambda x: sorted(x.dropna().unique()))
              .loc[lambda x: x.map(len) > 0].to_dict())

def build_ranges(timelines):
    return {key: (min(dates), max(dates)) for key, dates in timelines.items()}

def possible_candidate(clinical_range, lab_range, buffer_days=30):
    cs, ce = clinical_range
    ls, le = lab_range
    return (le >= cs - pd.Timedelta(days=buffer_days)
            and ls <= ce + pd.Timedelta(days=buffer_days))

def nearest_event_score(visit_dates, sample_dates, tolerance_days=2):
    distances = [min(abs((s-v).days) for v in visit_dates) for s in sample_dates]
    hits = sum(d <= tolerance_days for d in distances)
    return dict(hits=hits, n_sample_events=len(sample_dates),
                hit_rate=hits/len(sample_dates),
                mean_distance=sum(distances)/len(distances),
                distances=distances)

def score_all_candidates(clinical_timelines, lab_timelines,
                         clinical_ranges, lab_ranges, scoring_function,
                         buffer_days=30, **kwargs):
    rows = []
    # Vectorize range blocking, preserving the notebook's candidate iteration order.
    lab_ids = list(lab_timelines)
    starts = np.array([pd.Timestamp(lab_ranges[k][0]).value for k in lab_ids], dtype=np.int64)
    ends = np.array([pd.Timestamp(lab_ranges[k][1]).value for k in lab_ids], dtype=np.int64)
    buffer = pd.Timedelta(days=buffer_days).value
    for cid, vdates in clinical_timelines.items():
        start, end = (pd.Timestamp(d).value for d in clinical_ranges[cid])
        positions = np.flatnonzero((ends >= start-buffer) & (starts <= end+buffer))
        for j in positions:
            lid = lab_ids[j]
            rows.append(dict(clinical_id=cid, lab_id=lid,
                             **scoring_function(vdates, lab_timelines[lid], **kwargs)))
    return pd.DataFrame(rows)


def rank_candidates(results):
    if results.empty:
        return pd.DataFrame(columns=['clinical_id', 'lab_id', 'rank'])
    # B02 ranking: hit_rate desc, hits desc, mean_distance asc.
    # Add lab_id only as deterministic tie-breaker; tie sensitivity noted below.
    ranked = results.sort_values(
        ['clinical_id', 'hit_rate', 'hits', 'mean_distance', 'lab_id'],
        ascending=[True, False, False, True, True], kind='stable').copy()
    ranked['rank'] = ranked.groupby('clinical_id').cumcount() + 1
    return ranked

def assignment_score(
    visit_dates,
    sample_dates,
    tolerance_days=2
):
    # Build distance matrix:
    # rows = sample events
    # columns = clinical visits
    distance_matrix = np.array([
        [
            abs((sample_date - visit_date).days)
            for visit_date in visit_dates
        ]
        for sample_date in sample_dates
    ])

    # Find minimum-cost one-to-one assignment
    sample_idx, visit_idx = linear_sum_assignment(
        distance_matrix
    )

    assigned_distances = distance_matrix[
        sample_idx,
        visit_idx
    ].tolist()

    hits = sum(
        distance <= tolerance_days
        for distance in assigned_distances
    )

    n_sample_events = len(sample_dates)

    hit_rate = hits / n_sample_events

    mean_distance = (
        sum(assigned_distances)
        / len(assigned_distances)
    )

    return {
        "hits": hits,
        "n_sample_events": n_sample_events,
        "hit_rate": hit_rate,
        "mean_distance": mean_distance,
        "distances": assigned_distances,
    }

def sequence_alignment_score(
    visit_dates,
    sample_dates,
    tolerance_days=2,
    skip_visit_cost=0,
    skip_sample_cost=30,
):
    n = len(visit_dates)
    m = len(sample_dates)

    # dp[i, j]:
    # minimum cost for aligning
    # first i clinical visits with first j sample events
    dp = np.full((n + 1, m + 1), np.inf)

    # Keep track of which operation produced each cell
    trace = np.empty(
        (n + 1, m + 1),
        dtype=object
    )

    dp[0, 0] = 0

    # Skipping clinical visits is allowed
    for i in range(1, n + 1):
        dp[i, 0] = (
            dp[i - 1, 0]
            + skip_visit_cost
        )
        trace[i, 0] = "skip_visit"

    # A sample with no clinical explanation is penalized
    for j in range(1, m + 1):
        dp[0, j] = (
            dp[0, j - 1]
            + skip_sample_cost
        )
        trace[0, j] = "skip_sample"

    # Dynamic programming
    for i in range(1, n + 1):
        for j in range(1, m + 1):

            distance = abs(
                (
                    sample_dates[j - 1]
                    - visit_dates[i - 1]
                ).days
            )

            match_cost = (
                dp[i - 1, j - 1]
                + distance
            )

            skip_visit = (
                dp[i - 1, j]
                + skip_visit_cost
            )

            skip_sample = (
                dp[i, j - 1]
                + skip_sample_cost
            )

            costs = [
                match_cost,
                skip_visit,
                skip_sample,
            ]

            best = np.argmin(costs)

            dp[i, j] = costs[best]

            trace[i, j] = [
                "match",
                "skip_visit",
                "skip_sample",
            ][best]

    # --------------------------------------------------
    # Trace back through the optimal alignment
    # --------------------------------------------------

    i = n
    j = m

    matched_distances = []

    while i > 0 or j > 0:

        operation = trace[i, j]

        if operation == "match":

            distance = abs(
                (
                    sample_dates[j - 1]
                    - visit_dates[i - 1]
                ).days
            )

            matched_distances.append(distance)

            i -= 1
            j -= 1

        elif operation == "skip_visit":
            i -= 1

        elif operation == "skip_sample":
            j -= 1

        else:
            break

    matched_distances.reverse()

    hits = sum(
        distance <= tolerance_days
        for distance in matched_distances
    )

    n_sample_events = len(sample_dates)

    hit_rate = (
        hits / n_sample_events
        if n_sample_events > 0
        else 0
    )

    alignment_cost = dp[n, m]

    mean_distance = (
        np.mean(matched_distances)
        if matched_distances
        else np.inf
    )

    return {
        "hits": hits,
        "n_sample_events": n_sample_events,
        "hit_rate": hit_rate,
        "mean_distance": mean_distance,
        "alignment_cost": alignment_cost,
        "distances": matched_distances,
    }

def add_likelihood_score(
    matching_results,
    p_background
):
    results = matching_results.copy()

    results["chance_probability"] = binom.sf(
        results["hits"] - 1,
        results["n_sample_events"],
        p_background
    )

    results["evidence_score"] = (
        -np.log10(
            results["chance_probability"]
            .clip(lower=1e-300)
        )
    )

    return results
