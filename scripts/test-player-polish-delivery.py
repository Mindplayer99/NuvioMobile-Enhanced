#!/usr/bin/env python3
"""Test publication rejection paths without network calls."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec=importlib.util.spec_from_file_location('delivery',Path(__file__).with_name('publish-player-polish.py'))
delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery)

class DeliveryGateTests(unittest.TestCase):
    def exercise(self,failure=None):
        calls=[];sha='reviewed-source';apk=b'verified apk fixture'
        record=dict(commit=sha,new_failures=0,ui_tests=141,critical_tests=123,
                    baseline='530f4cb483f8d211ddd7c5365ca7c516a9b69ad0',
                    apk_sha256=hashlib.sha256(apk).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'release-tools/scripts').mkdir(parents=True);(root/'candidate').mkdir()
            (root/'release-tools/scripts/orientation-release.py').write_text(
                'BUILDS = {}\ndef verify(source, version, apk):\n'
                + ('    if "remote-ui-apk" in str(apk): raise RuntimeError("remote signer failed")\n' if failure=='signer' else '')
                + '    return '+repr({k:record[k] for k in ['commit','apk_sha256']})+'\n')
            def run(*args,**kwargs):
                calls.append(args)
                if args[1:3]==('api','repos/Mindplayer99/NuvioMobile-Enhanced/actions/runs/123'):
                    return json.dumps(dict(status='completed',conclusion='failure' if failure=='tests' else 'success',
                                           head_sha=sha,head_branch='feature/orientation-ui-polish',
                                           path='.github/workflows/ui-polish.yml'))
                if args[1:3]==('run','download'):
                    folder=Path(args[args.index('--dir')+1]);folder.mkdir()
                    (folder/'test.apk').write_bytes(apk)
                    (folder/'verification.json').write_text(json.dumps(record))
                    (folder/'release-notes.md').write_text('reviewed notes')
                if args[1:3]==('release','download'):
                    folder=Path(args[args.index('--dir')+1]);folder.mkdir()
                    (folder/'test.apk').write_bytes(b'wrong' if failure=='hash' else apk)
                return '{}'
            old=Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ,GITHUB_REPOSITORY='Mindplayer99/NuvioMobile-Enhanced',
                                VERIFIED_SOURCE_SHA=sha,VERIFIED_RUN_ID='123',RUNNER_TEMP=str(root)), \
                     patch.object(delivery,'run',side_effect=run), \
                     patch.object(delivery.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
                    if failure:
                        with self.assertRaises(RuntimeError):delivery.main()
                    else:delivery.main()
            finally:os.chdir(old)
        published=any(a[1:3]==('release','edit') and '--draft=false' in a for a in calls)
        self.assertEqual(published,failure is None)
        if failure=='tests':self.assertFalse(any(a[1:3]==('release','create') for a in calls))
    def test_failed_build_never_creates_release(self):self.exercise('tests')
    def test_remote_hash_failure_never_publishes(self):self.exercise('hash')
    def test_remote_signature_failure_never_publishes(self):self.exercise('signer')
    def test_verified_remote_bytes_can_publish(self):self.exercise()

if __name__=='__main__':unittest.main()
