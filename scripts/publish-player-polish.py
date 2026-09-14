#!/usr/bin/env python3
"""Publish only the APK associated with a successful exact-source verification run."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

REPO = 'Mindplayer99/NuvioMobile-Enhanced'
VERSION = '0.4.17-ui.2'
TAG = '0.4.17-orientation-ui.2'

def run(*args, cwd=None):
    return subprocess.check_output(args, text=True, cwd=cwd).strip()

def require(value, message):
    if not value:
        raise RuntimeError(message)

def main():
    require(os.environ['GITHUB_REPOSITORY'] == REPO, 'Wrong repository')
    sha = os.environ['VERIFIED_SOURCE_SHA']
    run_id = os.environ['VERIFIED_RUN_ID']
    job = json.loads(run('gh', 'api', f'repos/{REPO}/actions/runs/{run_id}'))
    require(job['status'] == 'completed' and job['conclusion'] == 'success'
            and job['head_sha'] == sha and job['head_branch'] == 'feature/orientation-ui-polish'
            and job['path'] == '.github/workflows/ui-polish.yml', 'Unverified source/run')
    folder = Path(os.environ['RUNNER_TEMP']) / 'verified-ui-artifact'
    run('gh', 'run', 'download', run_id, '--repo', REPO, '--name', 'orientation-ui-polish-' + sha, '--dir', str(folder))
    records = list(folder.rglob('verification.json'))
    apks = list(folder.rglob('*.apk'))
    require(len(records) == 1 and len(apks) == 1, 'Ambiguous build artifacts')
    record = json.loads(records[0].read_text())
    require(record['commit'] == sha and record['new_failures'] == 0
            and record['ui_tests'] >= 141 and record['critical_tests'] >= 123,
            'Invalid or incomplete verification evidence')
    require(record['baseline'] == '530f4cb483f8d211ddd7c5365ca7c516a9b69ad0', 'Wrong comparison baseline')
    spec = importlib.util.spec_from_file_location('release', Path('release-tools/scripts/orientation-release.py'))
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    release.BUILDS[VERSION] = (sha, 122, TAG)
    checked = release.verify(Path('candidate').resolve(), VERSION, apks[0])
    require(all(record[k] == v for k, v in checked.items()), 'APK differs from build evidence')
    notes = records[0].with_name('release-notes.md')
    require(notes.is_file(), 'Missing release notes')
    existing = subprocess.run(['gh', 'release', 'view', TAG, '--repo', REPO], capture_output=True)
    require(existing.returncode != 0, 'Existing release must not be overwritten')
    run('gh', 'release', 'create', TAG, '--repo', REPO, '--target', sha,
        '--title', 'Nuvio Enhanced 0.4.17 Orientation — UI update 2',
        '--notes-file', str(notes), '--draft', '--prerelease', '--latest=false')
    run('gh', 'release', 'upload', TAG, '--repo', REPO, str(apks[0]), str(records[0]))
    remote_folder = Path(os.environ['RUNNER_TEMP']) / 'remote-ui-apk'
    run('gh', 'release', 'download', TAG, '--repo', REPO, '--pattern', apks[0].name, '--dir', str(remote_folder))
    remote_apk = remote_folder / apks[0].name
    require(hashlib.sha256(remote_apk.read_bytes()).hexdigest() == record['apk_sha256'], 'Uploaded APK hash mismatch')
    require(release.verify(Path('candidate').resolve(), VERSION, remote_apk) == checked,
            'Remote package/version/ABI/signer verification failed')
    run('gh', 'release', 'edit', TAG, '--repo', REPO, '--draft=false', '--latest=false')
    print(run('gh', 'release', 'view', TAG, '--repo', REPO, '--json', 'url,assets'))
    print(json.dumps(record, indent=2))

if __name__ == '__main__':
    main()
