#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
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

    def test_player_change_is_blocked_even_without_textual_overlap(self):
        p = 'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/NewPlayerEngine.kt'
        self.assertEqual(sync.unsafe_paths([p], []), [p])

    def test_each_sensitive_change_is_blocked(self):
        paths = ['.github/workflows/build.yml', 'composeApp/build.gradle.kts', 'gradle/libs.versions.toml',
                 'androidApp/src/main/AndroidManifest.xml', 'scripts/build.sh', 'composeApp/libs/player.aar',
                 'composeApp/src/androidMain/kotlin/MainActivity.kt',
                 'composeApp/src/commonMain/kotlin/com/nuvio/app/features/updater/AppUpdater.kt',
                 'composeApp/src/commonMain/kotlin/com/nuvio/app/features/profiles/Profile.kt']
        self.assertEqual(sync.unsafe_paths(paths, []), paths)

    def test_any_canonical_overlap_is_blocked(self):
        p = 'composeApp/src/commonMain/kotlin/HomeHeroSection.kt'
        self.assertEqual(sync.unsafe_paths([p], [p]), [p])

    def test_unrelated_features_and_version_change_can_proceed(self):
        self.assertEqual(sync.unsafe_paths(['composeApp/src/commonMain/kotlin/features/search/Search.kt',
                                           'iosApp/Configuration/Version.xcconfig', 'README.md'], []), [])

    def test_ambiguous_version_code_rejected(self):
        with self.assertRaises(RuntimeError):
            sync.metadata('MARKETING_VERSION = 0.4.16\nCURRENT_PROJECT_VERSION = 122\nCURRENT_PROJECT_VERSION = 123')

    def test_version_metadata(self):
        self.assertEqual(sync.metadata('MARKETING_VERSION = 0.4.16\nCURRENT_PROJECT_VERSION = 122\n'), ('0.4.16', 122))

    def test_failed_apk_verification_prevents_publication(self):
        plan = {'baseline': False, 'version': '0.4.16'}
        with patch.object(sync, 'load_plan', return_value=plan), \
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

    def test_canonical_patch_matches_saved_reviewed_source(self):
        m = sync.config()
        self.assertEqual(m['base_tag'], '0.4.15')
        self.assertIn('androidApp/build.gradle.kts', m['delta_paths'])


if __name__ == '__main__':
    unittest.main()
