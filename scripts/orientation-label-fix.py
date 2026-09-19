#!/usr/bin/env python3
"""Verify and deliver two presentation fixes; retain the stable upstream version code."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('sync', ROOT/'scripts/orientation-sync.py')
sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
r = sync.release
t = sync.tests
SOURCE = '264594455fae2ccae1bf7ab10c7af66866bdf95d'
BASE = '6545296fb17f2be433ebe2288a23001c54bb8586'
TOOLS_BASE = 'b2369399f4e188c8003a4e511e6d6d5cf1373974'
UPSTREAM = '50b9194ce5ba7c06ff3709ec525087fa31ce4323'
TAG = '0.4.22-orientation-ui.1'
NAME = 'Nuvio-Enhanced-0.4.22-Orientation-UI1-Full-arm64-v8a.apk'
root = Path(os.environ['RUNNER_TEMP'])
source = root/'labels-source'
report = root/'labels-report'
report.mkdir(exist_ok=True)


def verify():
    m = sync.config()
    r.require(m['orientation_commit'] == SOURCE and m['base_commit'] == UPSTREAM, 'Wrong canonical baseline')
    r.require(sync.reproduced_tree(m, UPSTREAM) == sync.git('rev-parse', SOURCE+'^{tree}'), 'Canonical reproduction failed')
    r.require(sync.git('rev-parse', SOURCE+'^') == UPSTREAM, 'Wrong source parent')
    changed = sync.git('diff', '--name-only', BASE, SOURCE).splitlines()
    expected = ['composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/player/PlayerPolishLayoutTest.kt',
                'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerControls.kt',
                'composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/SubtitleModal.kt']
    r.require(changed == expected, 'Unexpected changes outside the two presentation fixes')
    r.require(sync.git('rev-parse','HEAD',cwd=source) == SOURCE, 'Wrong build source')
    # Reuse the immutable, already verified installed-release test measurement, not a waiver.
    release = r.api('releases/tags/0.4.22-orientation')
    r.require(not release['draft'] and not release['prerelease'], 'Baseline release unavailable')
    record = json.loads(release['body'].split('```json')[1].split('```')[0])
    r.require(record['commit'] == BASE and record['tests']['status'] == 'passed' and
              record['apk_sha256'] == '33b4aa360e869cad43cbd479befe00a36c51469ccff8f198b02aee59838f2551', 'Baseline identity changed')
    run = r.api('actions/runs/35463106008')
    r.require(run['head_sha'] == 'b90ac31d80e24635682e5b56e2dd45e4d5d3a43f', 'Baseline measurement changed')
    steps = r.api('actions/jobs/105950384765')['steps']
    r.require(all(next(s for s in steps if s['number'] == n)['conclusion'] == 'success' for n in [9,10]), 'Baseline tests or remote APK verification failed')
    artifact = r.api('actions/artifacts/10590228450')
    r.require(artifact['digest'] == 'sha256:e4945c1b73ece215a750aa99fb32aa37686171b7fd11fac4d170fda8aa1c1bc6' and not artifact['expired'], 'Baseline artifact changed/expired')
    baseline = root/'labels-baseline'
    r.run('gh','run','download','35463106008','--repo',r.REPO,'--name','orientation-0.4.22-evidence','--dir',str(baseline))
    prior = t.results(baseline/'orientation-reports/candidate-xml')
    r.require(len(prior) == 1127, 'Incomplete baseline tests')
    selected = [t.TASK]
    for pattern in t.CRITICAL: selected += ['--tests', '*'+pattern+'*']
    focused = t.run_tasks(source, selected, report, 'critical')
    critical = t.critical(focused)
    current = t.run_tasks(source,[t.TASK,t.ASSEMBLE],report,'candidate',['--continue','-Pnuvio.android.abis=arm64-v8a'])
    inherited = t.compare(current, prior)
    r.require(all(current[k]['status'] == 'passed' for k in focused), 'Focused tests regressed in full suite')
    r.BUILDS['0.4.22'] = (SOURCE,127,TAG)
    apks = list((source/'androidApp/build/outputs/apk/full/release').glob('*.apk'))
    r.require(len(apks) == 1, 'Ambiguous APK')
    result = r.verify(source,'0.4.22',apks[0])
    result.update(critical_tests=critical,candidate_tests=len(current),baseline_tests=len(prior),
                  inherited_failures=inherited,new_failures=0,baseline=BASE,upstream_commit=UPSTREAM,
                  device_smoke_test='Not performed; no physical phone attached')
    (report/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    shutil.copyfile(apks[0],report/NAME)
    print(json.dumps(result,indent=2))


def publish():
    result = json.loads((report/'verification.json').read_text())
    r.require(result['commit'] == SOURCE and result['new_failures'] == 0, 'Invalid build evidence')
    r.BUILDS['0.4.22'] = (SOURCE,127,TAG)
    checked = r.verify(source,'0.4.22',report/NAME)
    r.require(all(result[k] == v for k,v in checked.items()), 'APK differs from evidence')
    r.require(r.api('git/ref/heads/enhanced')['object']['sha'] == TOOLS_BASE, 'Automation advanced; review required')
    r.require(r.api('releases/tags/'+TAG,optional=True) is None and r.api('git/ref/tags/'+TAG,optional=True) is None, 'UI release already exists; never overwrite')
    notes = ('Two presentation fixes on the verified 0.4.22 Orientation build: subtitle language labels stay on one line, and quality controls align with icon buttons in portrait and landscape.\n\n'
             'Manual-install UI update. Same package, signer and version code 127; future stable updates remain installable. No playback, decoder, download or storage changes.\n\n'
             f"{result['critical_tests']} focused tests passed; {result['candidate_tests']} full-suite tests, {len(result['inherited_failures'])} unchanged baseline failures, zero new failures. Physical-device smoke testing was not performed.\n\n"
             'Verification:\n```json\n'+json.dumps(result,indent=2)+'\n```')
    notes_path=report/'release-notes.md';notes_path.write_text(notes)
    r.run('gh','release','create',TAG,'--repo',r.REPO,'--target',SOURCE,'--title','Nuvio Enhanced 0.4.22 Orientation — UI alignment update',
          '--notes-file',str(notes_path),'--draft','--prerelease','--latest=false')
    r.run('gh','release','upload',TAG,'--repo',r.REPO,str(report/NAME),str(report/'verification.json'))
    remote=root/'labels-remote'
    r.run('gh','release','download',TAG,'--repo',r.REPO,'--pattern',NAME,'--dir',str(remote))
    r.require(hashlib.sha256((remote/NAME).read_bytes()).hexdigest() == result['apk_sha256'], 'Remote hash mismatch')
    r.require(r.verify(source,'0.4.22',remote/NAME) == checked, 'Remote APK identity mismatch')
    r.run('gh','release','edit',TAG,'--repo',r.REPO,'--draft=false','--latest=false')
    # Update only the canonical delta. Stable-channel state and its race checks stay unchanged.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        env=os.environ.copy();env['GIT_INDEX_FILE']=tmp+'/index'
        sync.git('read-tree',TOOLS_BASE,env=env)
        for path in ['orientation/manifest.json','orientation/canonical.patch']:
            blob=sync.git('rev-parse','HEAD:'+path)
            sync.git('update-index','--add','--cacheinfo','100644,'+blob+','+path,env=env)
        tree=sync.git('write-tree',env=env)
        env.update(GIT_AUTHOR_NAME='Orientation automation',GIT_AUTHOR_EMAIL='orientation@users.noreply.github.com',
                   GIT_COMMITTER_NAME='Orientation automation',GIT_COMMITTER_EMAIL='orientation@users.noreply.github.com')
        commit=sync.git('commit-tree',tree,'-p',TOOLS_BASE,'-m','Preserve verified language and quality alignment fixes in future Orientation updates',env=env)
    sync.git('push','--force-with-lease=refs/heads/enhanced:'+TOOLS_BASE,'origin',commit+':refs/heads/enhanced')
    sync.prepare(root/'labels-reproduced',report/'canonical-reproduction.json',baseline=True)
    sync.prepare(root/'labels-next',report/'next-update.json')
    print(json.dumps({'automation_commit':commit,'source':SOURCE,'download':'https://github.com/'+r.REPO+'/releases/download/'+TAG+'/'+NAME},indent=2))

if __name__ == '__main__':
    import sys
    (verify if sys.argv[1] == 'verify' else publish)()
