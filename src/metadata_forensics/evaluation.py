import numpy as np
import pandas as pd

def evaluate_b03(ranked, truth, lab_timelines):
    gt = pd.Series(truth, name='true_lab_id')
    truth_df = gt.rename_axis('clinical_id').reset_index()
    if ranked.empty:
        hits = pd.DataFrame(columns=['clinical_id', 'rank'])
    else:
        tagged = ranked.assign(true_lab_id=ranked['clinical_id'].map(truth))
        hits = tagged.loc[tagged['lab_id'].eq(tagged['true_lab_id']),
                          ['clinical_id', 'rank']]
    ev = truth_df.merge(hits, on='clinical_id', how='left')
    ev['rank'] = pd.to_numeric(ev['rank'], errors='coerce').fillna(np.inf)
    ev['lab_observable'] = ev['true_lab_id'].isin(lab_timelines)
    ev['retrieved'] = np.isfinite(ev['rank'])
    observed = ev['lab_observable']
    retrieved = ev['retrieved']
    metrics = {
        'n_gt': len(ev),
        'n_lab_observable': int(observed.sum()),
        'n_unobservable': int((~observed).sum()),
        'n_blocked_out': int((observed & ~retrieved).sum()),
        'lab_observable_rate': float(observed.mean()),
        'retrieval_rate': float(retrieved.mean()),
        'blocking_recall_given_observable': float(retrieved[observed].mean()) if observed.any() else np.nan,
        'top1': float((ev['rank'] <= 1).mean()),
        'top3': float((ev['rank'] <= 3).mean()),
        'top10': float((ev['rank'] <= 10).mean()),
        'mrr': float((1 / ev['rank']).mean()),
        'top1_given_retrieved': float((ev.loc[retrieved, 'rank'] <= 1).mean()) if retrieved.any() else np.nan,
    }
    return ev, metrics

def evaluate_alias_aware(ranked, truth, alias_to_original):
    top = ranked.loc[ranked['rank'].eq(1), ['clinical_id', 'lab_id']].copy()
    top['canonical_pred'] = top['lab_id'].replace(alias_to_original)
    top['canonical_truth'] = top['clinical_id'].map(truth)
    correct = top['canonical_pred'].eq(top['canonical_truth']).sum()
    return float(correct / len(truth))

def ground_truth(identifiers):
    clinical = identifiers.query("system == 'clinical'").set_index('identifier')['patient_uid']
    lab = identifiers.query("system == 'lab'").set_index('patient_uid')['identifier']
    return {cid: lab[uid] for cid, uid in clinical.items()}
