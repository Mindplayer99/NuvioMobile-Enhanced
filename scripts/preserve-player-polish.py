#!/usr/bin/env python3
"""Carry verified UI runtime into the canonical numeric upstream integration baseline."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

TOOLS = '3799ecdd1cf2478c71fb0efd133e26236fc7ac5c'
BASE = '8457cbf009a0453f709ff787f09ef03e858b50c1'
REPO = 'Mindplayer99/NuvioMobile-Enhanced'

def git(*args, env=None):
    return subprocess.check_output(['git', *args], text=True, env=env).strip()

def require(value, message):
    if not value: raise RuntimeError(message)

def main():
    os.chdir('release-tools')
    source = os.environ['VERIFIED_SOURCE_SHA']
    require(git('rev-parse', 'HEAD') == TOOLS, 'Automation head changed')
    git('fetch', 'origin', source, 'enhanced')
    require(git('rev-parse', 'origin/enhanced') == TOOLS, 'Production automation advanced')
    git('fetch', '--no-tags', 'https://github.com/luqmanfadlli/NuvioMobile-Enhanced.git', 'refs/tags/0.4.17')
    require(git('rev-parse', 'FETCH_HEAD^{commit}') == BASE, 'Upstream 0.4.17 identity changed')
    git('config', 'user.name', 'Orientation automation')
    git('config', 'user.email', 'orientation@users.noreply.github.com')
    release = json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/0.4.17-orientation-ui.2'], text=True))
    require(not release['draft'] and release['target_commitish'] == source, 'UI release not published from reviewed source')
    exclusions = ['.github/workflows/ui-polish.yml','scripts/verify-ui-polish.py','UI_POLISH.md','iosApp/Configuration/Version.xcconfig']
    with tempfile.TemporaryDirectory() as t:
        env = os.environ.copy(); env['GIT_INDEX_FILE'] = t + '/index'
        git('read-tree', source, env=env)
        for path in exclusions[:3]: git('update-index','--force-remove',path,env=env)
        version_blob = git('rev-parse', BASE + ':iosApp/Configuration/Version.xcconfig')
        git('update-index','--cacheinfo','100644,'+version_blob+',iosApp/Configuration/Version.xcconfig',env=env)
        tree = git('write-tree',env=env)
        canonical = git('commit-tree',tree,'-p',BASE,'-m','Canonical 0.4.17 Orientation with verified Search and player polish')
    require(set(git('diff','--name-only',source,canonical).splitlines()) == set(exclusions),
            'Canonical runtime differs from verified release')
    patch = subprocess.check_output(['git','diff','--binary','--full-index',BASE,canonical])
    Path('orientation/canonical.patch').write_bytes(patch)
    manifest = json.loads(Path('orientation/manifest.json').read_text())
    manifest.update(base_tag='0.4.17',base_commit=BASE,orientation_commit=canonical,
                    initial_version_code=122,patch_sha256=hashlib.sha256(patch).hexdigest(),
                    delta_paths=git('diff','--name-only',BASE,canonical).splitlines(),
                    verified_ui_source=source,verified_ui_run=os.environ['VERIFIED_RUN_ID'],
                    canonical_exclusions=exclusions)
    Path('orientation/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    p=Path('scripts/test-orientation-sync.py')
    p.write_text(p.read_text().replace("self.assertEqual(m['base_tag'], '0.4.16')","self.assertEqual(m['base_tag'], '0.4.17')"))
    for script in ['test-orientation-release.py','test-orientation-sync.py','test-orientation-risk.py','test-orientation-tests.py']:
        subprocess.check_call(['python3','scripts/'+script])
    # Baseline must reproduce the exact reviewed runtime, with numeric upstream metadata.
    subprocess.check_call(['python3','scripts/orientation-sync.py','prepare','--baseline',
                           '--source',os.environ['RUNNER_TEMP']+'/ui-canonical-reproduced',
                           '--plan',os.environ['RUNNER_TEMP']+'/ui-canonical-plan.json'])
    # Rehearse the next upstream without building or publishing it. A semantic hard block
    # is recorded for later review; unrelated infrastructure failures remain fatal.
    risk_path = Path(os.environ['RUNNER_TEMP'])/'orientation-risk.json'
    risk_path.unlink(missing_ok=True)
    future = subprocess.run(['python3','scripts/orientation-sync.py','prepare',
                             '--source',os.environ['RUNNER_TEMP']+'/ui-future-candidate',
                             '--plan',os.environ['RUNNER_TEMP']+'/ui-future-plan.json'])
    hard = []
    if risk_path.exists():
        hard = [row for row in json.loads(risk_path.read_text())['changes'] if row['risk']=='hard']
    require(future.returncode == 0 or hard, 'Future dry-run failed for an unexplained reason')
    print('FUTURE_UPSTREAM_HARD_BLOCKS',json.dumps([dict(path=r['path'],reasons=r['reasons']) for r in hard]))
    git('push','origin',canonical+':refs/heads/orientation-canonical/0.4.17-ui2')
    git('add','orientation/manifest.json','orientation/canonical.patch','scripts/test-orientation-sync.py')
    git('commit','-m','Preserve verified player and Search polish in 0.4.17 canonical baseline')
    new_head=git('rev-parse','HEAD')
    # The same release concurrency group guards this workflow and hourly integration.
    git('push','--force-with-lease=refs/heads/enhanced:'+TOOLS,'origin',new_head+':refs/heads/enhanced')
    print(json.dumps(dict(automation_commit=new_head,canonical_commit=canonical,base=BASE,
                          patch_sha256=manifest['patch_sha256'],runtime_matches_verified_ui=True),indent=2))
if __name__ == '__main__': main()
