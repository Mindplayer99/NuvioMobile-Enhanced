import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
s=importlib.util.spec_from_file_location('gate',Path(__file__).with_name('orientation-tests.py'))
g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
class DifferentialTests(unittest.TestCase):
    def setUp(self):
        self.good={f'com.nuvio.app.features.{area}.{name}#case':{'status':'passed','failures':[]} for area,name in [('player','PlayerOrientationTest'),('player','PlayerOrientationAndroidTest'),('updater','OrientationUpdateChannelTest')]}
        self.failure={'status':'failed','failures':[{'type':'AssertionError','message':'expected 60 actual 30','frames':[]}]}
    def test_identical_upstream_failure_allowed(self):
        c={**self.good,'unrelated#retry':self.failure}
        self.assertEqual(list(g.compare(c,c)),['unrelated#retry'])
    def test_new_or_changed_failure_rejected(self):
        c={**self.good,'unrelated#retry':self.failure}
        for u in [self.good,{**self.good,'unrelated#retry':{'status':'failed','failures':[]}}]:
            with self.assertRaises(RuntimeError):g.compare(c,u)
    def test_even_inherited_critical_failure_blocks(self):
        c={**self.good};c[next(iter(c))]=self.failure
        with self.assertRaises(RuntimeError):g.compare(c,c)
    def test_missing_or_newly_skipped_test_blocks(self):
        u={**self.good,'other#test':{'status':'passed','failures':[]}}
        with self.assertRaises(RuntimeError):g.compare(self.good,u)
        with self.assertRaises(RuntimeError):g.compare({**u,'other#test':{'status':'skipped','failures':[]}},u)
    def test_signature_preserves_assertion_numbers_but_not_line_numbers(self):
        a=ET.fromstring('<failure type="AssertionError" message="expected 60 actual 30">at com.nuvio.Test.case(Test.kt:12)</failure>')
        b=ET.fromstring('<failure type="AssertionError" message="expected 60 actual 30">at com.nuvio.Test.case(Test.kt:14)</failure>')
        self.assertEqual(g.normalize(a),g.normalize(b));b.set('message','expected 60 actual 31');self.assertNotEqual(g.normalize(a),g.normalize(b))
    def test_build_or_test_failure_evidence_cannot_publish(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'evidence.json';p.write_text(json.dumps({'status':'blocked','commit':'x','upstream_commit':'y'}))
            with self.assertRaises(RuntimeError):g.validate(p,{'commit':'x','upstream_commit':'y'})
if __name__=='__main__':unittest.main()
