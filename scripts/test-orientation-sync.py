#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import os
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('sync', Path(__file__).with_name('orientation-sync.py'))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class IntegrationGateTests(unittest.TestCase):
    def test_only_published_stable_numeric_tags_are_selected(self):
        rows = [{'tag_name': tag, 'draft': draft, 'prerelease': pre} for tag, draft, pre in [
            ('0.4.16', False, False), ('0.4.17', True, False), ('0.4.18', False, True),
            ('0.4.19-beta', False, False), ('nightly', False, False)]]
        self.assertEqual([r['tag_name'] for r in sync.stable(rows)], ['0.4.16'])

    def test_own_channel_excludes_upstream_and_preserved_old_tag(self):
        rows = [{'tag_name': tag, 'draft': False, 'prerelease': False}
                for tag in ['0.4.15', '0.4.14-orientation-final', '0.4.15-orientation']]
        self.assertEqual([r['tag_name'] for r in sync.stable(rows, True)], ['0.4.15-orientation'])

    def test_numeric_version_order(self):
        self.assertGreater(sync.version('0.4.10'), sync.version('0.4.9'))

    def test_ambiguous_version_code_rejected(self):
        with self.assertRaises(RuntimeError):
            sync.metadata('MARKETING_VERSION = 0.4.16\nCURRENT_PROJECT_VERSION = 122\nCURRENT_PROJECT_VERSION = 123')

    def test_version_metadata(self):
        self.assertEqual(sync.metadata('MARKETING_VERSION = 0.4.16\nCURRENT_PROJECT_VERSION = 122\n'), ('0.4.16', 122))

    def test_failed_apk_verification_prevents_publication(self):
        plan = {'baseline': False, 'version': '0.4.16'}
        with patch.object(sync, 'load_plan', return_value=plan), \
             patch.object(sync.tests, 'validate', return_value={}), \
             patch.object(sync.release, 'verify', side_effect=RuntimeError('wrong signer')), \
             patch.object(sync, 'git') as git, patch.object(sync.release, 'publish') as publish:
            with self.assertRaises(RuntimeError):
                sync.publish(Path('.'), Path('plan.json'), Path('app.apk'))
            git.assert_not_called()
            publish.assert_not_called()

    def test_retagged_upstream_prevents_publication(self):
        plan = {'baseline': False, 'version': '0.4.16', 'upstream_commit': 'expected'}
        rows = [{'tag_name': '0.4.16', 'draft': False, 'prerelease': False}]
        with patch.object(sync, 'load_plan', return_value=plan), \
             patch.object(sync.tests, 'validate', return_value={}), \
             patch.object(sync.release, 'verify', return_value={}), \
             patch.object(sync, 'list_releases', return_value=rows), \
             patch.object(sync, 'git', side_effect=['', 'moved']) as git, \
             patch.object(sync.release, 'publish') as publish:
            with self.assertRaisesRegex(RuntimeError, 'tag moved'):
                sync.publish(Path('.'), Path('plan.json'), Path('app.apk'))
            publish.assert_not_called()
            self.assertFalse(any(c.args[0] == 'push' for c in git.call_args_list))

    def test_baseline_can_never_publish(self):
        with patch.object(sync, 'load_plan', return_value={'baseline': True}), \
             patch.object(sync.release, 'verify') as verify:
            with self.assertRaises(RuntimeError):
                sync.publish(Path('.'), Path('plan.json'), Path('app.apk'))
            verify.assert_not_called()

    def test_disabled_issues_preserve_actionable_failure_summary(self):
        with tempfile.TemporaryDirectory() as d:
            summary = Path(d) / 'summary.md'
            with patch.dict(os.environ, GITHUB_RUN_ID='123', GITHUB_STEP_SUMMARY=str(summary)), \
                 patch.object(sync.release, 'run', return_value='{"has_issues":false}'), \
                 patch.object(sync.release, 'api') as api:
                sync.report_failure()
                api.assert_not_called()
                self.assertIn('actions/runs/123', summary.read_text())

    def test_current_release_does_not_build_or_duplicate_publish(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            plan = Path(d) / 'plan.json'
            rows = [{'tag_name':'0.4.16', 'draft':False, 'prerelease':False}]
            with patch.object(sync,'config',return_value={}), patch.object(sync,'current_release',return_value=('0.4.16',121,'current')), patch.object(sync,'list_releases',return_value=rows), patch.object(sync,'git') as git, patch.object(sync.release,'publish') as publish:
                sync.prepare(Path(d)/'source',plan)
                self.assertEqual(json.loads(plan.read_text())['status'],'up-to-date')
                git.assert_not_called(); publish.assert_not_called()

    def test_failed_test_or_build_evidence_prevents_all_publication(self):
        with patch.object(sync,'load_plan',return_value={'baseline':False}), patch.object(sync.tests,'validate',side_effect=RuntimeError('failed build')), patch.object(sync.release,'verify') as verify, patch.object(sync.release,'publish') as publish, patch.object(sync,'git') as git:
            with self.assertRaises(RuntimeError): sync.publish(Path('.'),Path('plan'),Path('apk'),Path('evidence'))
            verify.assert_not_called(); publish.assert_not_called(); git.assert_not_called()

    def test_canonical_patch_matches_saved_reviewed_source(self):
        m = sync.config()
        self.assertEqual(m['base_tag'], '0.4.16')
        self.assertEqual(sync.reproduced_tree(m,m['base_commit']),sync.git('rev-parse',m['orientation_commit']+'^{tree}'))
        self.assertIn('androidApp/build.gradle.kts', m['delta_paths'])


if __name__ == '__main__':
    unittest.main()
