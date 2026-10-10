import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from metadata_forensics.synthetic import generate
from metadata_forensics import matching as m
from metadata_forensics.corruption import OPERATORS, id_fragmentation
from metadata_forensics.evaluation import evaluate_b03, ground_truth
from metadata_forensics.pipeline import match
from metadata_forensics.investigation import Investigator
from metadata_forensics.reporting import evidence_payload, validate_report, run_report

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.clinical, self.lab, self.ids = generate(40)

    def test_deterministic_generator(self):
        for a,b in zip((self.clinical,self.lab,self.ids),generate(40)):
            pd.testing.assert_frame_equal(a,b)
        self.assertEqual(len(self.ids), 80)
        self.assertTrue(self.lab.Sample_ID.is_unique)

    def test_blocking_equivalence(self):
        ct=m.build_timelines(self.clinical,'Patient_ID','Visit_Date')
        lt=m.build_timelines(self.lab,'Patient_No','Collection_Date')
        cr,lr=m.build_ranges(ct),m.build_ranges(lt)
        for scorer in [m.nearest_event_score,m.assignment_score,m.sequence_alignment_score]:
            expected=[]
            for cid,vd in ct.items():
                for lid,sd in lt.items():
                    if m.possible_candidate(cr[cid],lr[lid]):
                        expected.append(dict(clinical_id=cid,lab_id=lid,**scorer(vd,sd)))
            pd.testing.assert_frame_equal(pd.DataFrame(expected),m.score_all_candidates(ct,lt,cr,lr,scorer))

    def test_all_gt_denominator(self):
        ranked,lt=match(self.clinical,self.lab)
        _,metrics=evaluate_b03(ranked,ground_truth(self.ids),lt)
        self.assertEqual(metrics['n_gt'],40)
        self.assertEqual(metrics['top1'],.975)
        empty,metrics=evaluate_b03(ranked.iloc[:0],ground_truth(self.ids),{})
        self.assertEqual(metrics['top1'],0)
        self.assertEqual(metrics['mrr'],0)
        self.assertEqual(len(empty),40)

    def test_corruption_independence_and_manifest(self):
        original=self.lab.copy(deep=True)
        for name,operator in OPERATORS.items():
            dirty,audit=operator(self.lab,.1)
            self.assertEqual(len(audit),round(len(self.lab)*.1))
            pd.testing.assert_frame_equal(self.lab,original)
            if name=='wrong_assignment':
                self.assertTrue(audit.old_lab_id.ne(audit.new_lab_id).all())
            if name=='missing_event':
                self.assertEqual(len(dirty)+len(audit),len(self.lab))
        dirty,audit,aliases=id_fragmentation(self.lab,.1)
        self.assertEqual(set(audit.new_lab_id),set(aliases))

    def test_b04_report_has_no_labels(self):
        ranked,lt=match(self.clinical,self.lab)
        inv=Investigator(m.build_timelines(self.clinical,'Patient_ID','Visit_Date'))
        features=inv.counterfactual_features(ranked,lt)
        features['decision']='REVIEW'
        suspicious=inv.event_suspicion(features,self.lab)
        report=inv.investigate('UPIN101',self.lab,ranked,features,suspicious)
        self.assertNotIn('correct',json.dumps(report))
        self.assertNotIn('patient_uid',json.dumps(report))
        report['correct']=True
        self.assertNotIn('correct',evidence_payload(report))
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'case.json';source.write_text(json.dumps(report))
            bundle=run_report(source,Path(tmp)/'output')
            self.assertFalse(bundle['metadata']['live'])
            self.assertNotIn('llm_report',bundle)

    def test_empty_investigation(self):
        inv=Investigator({})
        features=inv.counterfactual_features(pd.DataFrame(columns=['clinical_id','lab_id','rank']),{})
        self.assertTrue(inv.event_suspicion(features,self.lab.iloc[:0]).empty)

if __name__=='__main__':
    unittest.main()
