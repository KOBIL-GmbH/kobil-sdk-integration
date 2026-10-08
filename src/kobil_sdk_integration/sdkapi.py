"""Look a name up in the delivered iOS SDK: its headers and the classes its binary exports.

The official documentation and the delivered headers disagree in places, and some classes
are declared in the headers but missing from the binary, so a build that uses them fails
at link time. This answers "does this SDK release have X" from the release itself: every
header line that mentions the name, and for each class declared there whether the binary
exports it. Reads the installed release only; needs `xcrun nm` (Xcode) for the binary check.
"""
import re
import subprocess
from pathlib import Path

from . import artifacts

# The device slice holds the same headers and classes as the simulator slice.
DEVICE_SLICE = 'ios-arm64'
DECLARATION = re.compile(r'@(?:interface|protocol)\s+([A-Za-z_][A-Za-z0-9_]*)')
# A Swift class names its runtime class in the generated header: SWIFT_CLASS("_TtC6kssidp13KssIdpWrapper").
SWIFT_CLASS = re.compile(r'SWIFT_CLASS(?:_NAMED)?\("([A-Za-z0-9_]+)"')
NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{1,80}$')
MAX_MATCHES = 200


def _slice(xcframework):
    folder = xcframework / DEVICE_SLICE
    frameworks = sorted(folder.glob('*.framework')) if folder.is_dir() else []
    return frameworks[0] if frameworks else None


def exported_symbols(binary):
    """Symbol names the binary defines and exports, or None when nm cannot read it."""
    try:
        output = subprocess.run(['xcrun', 'nm', '-gUj', str(binary)], capture_output=True, text=True,
                                timeout=60, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return {line.strip() for line in output.splitlines() if line.strip()}


def _in_binary(class_name, runtime_name, symbols):
    """An Objective-C class links through its class symbol; a Swift class through its Swift symbols."""
    if '_OBJC_CLASS_$_' + (runtime_name or class_name) in symbols:
        return True
    if runtime_name and runtime_name.startswith('_TtC'):
        # _TtC6kssidp13KssIdpWrapper is the Swift type 6kssidp13KssIdpWrapperC: its metadata and methods.
        prefix = '_$s' + runtime_name[len('_TtC'):] + 'C'
        return any(symbol.startswith(prefix) for symbol in symbols)
    return False


def lookup(name, version=None, frameworks=None, limit=50):
    """Header lines mentioning `name` (case-insensitive) and, per declared class, whether it links."""
    if not isinstance(name, str) or not NAME.match(name):
        raise ValueError('name must be one identifier (letters, digits, underscore), e.g. KSMStartEvent')
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_MATCHES:
        raise ValueError('limit must be between 1 and %d' % MAX_MATCHES)
    if frameworks is None:
        version, frameworks = artifacts.frameworks_dir(version=version)
    frameworks = Path(frameworks)
    needle = name.lower()
    matches, declared = [], {}
    for xcframework in sorted(frameworks.glob('*.xcframework')):
        framework = _slice(xcframework)
        if framework is None:
            continue
        for header in sorted((framework / 'Headers').glob('*.h')):
            runtime_name = None
            for number, line in enumerate(header.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                swift_class = SWIFT_CLASS.search(line)
                if swift_class:
                    runtime_name = swift_class.group(1)
                    continue
                if needle not in line.lower():
                    if line.strip():
                        runtime_name = None
                    continue
                matches.append({'framework': xcframework.stem, 'header': header.name, 'line': number,
                                'text': line.strip()[:300]})
                for declaration in DECLARATION.finditer(line):
                    if needle in declaration.group(1).lower():
                        is_protocol = line.lstrip().startswith('@protocol')
                        declared.setdefault(declaration.group(1), (xcframework.stem, framework, is_protocol,
                                                                   runtime_name if line.lstrip().startswith('@interface') else None))
                runtime_name = None
    classes = []
    exports = {}
    for class_name, (framework_name, framework, is_protocol, runtime_name) in sorted(declared.items()):
        entry = {'name': class_name, 'framework': framework_name, 'kind': 'protocol' if is_protocol else 'class'}
        if is_protocol:
            entry['in_binary'] = 'not applicable: protocols are not exported as classes'
        else:
            if framework_name not in exports:
                exports[framework_name] = exported_symbols(framework / framework.stem)
            symbols = exports[framework_name]
            entry['in_binary'] = ('unknown: xcrun nm could not read the binary' if symbols is None
                                  else _in_binary(class_name, runtime_name, symbols))
            if runtime_name:
                entry['swift_class'] = runtime_name
        classes.append(entry)
    missing = [c['name'] for c in classes if c['in_binary'] is False]
    if not matches:
        answer = 'No header of this release mentions %s.' % name
    elif missing:
        answer = ('Declared in the headers but missing from the binary (the app fails to link): %s.'
                  % ', '.join(missing))
    else:
        exact = any(c['name'] == name for c in classes)
        found = ', '.join(c['name'] for c in classes[:8]) + (', …' if len(classes) > 8 else '')
        answer = 'In the headers%s.' % (' and exported by the binary' if classes and all(
            c['in_binary'] is True for c in classes if c['kind'] == 'class') else '')
        if classes and not exact:
            # A partial match names other things: "Chat" finds chat status events, not a chat API.
            answer += (' No declaration is named %s itself; these contain it: %s. A matching name '
                       'does not prove a feature: read the declarations and the guides.' % (name, found))
    return {'name': name, 'sdk_version': version, 'answer': answer, 'declarations': classes,
            'matches': len(matches), 'results': matches[:limit],
            'note': 'The delivered headers and binary decide what compiles and links; where the official '
                    'documentation differs, trust these. Read the header with the line numbers given.'}
