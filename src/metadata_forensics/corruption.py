import numpy as np
import pandas as pd

# All operators take the same original laboratory table, never a previously corrupted table.
# The manifest tracks the precise rows affected, including original and new values.

def _select_rows(lab_df, rate, seed):
    assert 0 <= rate <= 1
    rng = np.random.default_rng(seed)
    n = round(len(lab_df) * rate)
    chosen = rng.choice(len(lab_df), size=n, replace=False)
    return rng, np.sort(chosen)

def date_shift(lab_df, rate, seed=42, min_days=7, max_days=90):
    # Shift dates by 7-90 days
    out = lab_df.copy().reset_index(drop=True)
    rng, idx = _select_rows(out, rate, seed)
    old = out.loc[idx, 'Collection_Date'].copy()
    shifts = rng.integers(min_days, max_days + 1, size=len(idx))
    shifts *= rng.choice([-1, 1], size=len(idx))
    out.loc[idx, 'Collection_Date'] = old + pd.to_timedelta(shifts, unit='D')
    manifest = pd.DataFrame({'Sample_ID': out.loc[idx, 'Sample_ID'].to_numpy(),
                             'operator': 'date_shift', 'old_date': old.to_numpy(),
                             'new_date': out.loc[idx, 'Collection_Date'].to_numpy(),
                             'shift_days': shifts})
    return out, manifest

def missing_event(lab_df, rate, seed=42):
    # Remove selected sample rows
    out = lab_df.copy().reset_index(drop=True)
    _, idx = _select_rows(out, rate, seed)
    manifest = out.iloc[idx][['Sample_ID', 'Patient_No', 'Collection_Date']].copy()
    manifest['operator'] = 'missing_event'
    return out.drop(index=idx).reset_index(drop=True), manifest.reset_index(drop=True)

def wrong_assignment(lab_df, rate, seed=42):
    # Assign selected samples to another ID
    out = lab_df.copy().reset_index(drop=True)
    rng, idx = _select_rows(out, rate, seed)
    ids = np.array(sorted(out['Patient_No'].unique()))
    if len(ids) < 2 and len(idx):
        raise ValueError('Need at least two laboratory identities')
    old = out.loc[idx, 'Patient_No'].to_numpy().copy()
    id_positions = pd.Index(ids).get_indexer(old)
    offsets = rng.integers(1, len(ids), size=len(idx)) if len(idx) else np.array([], dtype=int)
    new = ids[(id_positions + offsets) % len(ids)] if len(idx) else old
    out.loc[idx, 'Patient_No'] = new
    manifest = pd.DataFrame({'Sample_ID': out.loc[idx, 'Sample_ID'].to_numpy(),
                             'operator': 'wrong_assignment',
                             'old_lab_id': old, 'new_lab_id': new})
    return out, manifest

def id_fragmentation(lab_df, rate, seed=42):
    # Relabel rows with aliases; alias map is evaluation-only.
    out = lab_df.copy().reset_index(drop=True)
    _, idx = _select_rows(out, rate, seed)
    old = out.loc[idx, 'Patient_No'].to_numpy().copy()
    aliases = {lid: f'FRAG_{j:05d}' for j, lid in enumerate(sorted(set(old)), 1)}
    new = [aliases[lid] for lid in old]
    out.loc[idx, 'Patient_No'] = new
    manifest = pd.DataFrame({'Sample_ID': out.loc[idx, 'Sample_ID'].to_numpy(),
                             'operator': 'id_fragmentation',
                             'old_lab_id': old, 'new_lab_id': new})
    return out, manifest, {alias: original for original, alias in aliases.items()}

OPERATORS = {'date_shift': date_shift,
             'missing_event': missing_event,
             'wrong_assignment': wrong_assignment}
RATES = (0.0, 0.05, 0.10, 0.20)
