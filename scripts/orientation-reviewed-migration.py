#!/usr/bin/env python3
"""One reviewed stable migration; uses the production test and publication gates unchanged."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess

EXPECTED_AUTOMATION = '45a7c30c90289db3a95f4c7cac92b8bf2a01fb82'
EXPECTED_UPSTREAM = '50b9194ce5ba7c06ff3709ec525087fa31ce4323'
EXPECTED_SOURCE = '1efe80398144e4dc2ea9f84e9c0f3008056e3af5'
spec = importlib.util.spec_from_file_location('sync', Path(__file__).with_name('orientation-sync.py'))
sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'activate'])
    args = parser.parse_args()
    root = Path(os.environ['RUNNER_TEMP'])
    source = root / 'orientation-source'
    plan_path = root / 'orientation-plan.json'
    sync.require(os.environ['GITHUB_REPOSITORY'] == sync.REPO, 'Wrong repository')
    m = sync.config()
    sync.require(m['base_tag'] == '0.4.22' and m['base_commit'] == EXPECTED_UPSTREAM
                 and m['orientation_commit'] == EXPECTED_SOURCE, 'Reviewed source identity changed')
    if args.action == 'prepare':
        sync.git('fetch', 'origin', 'enhanced')
        sync.require(sync.git('rev-parse', 'origin/enhanced') == EXPECTED_AUTOMATION, 'Automation advanced')
        # This exact upstream and the integrated tree have been manually reviewed. Baseline
        # reproduction still proves all source, delta, version and upstream identity checks.
        sync.prepare(source, plan_path, baseline=True)
        plan = json.loads(plan_path.read_text())
        sync.require(plan['commit'] == EXPECTED_SOURCE and plan['version_code'] == 127
                     and plan['previous_version'] == '0.4.17'
                     and plan['previous_commit'] == '530f4cb483f8d211ddd7c5365ca7c516a9b69ad0',
                     'Migration no longer starts at the reviewed release')
        plan.update(status='ready', baseline=False, review='Exact stable 0.4.22 + verified UI3; player exit, updater and Search overlaps integrated')
        plan_path.write_text(json.dumps(plan, indent=2) + '\n')
        sync.load_plan(source, plan_path)
    else:
        plan = sync.load_plan(source, plan_path)
        sync.tests.validate(root / 'orientation-reports/test-evidence.json', plan)
        current_version, _, current = sync.current_release(m)
        sync.require(current_version == '0.4.22' and current == EXPECTED_SOURCE, 'Release not published')
        sync.require(sync.release.api('git/ref/heads/orientation-current')['object']['sha'] == current,
                     'Current branch did not advance after publication')
        paths = ['orientation/manifest.json', 'orientation/canonical.patch',
                 'scripts/orientation-tests.py', 'scripts/test-orientation-tests.py',
                 'scripts/test-orientation-sync.py']
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy(); env['GIT_INDEX_FILE'] = tmp + '/index'
            sync.git('read-tree', EXPECTED_AUTOMATION, env=env)
            for path in paths:
                blob = sync.git('rev-parse', 'HEAD:' + path)
                sync.git('update-index', '--cacheinfo', '100644,' + blob + ',' + path, env=env)
            tree = sync.git('write-tree', env=env)
            sync.git('config', 'user.name', 'Orientation automation')
            sync.git('config', 'user.email', 'orientation@users.noreply.github.com')
            commit = sync.git('commit-tree', tree, '-p', EXPECTED_AUTOMATION,
                              '-m', 'Rebase canonical Orientation and UI fixes onto verified stable 0.4.22')
        sync.git('push', '--force-with-lease=refs/heads/enhanced:' + EXPECTED_AUTOMATION,
                 'origin', commit + ':refs/heads/enhanced')
        sync.prepare(root / 'orientation-reproduced', root / 'orientation-reproduced.json', baseline=True)
        sync.prepare(root / 'orientation-next', root / 'orientation-next.json')
        next_plan = json.loads((root / 'orientation-next.json').read_text())
        print(json.dumps({'automation_commit': commit, 'canonical_commit': current,
                          'baseline': EXPECTED_UPSTREAM, 'patch_sha256': m['patch_sha256'],
                          'next_status': next_plan['status']}, indent=2))

if __name__ == '__main__': main()
