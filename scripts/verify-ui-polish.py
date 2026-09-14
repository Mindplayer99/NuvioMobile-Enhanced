#!/usr/bin/env python3
"""Build the focused UI update and compare every existing test against its parent release."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

BASELINE = '530f4cb483f8d211ddd7c5365ca7c516a9b69ad0'
VERSION = '0.4.17-ui.2'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--tools', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    source = Path.cwd()
    baseline = args.baseline.resolve()
    report = args.report.resolve()
    report.mkdir(parents=True, exist_ok=True)
    tests = load('orientation_tests', args.tools.resolve() / 'scripts/orientation-tests.py')
    release = tests.release
    sha = release.run('git', 'rev-parse', 'HEAD', cwd=source).strip()
    release.require(release.run('git', 'rev-parse', 'HEAD', cwd=baseline).strip() == BASELINE,
                    'Wrong baseline release')
    release.run('git', 'merge-base', '--is-ancestor', BASELINE, sha, cwd=source)
    # Reviewed UI and subtitle presentation changes only; decoding, storage and identity are protected.
    changed = release.run('git', 'diff', '--name-only', BASELINE, sha, cwd=source).splitlines()
    allowed = (
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/',
        'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/search/',
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/SettingsSearch.kt',
        'composeApp/src/commonMain/composeResources/values/strings.xml',
        'composeApp/src/commonMain/composeResources/values/search_polish.xml',
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/SubtitleModal.kt',
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/CompactPlayerTrackSheet.kt',
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerOverlayScaffold.kt',
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/AudioTrackModal.kt',
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerControls.kt',
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerPlaybackOverlays.kt',
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeUi.kt',
        'composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/PlayerEngine.android.kt',
        'composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/PortraitSubtitleViewport.android.kt',
        'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/player/PlayerPolishLayoutTest.kt',
        'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/player/PortraitSubtitleViewportTest.kt',
        'iosApp/Configuration/Version.xcconfig',
        '.github/workflows/ui-polish.yml', 'scripts/verify-ui-polish.py', 'UI_POLISH.md',
    )
    release.require(all(any(p.startswith(a) for a in allowed) for p in changed),
                    'Unexpected changes outside the reviewed UI scope')

    # Fail early on the changed UI before spending time on full baseline comparison.
    ui = tests.run_tasks(source, [tests.TASK], report, 'ui',
                         ['--tests', 'com.nuvio.app.features.search.SearchBrowseLayoutTest',
                          '--tests', 'com.nuvio.app.features.player.*',
                          '--tests', 'com.nuvio.app.features.updater.*',
                          '--tests', 'com.nuvio.app.features.downloads.*'])
    release.require(len(ui) >= 18 and all(v['status'] == 'passed' for v in ui.values()),
                    'UI interaction or layout test failed/skipped')
    tests.critical(ui)
    for suite, count in [('SearchBrowseLayoutTest', 8), ('PlayerPolishLayoutTest', 8), ('PortraitSubtitleViewportTest', 2)]:
        release.require(sum('.' + suite + '#' in k for k in ui) >= count, 'Missing focused suite: ' + suite)
    before = tests.run_tasks(baseline, [tests.TASK], report, 'baseline')
    after = tests.run_tasks(source, [tests.TASK, tests.ASSEMBLE], report, 'candidate',
                            ['--continue', '-Pnuvio.android.abis=arm64-v8a'])
    release.require(len(before) >= 900, 'Baseline suite unexpectedly incomplete')
    inherited = tests.compare(after, before)
    release.require(all(after.get(k, {}).get('status') == 'passed' for k in ui),
                    'UI tests did not pass in the full suite')
    apks = list((source / 'androidApp/build/outputs/apk/full/release').glob('*.apk'))
    release.require(len(apks) == 1, 'Expected exactly one Full ARM64 APK')
    tag = '0.4.17-orientation-ui.2'
    release.BUILDS[VERSION] = (sha, 122, tag)
    record = release.verify(source, VERSION, apks[0])
    # Report presence only. Never write credential values to logs or release artifacts.
    props = dict(line.split('=', 1) for line in (source / 'local.properties').read_text().splitlines()
                 if '=' in line and not line.lstrip().startswith('#'))
    tracking = {
        'trakt_configured': all(props.get(key, '').strip() for key in ('TRAKT_CLIENT_ID', 'TRAKT_CLIENT_SECRET')),
        'simkl_configured': bool(props.get('SIMKL_CLIENT_ID', '').strip()),
        'oauth_device_login_tested': False,
    }
    record.update(tracking=tracking, baseline=BASELINE, baseline_tests=len(before), candidate_tests=len(after),
                  ui_tests=len(ui), critical_tests=tests.critical(after),
                  inherited_failures=inherited, new_failures=0,
                  device_smoke_test='Not run: no physical phone attached',
                  changed_paths=changed)
    (report / 'verification.json').write_text(json.dumps(record, indent=2) + '\n')
    output = report / 'Nuvio-Enhanced-0.4.17-Orientation-UI2-Full-arm64-v8a.apk'
    shutil.copyfile(apks[0], output)
    release.require(hashlib.sha256(output.read_bytes()).hexdigest() == record['apk_sha256'],
                    'Delivery copy mismatch')
    (report / 'release-notes.md').write_text(
        '# Orientation UI update 2\n\n'
        'Built on the existing 0.4.17 Orientation release.\n\n'
        '- Recent searches appear before Discover, with three entries initially and Show all/Show less.\n'
        '- Discover filters stay directly above their results; the Search title stays consistent.\n'
        '- Discover uses the same heading hierarchy as Recent Searches.\n'
        '- Hero catalogs replaces Catalogs Source, including Settings search.\n'
        '- Portrait subtitles: fixed navigation for language/tracks/style and a persistent Off action.\n'
        '- Portrait captions follow the video; landscape caption behavior is preserved.\n'
        '- Full audio labels wrap; track menus hide player controls in both orientations.\n'
        '- Speed feedback clears the measured header; missing tracking configuration is explained.\n'
        '- Orientation policy, decoding, downloads, accounts and profile storage are preserved.\n\n'
        f'Validation: {len(ui)} focused UI and release-critical tests; {len(after)} total tests compared with {len(before)} '
        f'on the untouched installed-release source; {len(inherited)} inherited failures; '
        'zero added failures. Signed, non-debuggable Full ARM64 APK verified against the original signer.\n\n'
        'Physical-device playback and frame-time testing remain outstanding. This is a manual-install '
        'prerelease; the existing automatic release channel is unchanged. Install over the existing '
        'Orientation app; no uninstall or data reset is required. Version code stays 122 so the next '
        'upstream-based release can still update it normally.\n\n'
        f'Tracking configuration availability: {tracking}. No OAuth connection test was performed.\n\n'
        f'Source: `{sha}`\n\nAPK SHA-256: `{record["apk_sha256"]}`\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
