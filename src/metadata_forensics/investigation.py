import numpy as np
import pandas as pd
from .matching import nearest_event_score

class Investigator:
    """Observed timelines only; labels are passed only to localization evaluation."""
    def __init__(self, clinical_timelines):
        self.clinical_timelines = clinical_timelines

    def score_pair(self, cid, lid, lab_dates):
        if not lab_dates:
            return None
        return nearest_event_score(self.clinical_timelines[cid], lab_dates, tolerance_days=2)

    def winner_of_two(self, cid, options):
        # options: list of (lab_id, dates). Apply B02a tie ordering.
        rows = []
        for lid, dates in options:
            s = self.score_pair(cid, lid, dates)
            if s is not None:
                rows.append((lid, s))
        if not rows:
            return None
        return sorted(rows, key=lambda x: (-x[1]['hit_rate'], -x[1]['hits'], x[1]['mean_distance'], x[0]))[0][0]

    def counterfactual_features(self, ranked, lt):
        top = ranked.loc[ranked['rank'].le(2)].sort_values(['clinical_id','rank'])
        output = []
        for cid, group in top.groupby('clinical_id', sort=False):
            g = group.to_dict('records'); best = g[0]; best_id = best['lab_id']
            second = g[1] if len(g) > 1 else None
            margin = float(best['hit_rate'] - second['hit_rate']) if second else 0.0
            dates = lt[best_id]
            flips = 0; influential_dates = []
            if second is not None:
                other = (second['lab_id'], lt[second['lab_id']])
                for j, d in enumerate(dates):
                    remaining = dates[:j] + dates[j+1:]
                    alternative = self.winner_of_two(cid, [(best_id, remaining), other])
                    if alternative != best_id:
                        flips += 1; influential_dates.append(str(pd.Timestamp(d).date()))
            trials = len(dates) if second is not None else 0
            output.append(dict(clinical_id=cid, best_lab_id=best_id,
                               second_lab_id=second['lab_id'] if second else None,
                               hit_rate=float(best['hit_rate']), hits=int(best['hits']),
                               n_dates=len(dates), margin=margin,
                               n_counterfactuals=trials, n_flips=flips,
                               instability=flips/trials if trials else np.nan,
                               influential_dates=';'.join(influential_dates)))
        return pd.DataFrame(output, columns=['clinical_id','best_lab_id','second_lab_id','hit_rate','hits','n_dates','margin','n_counterfactuals','n_flips','instability','influential_dates'])

    def event_suspicion(self, features, lab_df):
        chosen = features[['clinical_id','best_lab_id','influential_dates']].copy()
        merged = chosen.merge(lab_df, left_on='best_lab_id', right_on='Patient_No', how='inner')
        if merged.empty:
            return merged.assign(distance_days=pd.Series(dtype=float), critical_date=pd.Series(dtype=bool), suspicion_score=pd.Series(dtype=float))
        def row_distance(r):
            return min(abs((r.Collection_Date - v).days) for v in self.clinical_timelines[r.clinical_id])
        merged['distance_days'] = merged.apply(row_distance, axis=1)
        merged['critical_date'] = merged.apply(
            lambda r: str(r.Collection_Date.date()) in r.influential_dates.split(';'), axis=1)
        merged['suspicion_score'] = merged['distance_days'].astype(float)
        return merged.sort_values(['suspicion_score','Sample_ID'], ascending=[False,True]).reset_index(drop=True)

    def localization_metrics(self, suspicious, manifest, k=100):
        # Unique sample IDs, since one sample may appear in several proposed top-1 pairings.
        unique = suspicious.sort_values(['suspicion_score','Sample_ID'], ascending=[False,True]).drop_duplicates('Sample_ID')
        known_corrupt = set(manifest['Sample_ID']) if 'Sample_ID' in manifest else set()
        labels = unique['Sample_ID'].isin(known_corrupt).to_numpy()
        n = min(k, len(labels))
        return {'scope_rows':len(labels), 'scope_corrupt':int(labels.sum()),
                'scope_prevalence':float(labels.mean()) if len(labels) else np.nan,
                'precision_at_k':float(labels[:n].mean()) if n else np.nan,
                'lift_at_k':float(labels[:n].mean()/labels.mean()) if n and labels.mean() else np.nan}

    def investigate(self, cid, dirty, ranked, features, suspicious, top_n=3):
        candidates = ranked.loc[ranked.clinical_id.eq(cid)].head(top_n)
        feature = features.loc[features.clinical_id.eq(cid)]
        f = feature.iloc[0].to_dict() if len(feature) else None
        result={'clinical_id':cid,'decision':f['decision'] if f else 'UNRESOLVED',
                'top_candidates':[], 'critical_dates':f['influential_dates'].split(';') if f and f['influential_dates'] else [],
                'recommended_action':'Verify source sample accession dates and patient assignment; compare original clinical encounter records.'}
        for row in candidates.itertuples():
            lab_rows=dirty.loc[dirty.Patient_No.eq(row.lab_id)]
            ev=[]
            for r in lab_rows.itertuples():
                d=min(abs((r.Collection_Date-v).days) for v in self.clinical_timelines[cid])
                ev.append({'sample_id':r.Sample_ID,'collection_date':str(r.Collection_Date.date()),
                           'nearest_visit_distance_days':int(d),
                           'role':'support' if d<=2 else 'contradiction'})
            result['top_candidates'].append({'lab_id':row.lab_id,'rank':int(row.rank),
                                             'hit_rate':float(row.hit_rate), 'hits':int(row.hits),
                                             'evidence':ev})
        return result
