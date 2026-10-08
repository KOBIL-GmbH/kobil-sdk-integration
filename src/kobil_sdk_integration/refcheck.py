"""Compile the iOS reference sources against a real MCSDK, as an app would.

The skill tells agents to copy the reference files verbatim, so a reference that does not
compile breaks every app built from it. This type-checks each activation variant with the
feature folders it supports, in Swift 5 and Swift 6 language mode, with and without DEBUG,
using the build settings of a new Xcode 26 app (default MainActor isolation, approachable
concurrency). The `#error("PER APP ...")` guards are removed from temporary copies only.

Needs Xcode (xcrun swiftc, iPhone simulator SDK) and an installed SDK release
(sdk_artifacts_install) or a folder holding the four xcframeworks.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import artifacts

IOS_TARGET = 'arm64-apple-ios26.0-simulator'
# What Xcode 26 turns on for a new app target, as swiftc flags.
XCODE_DEFAULTS = ['-default-isolation', 'MainActor', '-enable-bare-slash-regex',
                  '-enable-upcoming-feature', 'NonisolatedNonsendingByDefault',
                  '-enable-upcoming-feature', 'InferIsolatedConformances',
                  '-enable-upcoming-feature', 'MemberImportVisibility',
                  # Approachable concurrency also turns these on in Swift 5 mode.
                  '-enable-upcoming-feature', 'InferSendableFromCaptures',
                  '-enable-upcoming-feature', 'GlobalActorIsolatedTypesUsability',
                  '-enable-upcoming-feature', 'DisableOutwardActorInference']
FEATURES = ['ui', 'signing', 'profile', 'platform', 'sdk-requests', 'wallet']
SHARED = ['HeadlessIdpFlow.swift', 'IdpActivation.swift', 'LoginView.swift', 'TransactionCenter.swift']
# Variant -> files and folders (relative to references/ios) compiled together.
VARIANTS = {
    'login-standards': ['login-standards'] + SHARED + FEATURES,
    'email-code': ['email-code'] + SHARED + FEATURES,
    'activation-code': ['MasterControllerSession.swift', 'IdpActivation.swift', 'ActivationView.swift',
                        'LoginView.swift', 'MasterControllerStatusView.swift'],
}
# Swift Testing sources import the app module (`@testable import YourApp`); not compiled here.
NOT_COMPILED = {'tests'}
PER_APP_GUARD = re.compile(r'^\s*#error\("PER APP.*$', re.MULTILINE)
DIAGNOSTIC = re.compile(r'^(?P<file>[^\s:][^:]*\.swift):(?P<line>\d+):(?P<column>\d+): (?P<kind>error|warning): (?P<text>.*)$',
                        re.MULTILINE)


def ios_references():
    from .docs import _skill_dir
    return _skill_dir() / 'references' / 'ios'


def variant_files(variant, root=None):
    root = Path(root or ios_references())
    files = []
    for entry in VARIANTS[variant]:
        path = root / entry
        files += sorted(path.glob('*.swift')) if path.is_dir() else [path]
    return files


def uncovered_files(root=None):
    """Swift reference files no variant compiles: a new file must be added to VARIANTS."""
    root = Path(root or ios_references())
    covered = {path for variant in VARIANTS for path in variant_files(variant, root)}
    return sorted(path.relative_to(root).as_posix() for path in root.rglob('*.swift')
                  if path not in covered and path.relative_to(root).parts[0] not in NOT_COMPILED)


def simulator_slices(frameworks):
    slices = []
    for xcframework in sorted(Path(frameworks).glob('*.xcframework')):
        found = [p for p in xcframework.iterdir() if p.is_dir() and 'simulator' in p.name]
        if not found:
            raise ValueError('%s has no simulator slice' % xcframework.name)
        slices.append(found[0])
    if not slices:
        raise ValueError('No xcframework in %s' % frameworks)
    return slices


def _copy(root, into):
    for path in root.rglob('*'):
        if path.is_file() and path.suffix in {'.swift', '.h'}:
            target = into / path.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            text = path.read_text(encoding='utf-8')
            target.write_text(PER_APP_GUARD.sub('', text) if path.suffix == '.swift' else text, encoding='utf-8')


def _typecheck(copy, files, slices, sdk, swift_version, debug):
    command = ['xcrun', 'swiftc', '-typecheck', '-parse-as-library', '-sdk', sdk, '-target', IOS_TARGET,
               '-swift-version', swift_version, '-import-objc-header', str(copy / 'App-Bridging-Header.h')]
    command += XCODE_DEFAULTS + (['-DDEBUG'] if debug else [])
    for slice_dir in slices:
        command += ['-F', str(slice_dir)]
    command += [str(copy / f) for f in files]
    run = subprocess.run(command, cwd=copy, capture_output=True, text=True, timeout=600)
    diagnostics = []
    for match in DIAGNOSTIC.finditer(run.stdout + run.stderr):
        file = Path(match['file'])
        try:
            file = file.resolve().relative_to(copy.resolve())
        except ValueError:
            continue  # SDK headers
        entry = '%s:%s:%s: %s' % (file.as_posix(), match['line'], match['column'], match['text'])
        if (match['kind'], entry) not in {(d['kind'], d['at']) for d in diagnostics}:
            diagnostics.append({'kind': match['kind'], 'at': entry})
    return {'passed': run.returncode == 0 and not any(d['kind'] == 'error' for d in diagnostics),
            'errors': [d['at'] for d in diagnostics if d['kind'] == 'error'],
            'warnings': [d['at'] for d in diagnostics if d['kind'] == 'warning']}


def check(frameworks=None, variants=None, swift_versions=('5', '6'), configurations=('debug', 'release'), root=None):
    """Type-check every variant; returns one result per variant, language mode and configuration."""
    if shutil.which('xcrun') is None:
        raise RuntimeError('Xcode command-line tools are required (xcrun not found)')
    root = Path(root or ios_references())
    if frameworks is None:
        _, frameworks = artifacts.frameworks_dir()
    slices = simulator_slices(frameworks)
    sdk = subprocess.run(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'],
                         capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='kobil-refcheck-') as temp:
        copy = Path(temp)
        _copy(root, copy)
        jobs = [(v, s, c) for v in (variants or VARIANTS) for s in swift_versions for c in configurations]
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {job: pool.submit(_typecheck, copy,
                                        [p.relative_to(root) for p in variant_files(job[0], root)],
                                        slices, sdk, job[1], job[2] == 'debug') for job in jobs}
            results = []
            for (variant, swift, configuration), future in futures.items():
                results.append({'variant': variant, 'swift': swift, 'configuration': configuration, **future.result()})
    return {'passed': all(r['passed'] for r in results), 'uncovered': uncovered_files(root), 'results': results}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='kobil-sdk-refcheck', description=__doc__.split('\n\n')[0])
    parser.add_argument('--frameworks', help='folder with the four xcframeworks (default: the installed SDK release)')
    parser.add_argument('--variant', action='append', choices=sorted(VARIANTS))
    parser.add_argument('--swift', action='append', choices=['5', '6'])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    report = check(args.frameworks, args.variant, tuple(args.swift or ('5', '6')))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for r in report['results']:
            print('%-4s %-16s Swift %s %-7s %d errors, %d warnings' % (
                'ok' if r['passed'] else 'FAIL', r['variant'], r['swift'], r['configuration'],
                len(r['errors']), len(r['warnings'])))
            for line in r['errors'] + r['warnings']:
                print('       ' + line)
        for path in report['uncovered']:
            print('FAIL not compiled by any variant: ' + path)
    return 0 if report['passed'] and not report['uncovered'] else 1


if __name__ == '__main__':
    sys.exit(main())
