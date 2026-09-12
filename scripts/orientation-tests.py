#!/usr/bin/env python3
"""Critical tests first; shared full-suite/build; per-tag upstream equivalence."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

s = importlib.util.spec_from_file_location('release', Path(__file__).with_name('orientation-release.py'))
release = importlib.util.module_from_spec(s); s.loader.exec_module(release)
TASK = ':composeApp:testAndroidHostTest'
ASSEMBLE = ':androidApp:assembleFullRelease'
CRITICAL = ('.features.player.', '.features.updater.', '.features.downloads.')
REQUIRED = ('PlayerOrientationTest', 'PlayerOrientationAndroidTest', 'OrientationUpdateChannelTest')
FLAGS = ['-Pnuvio.android.distribution=full', '--parallel', '--max-workers=2',
         '-Dorg.gradle.jvmargs=-Xmx4g', '-Pkotlin.daemon.jvmargs=-Xmx2g', '--console=plain', '--no-configuration-cache']


def normalize(failure):
    message = failure.get('message', '')
    message = re.sub(r'(?<=@)[0-9a-fA-F]{6,}\b', '<identity>', message)
    message = re.sub(r'/(?:home/runner|tmp|workspace)/[^\s:]+', '<path>', message)
    frames = re.findall(r'^\s*at (com\.nuvio\.[^\n]+)', failure.text or '', re.M)
    frames = [re.sub(r':\d+\)', ':<line>)', f) for f in frames[:5]]
    return {'type': failure.get('type', ''), 'message': message, 'frames': frames}


def results(folder):
    cases = {}
    for file in sorted(Path(folder).rglob('TEST-*.xml')):
        root = ET.parse(file).getroot()
        for case in root.iter('testcase'):
            identity = case.get('classname', '') + '#' + case.get('name', '')
            release.require(identity not in cases, 'Duplicate test identity: ' + identity)
            failures = list(case.findall('failure')) + list(case.findall('error'))
            cases[identity] = {'status': 'failed' if failures else 'skipped' if case.find('skipped') is not None else 'passed',
                               'failures': [normalize(f) for f in failures]}
    release.require(cases, 'No test XML results; compilation/infrastructure failure is not an inherited test failure')
    return cases


def critical(cases):
    subset = {k:v for k,v in cases.items() if any(p in k for p in CRITICAL)}
    for required in REQUIRED:
        release.require(any('.' + required + '#' in k for k in subset), 'Missing critical suite: ' + required)
    release.require(all(v['status'] == 'passed' for v in subset.values()), 'Critical test failed or skipped')
    return len(subset)


def compare(candidate, upstream):
    critical(candidate)
    for identity, result in upstream.items():
        release.require(identity in candidate, 'Candidate omitted upstream test: ' + identity)
        release.require(candidate[identity]['status'] != 'skipped' or result['status'] == 'skipped', 'Candidate newly skipped test: ' + identity)
    inherited = {}
    for identity, result in candidate.items():
        if result['status'] == 'failed':
            release.require(upstream.get(identity) == result, 'Candidate regression or different failure signature: ' + identity)
            inherited[identity] = result['failures']
    return inherited


def run_tasks(source, tasks, report, label, extra=()):
    xml = source / 'composeApp/build/test-results/testAndroidHostTest'
    shutil.rmtree(xml, ignore_errors=True)
    outcomes = report / (label + '-tasks.jsonl')
    outcomes.unlink(missing_ok=True)
    init = report / (label + '-outcomes.gradle')
    # Public Gradle TaskExecutionGraph API. Configuration cache explicitly disabled.
    init.write_text('''import groovy.json.JsonOutput
def destination = new File(System.getenv('ORIENTATION_TASK_OUTCOMES'))
gradle.taskGraph.afterTask { task, state ->
    synchronized(destination) {
        destination << JsonOutput.toJson([path: task.path, failed: state.failure != null, skipped: state.skipped, noSource: state.noSource]) + '\\n'
    }
}
''')
    env = os.environ.copy(); env['ORIENTATION_TASK_OUTCOMES'] = str(outcomes)
    with (report / (label + '-gradle.log')).open('w') as log:
        process = subprocess.Popen(['./gradlew', *tasks, *FLAGS, '--init-script', str(init), *extra], cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end='', flush=True); log.write(line)
        exit_code = process.wait()
    states = [json.loads(x) for x in outcomes.read_text().splitlines()] if outcomes.exists() else []
    failed_tasks = [x['path'] for x in states if x['failed']]
    release.require(not set(failed_tasks) - {TASK}, 'Compilation/build/infrastructure task failed: ' + ', '.join(failed_tasks))
    test_state = next((x for x in states if x['path'] == TASK), None)
    release.require(test_state is not None and not test_state['noSource'], 'Host suite did not complete')
    cases = results(xml)
    failures = any(v['status'] == 'failed' for v in cases.values())
    release.require(test_state['failed'] == failures and (exit_code == 0) == (not failures), 'Gradle exit/task/XML evidence disagrees')
    if ASSEMBLE in tasks:
        release.require(any(x['path'] == ASSEMBLE and not x['failed'] for x in states), 'Full release assembly did not complete')
    release.require(not release.run('git','status','--porcelain','--untracked-files=no',cwd=source).strip(), 'Build modified tracked source')
    shutil.copytree(xml, report / (label + '-xml'), dirs_exist_ok=True)
    return cases


def artifact_results(run_id, commit, report):
    # Only reuse the explicitly reviewed first-migration measurement, not a cross-version waiver.
    release.require(run_id == '34640006876' and commit == 'fdc8d77a6594d4eeb5c2129b379dab85c2d2d8ac', 'Unrecognized upstream measurement')
    info = release.api('actions/runs/' + run_id)
    release.require(info['status'] == 'completed' and info['conclusion'] == 'success'
                    and info['head_sha'] == '3d4c3e931082d87c81f7a415ebc36142229c328a', 'Upstream measurement run is not the pinned successful diagnostic')
    destination = report / 'raw-artifact'
    release.run('gh','run','download',run_id,'--repo',release.REPO,'--name','exact-upstream-0.4.16-tests','--dir',str(destination))
    metadata = json.loads(next(destination.rglob('upstream-result.json')).read_text())
    release.require(metadata['commit'] == commit and metadata['tracked_source_unchanged'] is True, 'Raw upstream source evidence mismatch')
    log = next(destination.rglob('upstream-gradle.log')).read_text()
    cases = results(destination)
    failures = any(v['status'] == 'failed' for v in cases.values())
    failed_tasks = re.findall(r'^> Task (\S+) FAILED$', log, re.M)
    release.require(failed_tasks == ([TASK] if failures else []) and metadata['gradle_exit'] == (1 if failures else 0)
                    and ('BUILD FAILED' if failures else 'BUILD SUCCESSFUL') in log, 'Raw upstream build did not complete its host suite')
    return cases


def gate(source, plan_path, report, upstream_run=None):
    plan = json.loads(plan_path.read_text())
    report.mkdir(parents=True, exist_ok=True)
    evidence = {'status':'blocked', 'commit':plan['commit'], 'upstream_commit':plan['upstream_commit'], 'inherited_failures':{}}
    evidence_path = report / 'test-evidence.json'
    evidence_path.write_text(json.dumps(evidence, indent=2))
    try:
        release.require(release.run('git','rev-parse','HEAD',cwd=source).strip() == plan['commit'], 'Wrong candidate source')
        selected = [TASK]
        for pattern in CRITICAL:
            selected += ['--tests', '*' + pattern + '*']
        focused = run_tasks(source, selected, report, 'critical')
        evidence['critical_tests'] = critical(focused)
        candidate = run_tasks(source, [TASK, ASSEMBLE], report, 'candidate', ['--continue','-Pnuvio.android.abis=arm64-v8a'])
        critical(candidate)
        evidence['candidate_tests'] = len(candidate)
        if any(x['status'] == 'failed' for x in candidate.values()):
            if upstream_run:
                upstream = artifact_results(upstream_run, plan['upstream_commit'], report)
            else:
                raw = report / 'raw-upstream'
                release.run('git','worktree','add','--detach',str(raw),plan['upstream_commit'],cwd=source)
                release.run('git','lfs','pull',cwd=raw)
                shutil.copyfile(source/'local.properties',raw/'local.properties')
                (raw/'local.properties').chmod(0o600)
                try:
                    upstream = run_tasks(raw,[TASK],report,'upstream')
                finally:
                    (raw/'local.properties').unlink(missing_ok=True)
            evidence['upstream_tests'] = len(upstream)
            evidence['inherited_failures'] = compare(candidate, upstream)
            evidence['upstream_measurement_run'] = upstream_run or os.environ.get('GITHUB_RUN_ID')
        evidence['status'] = 'passed'
    except Exception as error:
        evidence['reason'] = str(error)
        raise
    finally:
        evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence, indent=2))


def validate(path, plan):
    evidence = json.loads(path.read_text())
    release.require(evidence.get('status') == 'passed' and evidence.get('commit') == plan['commit']
                    and evidence.get('upstream_commit') == plan['upstream_commit']
                    and evidence.get('critical_tests',0) > 0 and evidence.get('candidate_tests',0) >= evidence['critical_tests'], 'Test/build evidence missing, failed, or from different source')
    return evidence

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--source',type=Path,required=True); p.add_argument('--plan',type=Path,required=True); p.add_argument('--report',type=Path,required=True); p.add_argument('--upstream-run')
    a=p.parse_args(); gate(a.source.resolve(),a.plan.resolve(),a.report.resolve(),a.upstream_run)
