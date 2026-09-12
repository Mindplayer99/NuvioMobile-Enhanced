#!/usr/bin/env python3
"""Review changed content and canonical hunk intersections, not broad directories."""
import re
import subprocess

CONTRACT = re.compile(r'requestedOrientation|SCREEN_ORIENTATION|PlayerOrientation|player_orientation|rememberedOrientation|orientationOverride|orientationPreference|lastUsedOrientation|CompactPlayerTrackSheet|supportsPictureInPicture|resizeableActivity|android:screenOrientation|android:configChanges', re.I)
IDENTITY = re.compile(r'applicationId|applicationIdSuffix|namespace\s*=|signingConfig|signingConfigs|NUVIO_RELEASE_|storePassword|keyPassword|keyAlias|storeFile|android:debuggable|package=')
LIFECYCLE = re.compile(r'LaunchedEffect|DisposableEffect|onDispose|onStop|onPause|onResume|onConfigurationChanged|isInPictureInPictureMode|isInMultiWindowMode|sessionId|sessionKey|contentKey|requestedOrientation|playbackSession|sourceId|contentId')
CHANNEL = re.compile(r'releases|github|orientation|\.apk|asset|versionCode|download|channel', re.I)
HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)')


def hunks(diff):
    result = []
    for line in diff.splitlines():
        match = HUNK.match(line)
        if match:
            start, count = int(match[1]), int(match[2] or 1)
            result.append({'start': start, 'end': start + max(count, 1) - 1,
                           'header': line, 'lines': []})
        elif result and line[:1] in ('+', '-') and not line.startswith(('+++', '---')):
            result[-1]['lines'].append(line)
    return result


def code(lines):
    # Ignore comment-only/whitespace edits, without erasing string literals or numbers.
    before = [x[1:].strip() for x in lines if x.startswith('-')]
    after = [x[1:].strip() for x in lines if x.startswith('+')]
    if before == after:
        return ''
    return '\n'.join(x[1:].strip() for x in lines if x[1:].strip()
                     and not x[1:].lstrip().startswith(('//', '*', '/*', '#')))


def classify(path, diff, canonical=''):
    changes = hunks(diff)
    report = {'path': path, 'risk': 'soft', 'reasons': [], 'hunks': []}
    # Data/resources cannot call platform APIs. Manifest is deliberately excluded.
    data = bool(re.search(r'(^|/)(docs|fastlane|metadata)/|\.(md|png|jpg|webp|svg)$|/composeResources/|baseline-prof', path))
    tests = bool(re.search(r'/(commonTest|androidHostTest|test)/', path))
    canonical_hunks = hunks(canonical)
    for h in changes:
        text = code(h['lines'])
        reasons = []
        if not text:
            continue
        if not data and not tests:
            symbols = CONTRACT.findall(text)
            if symbols:
                reasons.append('Orientation/platform contract: ' + ', '.join(sorted(set(symbols))))
            if IDENTITY.search(text) and (path.endswith(('.kts', '.gradle', '.xml', '.properties')) or '/buildSrc/' in path):
                reasons.append('Package/signing identity configuration changed')
            if '/player/' in path and LIFECYCLE.search(text):
                reasons.append('Player lifecycle/session state used by Orientation changed')
            if ('/updater/' in path or 'AppVersionConfig' in path) and CHANNEL.search(text):
                reasons.append('Updater channel/asset selection changed')
        for c in canonical_hunks:
            if h['start'] <= c['end'] and c['start'] <= h['end']:
                reasons.append('Changed upstream hunk intersects the canonical Orientation delta')
                break
        if reasons:
            report['risk'] = 'hard'
            report['reasons'].extend(reasons)
            report['hunks'].append({'header': h['header'], 'changed_lines': h['lines']})
    if report['risk'] != 'hard':
        report['risk'] = 'low' if data or tests or (changes and not any(code(h['lines']) for h in changes)) else 'soft'
        report['reasons'] = ['Orthogonal data/tests' if report['risk'] == 'low' else 'Proceed to structural integration, tests, build and APK verification']
    return report


def review(root, base, target, orientation):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True)
    paths = git('diff', '--name-only', base, target).splitlines()
    return [classify(p, git('diff', '--no-ext-diff', '--unified=0', base, target, '--', p),
                     git('diff', '--no-ext-diff', '--unified=3', base, orientation, '--', p)) for p in paths]
