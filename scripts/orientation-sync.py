#!/usr/bin/env python3
"""Integrate exact stable upstream tags; stop before signing on unsafe changes."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('release', ROOT / 'scripts/orientation-release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
MANIFEST = ROOT / 'orientation/manifest.json'
UPSTREAM = 'luqmanfadlli/NuvioMobile-Enhanced'
REPO = release.REPO


def git(*args, cwd=ROOT, env=None):
    return release.run('git', *args, cwd=cwd, env=env).strip()


def require(test, message):
    release.require(test, message)


def version(tag):
    require(bool(re.fullmatch(r'\d+\.\d+\.\d+', tag)), 'Not a stable numeric version')
    return tuple(map(int, tag.split('.')))


def stable(releases, orientation=False):
    suffix = '-orientation' if orientation else ''
    pattern = r'\d+\.\d+\.\d+' + suffix
    return [r for r in releases if not r['draft'] and not r['prerelease']
            and re.fullmatch(pattern, r['tag_name'])]


def list_releases(repository):
    result = []
    for page in range(1, 101):
        rows = json.loads(release.run('gh', 'api', f'repos/{repository}/releases?per_page=100&page={page}'))
        result.extend(rows)
        if len(rows) < 100:
            return result
    raise RuntimeError('Release listing exceeded its limit; refusing an incomplete history')


def config():
    m = json.loads(MANIFEST.read_text())
    require(m['schema'] == 1 and m['upstream_repository'] == UPSTREAM, 'Unexpected manifest')
    require(m['package'] == 'com.nuvio.media' and m['certificate_sha256'] == release.CERT,
            'Canonical identity changed')
    patch = ROOT / 'orientation/canonical.patch'
    require(hashlib.sha256(patch.read_bytes()).hexdigest() == m['patch_sha256'], 'Canonical patch changed')
    require(git('rev-parse', m['orientation_commit'] + '^' + '{commit}') == m['orientation_commit'],
            'Canonical source unavailable')
    exact = subprocess.check_output(['git', 'diff', '--binary', '--full-index', m['base_commit'],
                                     m['orientation_commit']], cwd=ROOT)
    require(exact == patch.read_bytes(), 'Patch differs from the reviewed canonical source delta')
    require(git('diff', '--name-only', m['base_commit'], m['orientation_commit']).splitlines()
            == m['delta_paths'], 'Canonical file list changed')
    return m


def metadata(text):
    names = re.findall(r'^MARKETING_VERSION\s*=\s*(\d+\.\d+\.\d+)\s*$', text, re.M)
    codes = re.findall(r'^CURRENT_PROJECT_VERSION\s*=\s*(\d+)\s*$', text, re.M)
    require(len(names) == len(codes) == 1, 'Ambiguous version metadata')
    return names[0], int(codes[0])


def unsafe_paths(paths, delta_paths):
    """Conservative: textual merge success cannot establish player compatibility."""
    bad = []
    for p in paths:
        if p == 'iosApp/Configuration/Version.xcconfig':
            continue
        sensitive = (p in delta_paths or p.startswith(('.github/', 'gradle/', 'buildSrc/', 'scripts/'))
                     or p in ('gradlew', 'gradlew.bat', 'gradle.properties', '.gitattributes', '.gitmodules')
                     or p.endswith(('.gradle', '.gradle.kts', 'AndroidManifest.xml', '.aar', '.jar', '.so', '.c', '.cpp', '.h'))
                     or re.search(r'/(player|updater|profiles)/', p)
                     or re.search(r'(MainActivity|PlayerSettings|GenerateRuntimeConfig|AppFeaturePolicy|AppVersionConfig)', p))
        if sensitive:
            bad.append(p)
    return bad


def check_upstream(m, target):
    require(subprocess.run(['git', 'merge-base', '--is-ancestor', m['base_commit'], target], cwd=ROOT).returncode == 0,
            'Upstream history does not descend from the canonical baseline')
    changed = git('diff', '--name-only', m['base_commit'], target).splitlines()
    bad = unsafe_paths(changed, m['delta_paths'])
    require(not bad, 'Upstream changes require Orientation review:\n' + '\n'.join(bad))
    path = 'iosApp/Configuration/Version.xcconfig'
    before = git('show', m['base_commit'] + ':' + path)
    after = git('show', target + ':' + path)
    strip = lambda s: re.sub(r'^(MARKETING_VERSION|CURRENT_PROJECT_VERSION)\s*=.*$', '', s, flags=re.M)
    require(strip(before) == strip(after), 'Version configuration changed beyond version numbers')


def current_release(m):
    releases = stable(list_releases(REPO), orientation=True)
    require(releases, 'Publish and verify 0.4.15 Orientation before enabling future releases')
    newest = max(releases, key=lambda r: version(r['tag_name'].removesuffix('-orientation')))
    v = newest['tag_name'].removesuffix('-orientation')
    record_match = re.search(r'```json\s*(\{.*?\})\s*```', newest.get('body') or '', re.S)
    require(record_match is not None, 'Current release lacks verification metadata')
    record = json.loads(record_match.group(1))
    require(record['package'] == m['package'] and record['signer_sha256'] == release.CERT
            and record['versionName'] == v and record['abi'] == 'arm64-v8a', 'Current release identity mismatch')
    tag = release.api('git/ref/tags/' + newest['tag_name'])
    require(tag['object']['type'] == 'commit' and tag['object']['sha'] == record['commit'], 'Current release tag moved')
    expected_name = f'Nuvio-Enhanced-{v}-Orientation-Full-arm64-v8a.apk'
    require(len([a for a in newest['assets'] if a['name'] == expected_name and a['state'] == 'uploaded']) == 1,
            'Current release APK is missing')
    return v, record['versionCode'], record['commit']


def prepare(source, plan_path, baseline=False):
    m = config()
    old_version, old_code, old_commit = current_release(m)
    releases = stable(list_releases(UPSTREAM))
    if baseline:
        selected = next(r for r in releases if r['tag_name'] == m['base_tag'])
    else:
        newer = [r for r in releases if version(r['tag_name']) > version(old_version)]
        if not newer:
            plan_path.write_text(json.dumps({'status': 'up-to-date'}, indent=2) + '\n')
            print('No newer stable upstream release.')
            return
        selected = min(newer, key=lambda r: version(r['tag_name']))
    v = selected['tag_name']
    git('fetch', '--no-tags', 'https://github.com/' + UPSTREAM + '.git', 'refs/tags/' + v)
    target = git('rev-parse', 'FETCH_HEAD^{commit}')
    if baseline:
        require(target == m['base_commit'], 'Canonical upstream tag moved')
    check_upstream(m, target)
    v_name, code = metadata(git('show', target + ':iosApp/Configuration/Version.xcconfig'))
    require(v == v_name and (baseline or code > old_code), 'Version does not match tag or cannot update installed app')
    require(not source.exists(), 'Candidate directory already exists')
    git('worktree', 'add', '--detach', str(source), target)
    git('apply', '--index', '--3way', str(ROOT / 'orientation/canonical.patch'), cwd=source)
    require(git('diff', '--cached', '--name-only', cwd=source).splitlines() == m['delta_paths'], 'Unexpected integrated delta')
    # Every original upstream file outside the reviewed delta remains exact.
    env = os.environ.copy()
    env.update(GIT_AUTHOR_NAME='Orientation automation', GIT_AUTHOR_EMAIL='orientation@users.noreply.github.com',
               GIT_COMMITTER_NAME='Orientation automation', GIT_COMMITTER_EMAIL='orientation@users.noreply.github.com')
    git('commit', '-m', f'Apply canonical Orientation delta to exact upstream {v}', cwd=source, env=env)
    candidate = git('rev-parse', 'HEAD', cwd=source)
    require(git('rev-parse', 'HEAD^', cwd=source) == target, 'Candidate is not based on exact upstream tag')
    if baseline:
        require(git('rev-parse', 'HEAD^{tree}', cwd=source) == git('rev-parse', m['orientation_commit'] + '^{tree}'),
                'Baseline replay did not reproduce the reviewed candidate tree')
    plan = {'status': 'ready', 'baseline': baseline, 'version': v, 'version_code': code,
            'upstream_commit': target, 'commit': candidate, 'previous_commit': old_commit,
            'previous_version': old_version, 'patch_sha256': m['patch_sha256']}
    plan_path.write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps(plan, indent=2))


def load_plan(source, path):
    m = config()
    plan = json.loads(path.read_text())
    require(plan['status'] == 'ready' and plan['patch_sha256'] == m['patch_sha256'], 'Invalid build plan')
    require(git('rev-parse', 'HEAD', cwd=source) == plan['commit'], 'Candidate moved during the run')
    require(git('rev-parse', 'HEAD^', cwd=source) == plan['upstream_commit'], 'Candidate parent changed')
    require(not git('status', '--porcelain', '--untracked-files=no', cwd=source), 'Candidate tracked files changed')
    check_upstream(m, plan['upstream_commit'])
    require(git('diff', '--name-only', 'HEAD^', 'HEAD', cwd=source).splitlines() == m['delta_paths'], 'Candidate delta changed')
    release.BUILDS[plan['version']] = (plan['commit'], plan['version_code'], plan['version'] + '-orientation')
    return plan


def publish(source, plan_path, apk):
    plan = load_plan(source, plan_path)
    require(not plan['baseline'], 'Baseline dry run cannot publish')
    record = release.verify(source, plan['version'], apk)
    upstream = [r for r in stable(list_releases(UPSTREAM)) if r['tag_name'] == plan['version']]
    require(len(upstream) == 1, 'Upstream release was removed or is no longer stable')
    git('fetch', '--no-tags', 'https://github.com/' + UPSTREAM + '.git', 'refs/tags/' + plan['version'])
    require(git('rev-parse', 'FETCH_HEAD^{commit}') == plan['upstream_commit'], 'Upstream tag moved during the build')
    _, _, current = current_release(config())
    require(current == plan['previous_commit'], 'Another release was published; start from its state')
    current_ref = release.api('git/ref/heads/orientation-current', optional=True)
    require(current_ref is None or current_ref['object']['sha'] == plan['previous_commit'],
            'orientation-current differs from the previous verified release')
    # Upload tested source before publication, using a new immutable candidate branch.
    branch = 'orientation-candidates/' + plan['version'] + '-' + plan['commit'][:12]
    git('push', 'origin', plan['commit'] + ':refs/heads/' + branch)
    release.publish(source, plan['version'], apk)
    published = release.api('releases/tags/' + plan['version'] + '-orientation')
    # Publication has already verified the actual remote APK before making it visible.
    require(not published['draft'], 'Release was not published')
    current_ref = release.api('git/ref/heads/orientation-current', optional=True)
    if current_ref:
        require(current_ref['object']['sha'] == plan['previous_commit'], 'orientation-current advanced unexpectedly')
        git('push', '--force-with-lease=refs/heads/orientation-current:' + plan['previous_commit'],
            'origin', plan['commit'] + ':refs/heads/orientation-current')
    else:
        git('push', 'origin', plan['commit'] + ':refs/heads/orientation-current')
    print(json.dumps(record, indent=2))


def report_failure():
    title = 'Orientation integration requires review'
    issues = release.api('issues?state=open&per_page=100')
    if any(i['title'] == title for i in issues):
        return
    url = f"https://github.com/{REPO}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    release.api('issues', '--method', 'POST', '-f', 'title=' + title, '-f', 'body=' +
                'The automatic integration stopped before publishing an unsafe update. '
                'The previous working release is preserved. Inspect the failed gate and test reports: ' + url)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare', 'verify', 'publish', 'report'])
    p.add_argument('--source', type=Path)
    p.add_argument('--plan', type=Path)
    p.add_argument('--apk', type=Path)
    p.add_argument('--baseline', action='store_true')
    a = p.parse_args()
    if a.action == 'report':
        report_failure()
    elif a.action == 'prepare':
        prepare(a.source.resolve(), a.plan.resolve(), a.baseline)
    elif a.action == 'verify':
        plan = load_plan(a.source, a.plan)
        print(json.dumps(release.verify(a.source, plan['version'], a.apk), indent=2))
    else:
        publish(a.source, a.plan, a.apk)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError:
        sys.exit('An integration command failed; no unverified release is published.')
    except (RuntimeError, ValueError) as e:
        sys.exit(str(e))
