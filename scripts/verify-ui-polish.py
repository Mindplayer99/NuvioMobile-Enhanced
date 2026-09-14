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
VERSION = '0.4.17-ui.1'


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
    # This update has no reason to touch playback, downloads, profiles, account sync, or dependencies.
    changed = release.run('git', 'diff', '--name-only', BASELINE, sha, cwd=source).splitlines()
    allowed = (
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/',
        'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/search/',
        'composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/SettingsSearch.kt',
        'composeApp/src/commonMain/composeResources/values/strings.xml',
        'composeApp/src/commonMain/composeResources/values/search_polish.xml',
        'iosApp/Configuration/Version.xcconfig',
        '.github/workflows/ui-polish.yml', 'scripts/verify-ui-polish.py', 'UI_POLISH.md',
    )
    release.require(all(any(p.startswith(a) for a in allowed) for p in changed),
                    'Unexpected changes outside the reviewed UI scope')

    # Fail early on the changed UI before spending time on full baseline comparison.
    ui = tests.run_tasks(source, [tests.TASK], report, 'ui',
                         ['--tests', 'com.nuvio.app.features.search.SearchBrowseLayoutTest'])
    release.require(len(ui) >= 8 and all(v['status'] == 'passed' for v in ui.values()),
                    'UI interaction or layout test failed/skipped')
    before = tests.run_tasks(baseline, [tests.TASK], report, 'baseline')
    after = tests.run_tasks(source, [tests.TASK, tests.ASSEMBLE], report, 'candidate',
                            ['--continue', '-Pnuvio.android.abis=arm64-v8a'])
    release.require(len(before) >= 900, 'Baseline suite unexpectedly incomplete')
    inherited = tests.compare(after, before)
    release.require(all(after.get(k, {}).get('status') == 'passed' for k in ui),
                    'UI tests did not pass in the full suite')
    apks = list((source / 'androidApp/build/outputs/apk/full/release').glob('*.apk'))
    release.require(len(apks) == 1, 'Expected exactly one Full ARM64 APK')
    tag = '0.4.17-orientation-ui.1'
    release.BUILDS[VERSION] = (sha, 122, tag)
    record = release.verify(source, VERSION, apks[0])
    record.update(baseline=BASELINE, baseline_tests=len(before), candidate_tests=len(after),
                  ui_tests=len(ui), critical_tests=tests.critical(after),
                  inherited_failures=inherited, new_failures=0,
                  device_smoke_test='Not run: no physical phone attached',
                  changed_paths=changed)
    (report / 'verification.json').write_text(json.dumps(record, indent=2) + '\n')
    output = report / 'Nuvio-Enhanced-0.4.17-Orientation-UI1-Full-arm64-v8a.apk'
    shutil.copyfile(apks[0], output)
    release.require(hashlib.sha256(output.read_bytes()).hexdigest() == record['apk_sha256'],
                    'Delivery copy mismatch')
    (report / 'release-notes.md').write_text(
        '# Orientation UI update 1\n\n'
        'Built on the existing 0.4.17 Orientation release.\n\n'
        '- Recent searches appear before Discover, with three entries initially and Show all/Show less.\n'
        '- Discover filters stay directly above their results; the Search title stays consistent.\n'
        '- Discover uses the same heading hierarchy as Recent Searches.\n'
        '- Hero catalogs replaces Catalogs Source, including Settings search.\n'
        '- Working orientation, player engines, downloads, accounts and profile storage are preserved.\n\n'
        f'Validation: {len(ui)} UI tests; {len(after)} total tests compared with {len(before)} '
        f'on the untouched installed-release source; {len(inherited)} inherited failures; '
        'zero added failures. Signed, non-debuggable Full ARM64 APK verified against the original signer.\n\n'
        'Physical-device playback and frame-time testing remain outstanding. This is a manual-install '
        'prerelease; the existing automatic release channel is unchanged. Install over the existing '
        'Orientation app; no uninstall or data reset is required. Version code stays 122 so the next '
        'upstream-based release can still update it normally.\n\n'
        f'Source: `{sha}`\n\nAPK SHA-256: `{record["apk_sha256"]}`\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
