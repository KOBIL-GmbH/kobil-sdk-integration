"""Wire the delivered XCFrameworks into an Xcode project the way the verified app has them.

Xcode's own agent tools can create a project and set build settings, but nothing adds a
framework as "Embed & Sign". The manual steps (drag four bundles, tick the right target,
switch each to Embed & Sign, add a bridging header, set its build setting, fix the version)
were the part outsiders got wrong most. This writes exactly the project-file entries the
device-verified app carries, and verifies them by reading the file back.

Scope: an Xcode 16+ project whose app target uses a file-system-synchronised folder (the
default for new projects). Frameworks are copied into that folder so the sources see them.
"""
import hashlib
import platform
import re
import shutil
import subprocess
from pathlib import Path

from .artifacts import IOS_FRAMEWORKS

TARGET = re.compile(r'[A-Za-z0-9_.-]{1,80}')
SEMVER = re.compile(r'\d+\.\d+(?:\.\d+)?')

BRIDGING_HEADER = (
    "#import <KSMasterController/KSMasterController.h>\n"
    "#import <KSMasterController/KsHelpers.h>\n"
    "#import <KSMasterController/KSEvent.h>\n"
    "#import <KSMasterController/KsEcoModulInterface.h>\n"
    "#import <kssidp/kssidp.h>\n"
)


def _copy_bundle(source, dest):
    """Copy a framework bundle; on macOS as an APFS clone, which is instant and exact."""
    if platform.system() == 'Darwin':
        done = subprocess.run(['cp', '-Rc', str(source), str(dest)], capture_output=True)
        if done.returncode == 0:
            return
        shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(source, dest, symlinks=True)


def object_id(seed):
    """A stable 24-hex identifier, so re-runs and reviews see the same ids."""
    return hashlib.sha1(seed.encode()).hexdigest()[:24].upper()


def _native_target(text, target_name):
    pattern = re.compile(r'\t\t([0-9A-F]{24}) /\* %s \*/ = \{\n\t\t\tisa = PBXNativeTarget;(.*?)\n\t\t\};'
                         % re.escape(target_name), re.S)
    match = pattern.search(text)
    if not match:
        raise ValueError('The project has no native target named %s' % target_name)
    return match


def _config_ids(text, target_body):
    list_id = re.search(r'buildConfigurationList = ([0-9A-F]{24})', target_body).group(1)
    block = re.search(r'\t\t%s /\*.*?\*/ = \{\n\t\t\tisa = XCConfigurationList;(.*?)\n\t\t\};' % list_id, text, re.S)
    if not block:
        raise ValueError('The target has no configuration list')
    return re.findall(r'\t\t\t\t([0-9A-F]{24}) /\*', block.group(1))


def _set_build_setting(text, config_id, key, value):
    """Set one key inside one XCBuildConfiguration block, replacing or inserting."""
    pattern = re.compile(r'(\t\t%s /\*.*?\*/ = \{\n\t\t\tisa = XCBuildConfiguration;\n\t\t\tbuildSettings = \{\n)(.*?)(\n\t\t\t\};)'
                         % config_id, re.S)
    match = pattern.search(text)
    if not match:
        raise ValueError('Build configuration %s not found' % config_id)
    body = match.group(2)
    line = '\t\t\t\t%s = %s;' % (key, value)
    if re.search(r'^\t\t\t\t%s = ' % re.escape(key), body, re.M):
        body = re.sub(r'^\t\t\t\t%s = .*;$' % re.escape(key), line.replace('\\', '\\\\'), body, count=1, flags=re.M)
    else:
        body = line + '\n' + body
    return text[:match.start(2)] + body + text[match.end(2):]


def integrate(project_path, target_name, frameworks_dir, marketing_version='1.0.0', deployment_target=None):
    """Copy the frameworks next to the target's sources and register them as Embed & Sign."""
    project = Path(project_path).expanduser()
    if project.suffix != '.xcodeproj' or not (project / 'project.pbxproj').is_file():
        raise ValueError('Provide the path of a .xcodeproj')
    if not isinstance(target_name, str) or not TARGET.fullmatch(target_name):
        raise ValueError('Provide the app target name')
    if not SEMVER.fullmatch(str(marketing_version)):
        raise ValueError('marketing_version must look like 1.0.0')
    if deployment_target is not None and not SEMVER.fullmatch(str(deployment_target)):
        raise ValueError('deployment_target must look like 26.0')
    frameworks = Path(frameworks_dir).expanduser()
    missing = [n for n in IOS_FRAMEWORKS if not (frameworks / (n + '.xcframework')).is_dir()]
    if missing:
        raise ValueError('Framework set incomplete, missing: %s' % ', '.join(missing))
    pbxproj = project / 'project.pbxproj'
    text = pbxproj.read_text()
    target = _native_target(text, target_name)
    target_dir = project.parent / target_name
    if not target_dir.is_dir():
        raise ValueError('Expected the target folder %s next to the project' % target_dir)
    prefix = 'kobil-sdk:%s:' % target_name
    ref_ids = {n: object_id(prefix + 'ref:' + n) for n in IOS_FRAMEWORKS}
    if all(ref_ids[n] in text for n in IOS_FRAMEWORKS):
        return {'project': str(project), 'target': target_name, 'changed': False,
                'note': 'Already integrated; nothing was modified.'}
    if 'wrapper.xcframework' in text:
        raise ValueError('The project already references XCFrameworks in another way; integrate by hand')

    copied = []
    for name in IOS_FRAMEWORKS:
        dest = target_dir / (name + '.xcframework')
        if not dest.exists():
            _copy_bundle(frameworks / (name + '.xcframework'), dest)
            copied.append(name)
    header_name = '%s-Bridging-Header.h' % target_name
    header = target_dir / header_name
    if not header.exists():
        header.write_text(BRIDGING_HEADER)

    embed_ids = {n: object_id(prefix + 'embed:' + n) for n in IOS_FRAMEWORKS}
    phase_id = object_id(prefix + 'phase')
    group_id = object_id(prefix + 'group')
    build_files = ''.join(
        '\t\t%s /* %s.xcframework in Embed Frameworks */ = {isa = PBXBuildFile; fileRef = %s /* %s.xcframework */; '
        'settings = {ATTRIBUTES = (CodeSignOnCopy, RemoveHeadersOnCopy, ); }; };\n'
        % (embed_ids[n], n, ref_ids[n], n) for n in IOS_FRAMEWORKS)
    file_refs = ''.join(
        '\t\t%s /* %s.xcframework */ = {isa = PBXFileReference; lastKnownFileType = wrapper.xcframework; '
        'name = %s.xcframework; path = %s/%s.xcframework; sourceTree = "<group>"; };\n'
        % (ref_ids[n], n, n, target_name, n) for n in IOS_FRAMEWORKS)
    phase = ('\t\t%s /* Embed Frameworks */ = {\n\t\t\tisa = PBXCopyFilesBuildPhase;\n\t\t\tdstPath = "";\n'
             '\t\t\tdstSubfolder = Frameworks;\n\t\t\tfiles = (\n' % phase_id
             + ''.join('\t\t\t\t%s /* %s.xcframework in Embed Frameworks */,\n' % (embed_ids[n], n) for n in IOS_FRAMEWORKS)
             + '\t\t\t);\n\t\t\tname = "Embed Frameworks";\n\t\t};\n')
    group = ('\t\t%s /* KOBIL SDK */ = {\n\t\t\tisa = PBXGroup;\n\t\t\tchildren = (\n' % group_id
             + ''.join('\t\t\t\t%s /* %s.xcframework */,\n' % (ref_ids[n], n) for n in IOS_FRAMEWORKS)
             + '\t\t\t);\n\t\t\tname = "KOBIL SDK";\n\t\t\tsourceTree = "<group>";\n\t\t};\n')

    def add_section(text, name, body):
        end = '/* End %s section */' % name
        if end in text:
            return text.replace(end, body + end, 1)
        anchor = 'objects = {\n\n'
        if anchor not in text:
            raise ValueError('Unrecognised project file layout')
        return text.replace(anchor, anchor + '/* Begin %s section */\n%s/* End %s section */\n\n' % (name, body, name), 1)

    text = add_section(text, 'PBXBuildFile', build_files)
    text = add_section(text, 'PBXCopyFilesBuildPhase', phase)
    text = add_section(text, 'PBXFileReference', file_refs)
    text = add_section(text, 'PBXGroup', group)

    main_group = re.search(r'mainGroup = ([0-9A-F]{24})', text).group(1)
    main_pattern = re.compile(r'(\t\t%s = \{\n\t\t\tisa = PBXGroup;\n\t\t\tchildren = \(\n)' % main_group)
    if not main_pattern.search(text):
        raise ValueError('Main group not found')
    text = main_pattern.sub(lambda m: m.group(1) + '\t\t\t\t%s /* KOBIL SDK */,\n' % group_id, text, count=1)

    target = _native_target(text, target_name)
    body = target.group(2)
    phases = re.search(r'buildPhases = \(\n(.*?)\t\t\t\);', body, re.S)
    new_body = body[:phases.end(1)] + '\t\t\t\t%s /* Embed Frameworks */,\n' % phase_id + body[phases.end(1):]
    text = text[:target.start(2)] + new_body + text[target.end(2):]

    for config_id in _config_ids(text, new_body):
        text = _set_build_setting(text, config_id, 'SWIFT_OBJC_BRIDGING_HEADER', '"%s/%s"' % (target_name, header_name))
        text = _set_build_setting(text, config_id, 'MARKETING_VERSION', str(marketing_version))
    if deployment_target is not None:
        # Every native target, not only the app: Xcode marks a device "Incompatible" for
        # the scheme while any target, the test targets included, demands a newer OS.
        for body in re.findall(r'isa = PBXNativeTarget;(.*?)\n\t\t\};', text, re.S):
            for config_id in _config_ids(text, body):
                text = _set_build_setting(text, config_id, 'IPHONEOS_DEPLOYMENT_TARGET', str(deployment_target))

    pbxproj.write_text(text)
    check = pbxproj.read_text()
    problems = [n for n in IOS_FRAMEWORKS if check.count(ref_ids[n]) < 3 or check.count(embed_ids[n]) != 2]
    if problems or check.count(phase_id) != 2 or check.count('SWIFT_OBJC_BRIDGING_HEADER') < 2:
        raise ValueError('The project file did not read back as expected; inspect it before building')
    return {'project': str(project), 'target': target_name, 'changed': True,
            'frameworks_copied': copied, 'bridging_header': str(header),
            'build_settings': {'SWIFT_OBJC_BRIDGING_HEADER': '%s/%s' % (target_name, header_name),
                               'MARKETING_VERSION': str(marketing_version),
                               'IPHONEOS_DEPLOYMENT_TARGET': deployment_target},
            'note': 'Frameworks are embedded and signed on copy, as in the device-verified app. '
                    'Build once before adding code: a green build proves the link.'}
