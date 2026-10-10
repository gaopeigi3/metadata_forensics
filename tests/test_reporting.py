import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from metadata_forensics.reporting import validate_report, run_report

class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {'clinical_id':'C1','decision':'REVIEW','top_candidates':[
            {'lab_id':'L1','rank':1,'evidence':[{'sample_id':'S1','role':'support'}]}]}
        self.report = {'clinical_id':'C1','decision':'REVIEW','summary':'需要核查',
                       'candidate_assessments':[{'lab_id':'L1','supporting_sample_ids':['S1'],
                       'contradicting_sample_ids':[],'interpretation':'时间证据有限'}],
                       'uncertainties':[],'recommended_checks':[],'limitations':['不能确认身份']}

    def test_reject_changed_decision_and_role(self):
        self.assertEqual(validate_report(self.report,self.evidence),[])
        self.report['decision']='MATCH'
        self.report['candidate_assessments'][0]['contradicting_sample_ids']=['S1']
        issues=validate_report(self.report,self.evidence)
        self.assertIn('upstream decision changed',issues)
        self.assertTrue(any('roles' in x for x in issues))

    def test_mock_transport_audit_and_markdown(self):
        # Transport mock checks plumbing only; it is not live LLM validation.
        response={'choices':[{'message':{'content':json.dumps(self.report)}}]}
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'case.json';source.write_text(json.dumps(self.evidence))
            with patch('metadata_forensics.reporting.urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
                result=run_report(source,Path(tmp)/'out',live=True,provider='ollama')
            self.assertTrue(result['metadata']['validated'])
            self.assertTrue((Path(tmp)/'out/C1_report.md').exists())
            self.assertTrue((Path(tmp)/'out/C1_llm_audit.json').exists())
