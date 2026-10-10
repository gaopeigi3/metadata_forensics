"""Experiment orchestration; matching never receives evaluation truth."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .synthetic import generate
from . import matching as m
from .corruption import OPERATORS, id_fragmentation
from .evaluation import ground_truth, evaluate_b03, evaluate_alias_aware
from .investigation import Investigator


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def match(clinical, lab, method='nearest', *, blocked=True):
    ct = m.build_timelines(clinical, 'Patient_ID', 'Visit_Date')
    lt = m.build_timelines(lab, 'Patient_No', 'Collection_Date')
    scorer = {'nearest': m.nearest_event_score, 'assignment': m.assignment_score,
              'sequence': m.sequence_alignment_score, 'likelihood': m.sequence_alignment_score}[method]
    scored = m.score_all_candidates(ct, lt, m.build_ranges(ct), m.build_ranges(lt),
                                    scorer, buffer_days=30 if blocked else 100000)
    if scored.empty:
        return m.rank_candidates(scored), lt
    columns = ['hit_rate', 'hits', 'mean_distance']
    directions = [False, False, True]
    if method == 'sequence':
        columns = ['hit_rate', 'hits', 'alignment_cost', 'mean_distance']
        directions = [False, False, True, True]
    elif method == 'likelihood':
        background = scored.hits.sum() / scored.n_sample_events.sum()
        scored = m.add_likelihood_score(scored, background)
        columns, directions = ['evidence_score', 'mean_distance'], [False, True]
    ranked = scored.sort_values(['clinical_id', *columns, 'lab_id'],
                               ascending=[True, *directions, True], kind='stable').copy()
    ranked['rank'] = ranked.groupby('clinical_id').cumcount() + 1
    return ranked, lt


def run_experiment(stage, output, n_patients=4000, seed=42, full=False, methods=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    clinical, lab, identifiers = generate(n_patients, seed)
    clinical.to_csv(output/'Clinical_Visits.csv', index=False)
    lab.to_csv(output/'Sample_Tracking.csv', index=False)
    evaluation_dir = output/'evaluation_only'
    evaluation_dir.mkdir(exist_ok=True)
    identifiers.to_csv(evaluation_dir/'Patient_Identifiers.csv', index=False)
    truth = ground_truth(identifiers)
    save_json(output/'run_config.json', dict(stage=stage, n_patients=n_patients, seed=seed,
              full=full, methods=methods, tie_break='lab_id ascending', buffer_days=30,
              tolerance_days=2))
    if stage in ('b01', 'b02'):
        summaries = []
        for method in methods or (['nearest'] if stage == 'b01' else ['nearest','assignment','sequence','likelihood']):
            ranked, lt = match(clinical, lab, method, blocked=stage != 'b01')
            ev, metrics = evaluate_b03(ranked, truth, lt)
            ev.to_csv(evaluation_dir/f'{method}_evaluation.csv', index=False)
            ranked.loc[ranked['rank'].le(10)].to_csv(output/f'{method}_top10.csv', index=False)
            summaries.append({'method': method, **metrics})
            print(stage, method, metrics, flush=True)
        result = pd.DataFrame(summaries)
        result.to_csv(output/'metrics.csv', index=False)
        return result
    conditions = [('clean', 0.0)] + [(op, rate) for op in OPERATORS for rate in (.05,.10,.20)]
    if stage == 'b04' and not full:
        conditions = [('clean',0.0), ('date_shift',.10), ('wrong_assignment',.10)]
    investigator = Investigator(m.build_timelines(clinical, 'Patient_ID', 'Visit_Date'))
    summaries, diagnostics = [], []
    for op, rate in conditions:
        dirty, manifest = (lab.copy(), pd.DataFrame(columns=['Sample_ID'])) if op == 'clean' else OPERATORS[op](lab, rate, seed=seed)
        tag = f'{op}_{int(rate*100):02d}'
        manifest.to_csv(evaluation_dir/f'{tag}_manifest.csv', index=False)
        ranked, lt = match(clinical, dirty)
        ev, metrics = evaluate_b03(ranked, truth, lt)
        ev.to_csv(evaluation_dir/f'{tag}_evaluation.csv', index=False)
        summary = {'operator':op, 'rate':rate, **metrics}
        if stage == 'b04':
            features = investigator.counterfactual_features(ranked, lt)
            features['review'] = ((features.n_dates < 2) | (features.margin <= 0) | (features.instability.fillna(1) > 0))
            features['decision'] = np.where(features.review, 'REVIEW', 'MATCH')
            suspicious = investigator.event_suspicion(features, dirty)
            features.to_csv(output/f'{tag}_decisions.csv', index=False)
            suspicious.to_csv(output/f'{tag}_event_suspicion.csv', index=False)
            # Evaluation labels are added to a separate copy after decisions are fixed.
            assessed = features.assign(correct=features.best_lab_id.eq(features.clinical_id.map(truth)))
            auto = assessed.loc[~assessed.review]
            summary.update(b02_top1=metrics['top1'], coverage_all_gt=len(auto)/len(truth),
                           accuracy_auto=float(auto.correct.mean()),
                           accuracy_all_proposed=float(assessed.correct.mean()),
                           review_rate_among_proposed=float(assessed.review.mean()),
                           n_proposed=len(features), **investigator.localization_metrics(suspicious, manifest))
            for review, part in assessed.groupby('review'):
                diagnostics.append(dict(operator=op,rate=rate,review=bool(review),n=len(part),error_rate=float((~part.correct).mean())))
            if len(features):
                cid = features.sort_values(['review','n_flips'], ascending=False).iloc[0].clinical_id
                case = investigator.investigate(cid, dirty, ranked, features, suspicious)
                save_json(output/f'{tag}_investigation.json', case)
                if op == 'date_shift' and rate == .10:
                    save_json(output/'example_investigation.json', case)
        summaries.append(summary)
        pd.DataFrame(summaries).to_csv(output/f'{stage}_results_partial.csv', index=False)
        print(stage, tag, 'top1=', metrics['top1'], flush=True)
    result = pd.DataFrame(summaries)
    result['delta_top1'] = result.top1 - result.iloc[0].top1
    result['delta_retrieval'] = result.retrieval_rate - result.iloc[0].retrieval_rate
    result.to_csv(output/f'{stage}_results.csv', index=False)
    if stage == 'b03':
        frag_results = []
        for rate in (.05,.10,.20):
            dirty, manifest, aliases = id_fragmentation(lab, rate, seed=seed)
            ranked, lt = match(clinical, dirty)
            _, metrics = evaluate_b03(ranked, truth, lt)
            frag_results.append(dict(rate=rate, **metrics, alias_aware_top1=evaluate_alias_aware(ranked, truth, aliases)))
            manifest.to_csv(evaluation_dir/f'fragmentation_{int(rate*100)}_manifest.csv', index=False)
            save_json(evaluation_dir/f'fragmentation_{int(rate*100)}_aliases.json', aliases)
        pd.DataFrame(frag_results).to_csv(output/'fragmentation_diagnostic.csv', index=False)
    else:
        pd.DataFrame(diagnostics).to_csv(output/'review_diagnostics.csv', index=False)
    plot_results(result, output, stage)
    return result


def plot_results(result, output, stage):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for metric in ['top1', 'retrieval_rate']:
        fig, ax = plt.subplots(figsize=(7,4))
        for op, sub in result.loc[result.operator.ne('clean')].groupby('operator'):
            ax.plot(sub.rate*100, sub[metric], marker='o', label=op)
        ax.axhline(result.iloc[0][metric], linestyle='--', label='clean')
        ax.set(xlabel='Corrupted sample rows (%)', ylabel=metric, title=stage.upper())
        ax.legend(); fig.tight_layout()
        fig.savefig(output/f'{metric}.png', dpi=150); plt.close(fig)
    if stage == 'b04':
        sub = result.loc[result.operator.ne('clean')]
        fig, ax = plt.subplots(figsize=(8,4)); x = np.arange(len(sub))
        ax.bar(x-.2, sub.precision_at_k, .4, label='Precision@100')
        ax.bar(x+.2, sub.scope_prevalence, .4, label='Within-scope prevalence')
        ax.set_xticks(x, [f'{r.operator} {r.rate:.0%}' for r in sub.itertuples()], rotation=35, ha='right')
        ax.legend(); fig.tight_layout(); fig.savefig(output/'localization.png', dpi=150); plt.close(fig)
