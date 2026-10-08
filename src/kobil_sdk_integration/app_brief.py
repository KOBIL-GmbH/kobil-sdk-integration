"""One short request ("build me an app with the KOBIL SDK") expands into the full, verified task.

The brief is made from facts the server already knows (the selected environment and its TLS hosts, the project folder,
the Xcode target and team, the SDK delivery) plus the decisions that were verified on a simulator: trusted WebView
enrollment and token-based SignedJWT login with the kobil-mobile themed clients, mTLS off, pinning on. It asks the
owner only for what it cannot find, and never invents a path or a credential.
"""
import os
import re
from pathlib import Path

IOS_FRAMEWORKS = ('KSMasterController', 'hnb', 'kssidp', 'KSTrustedWebView')
_UNSET = object()

RULES = [
    'Never print or write passwords, activation codes, tokens or JWTs into files or logs.',
    'Never request credentials and never call sdk_onboarding_prepare: the connection is configured.',
    'Never edit project.pbxproj by hand and never copy frameworks by hand: sdk_ios_project_integrate does it.',
    'Never modify or delete existing users, clients, flows or scopes; create your own test users only.',
    'maverick.mTLS is always false; certificate pinning stays on and validation is never weakened.',
    'Test first: a failing XCTest before each feature, then make it pass. No git.',
]

GATES = [
    {'id': 1, 'name': 'start', 'evidence': 'SDK log shows Start OK with pinned TLS'},
    {'id': 2, 'name': 'activation', 'evidence': 'SDK log plus the user showing a registered device on the server'},
    {'id': 3, 'name': 'login', 'evidence': 'SDK log plus an access token event on the server (claims only)'},
    {'id': 4, 'name': 'cold start and SignedJWT offline login', 'evidence': 'SDK log with the proof signature'},
    {'id': 5, 'name': 'TMS accept and reject', 'evidence': 'sdk_tms_status and sdk_tms_result readback for both'},
    {'id': 6, 'name': 'encrypted log export', 'evidence': 'the archive exists, entries listed, no secrets inside'},
]


def find_framework_set(base):
    """The folder that holds all four .xcframework, directly or in its debug subfolder; None when incomplete."""
    base = Path(base).expanduser()
    for folder in (base, base / 'debug'):
        if folder.is_dir() and all((folder / (name + '.xcframework')).is_dir() for name in IOS_FRAMEWORKS):
            return folder
    return None


def _project_facts(project):
    """(.xcodeproj path, target name, team id) of the Xcode project in the folder, or (None, None, None)."""
    if not project or not Path(project).is_dir():
        return None, None, None
    found = sorted(Path(project).glob('*.xcodeproj'))
    if not found:
        return None, None, None
    xcodeproj = found[0]
    team = None
    try:
        match = re.search(r'DEVELOPMENT_TEAM = ([A-Z0-9]{10});', (xcodeproj / 'project.pbxproj').read_text())
        team = match.group(1) if match else None
    except OSError:
        pass
    return xcodeproj, xcodeproj.stem, team


def _state_file():
    return Path(os.environ.get('KOBIL_SDK_HOME') or Path.home() / '.kobil-sdk') / 'sdk-delivery'


def _remember(folder):
    """Keep the folder the owner named, so the next app is not asked again (local, owner-only file)."""
    try:
        path = _state_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(str(folder))
        os.chmod(path, 0o600)
    except OSError:
        pass


def _delivery(explicit, project):
    try:
        remembered = _state_file().read_text().strip()
    except OSError:
        remembered = None
    candidates = [explicit, os.environ.get('KOBIL_SDK_DELIVERY'), remembered]
    if project:
        candidates += [Path(project) / 'SDK', Path(project).parent / 'SDK']
    for candidate in candidates:
        if candidate:
            folder = find_framework_set(candidate)
            if folder:
                if explicit and candidate == explicit:
                    _remember(folder)
                return folder
    return None


def build(platform, status=_UNSET, delivery_folder=None):
    if platform != 'ios':
        raise ValueError('The app brief is verified for iOS only; for Android follow the skill, start with sdk_knowledge_bundle(platform="android")')
    project = os.environ.get('KOBIL_SDK_PROJECT')
    xcodeproj, target, team = _project_facts(project)
    delivery = _delivery(delivery_folder, project)
    needs = []
    if not status or not status.get('configured'):
        needs.append({'key': 'connection', 'ask': 'No backend connection is selected. Ask the owner once to import the access delivery '
                      '(sdk_onboarding_prepare is only for this case); do not ask for credentials in the chat.'})
    if xcodeproj is None:
        needs.append({'key': 'xcode_project', 'ask': 'No .xcodeproj in the project folder. Ask the owner to create the SwiftUI app in Xcode '
                      '(or create it with the Xcode tools) and start the chat in that folder.'})
    if delivery is None:
        needs.append({'key': 'sdk_delivery_folder', 'ask': 'Ask the owner once for the folder with the iOS SDK delivery '
                      '(the debug set with the four .xcframework: ' + ', '.join(IOS_FRAMEWORKS) + ').'})
    status = status or {}
    environment = status.get('environment', '<environment>')
    hosts = list(status.get('tls_check_hosts') or [])
    name = (target or 'app').lower()
    decisions = {
        'platform': 'ios', 'environment': environment, 'tenant': status.get('tenant'), 'tls_hosts': hosts,
        'project_path': str(xcodeproj) if xcodeproj else None, 'target_name': target, 'team_id': team,
        'frameworks_dir': str(delivery) if delivery else None,
        'login_path': 'kstrustedwebview', 'activation_client': 'KobilMobileEnrollment', 'login_client': 'KobilMobileLogin',
        'use_token_based_login': True, 'mtls': False, 'jwt_sign_key_policy_simulator': 'ALLOW_VIRTUAL_SMART_CARD',
        'test_user_prefix': 'xcode%s-%s' % (os.environ.get('KOBIL_SDK_BRIEF_DATE', __import__('time').strftime('%Y%m%d')), name),
    }
    steps = [
        {'tool': 'sdk_runtime_info', 'args': {}, 'why': 'which runtime and which project this server is bound to'},
        {'tool': 'sdk_backend_status', 'args': {}, 'why': 'environment, tenant and the hosts for the TLS check'},
        {'tool': 'sdk_theme_get', 'args': {}, 'why': 'the look and feel to build with; the owner\'s own theme replaces the default'},
        {'tool': 'sdk_artifact_info', 'args': {'path': '<each .xcframework in frameworks_dir>'}, 'why': 'check the delivery before use'},
        {'tool': 'sdk_ios_project_integrate', 'args': {'project_path': decisions['project_path'] or '<.xcodeproj>',
                                                        'target_name': target or '<target>',
                                                        'frameworks_dir': decisions['frameworks_dir'] or '<debug set folder>'},
         'why': 'link and embed the four frameworks; build once and start the app before adding SDK code'},
        {'tool': 'sdk_tls_chain_check', 'args': {'hosts': hosts or ['<tls_check_hosts>'], 'trust_asset_path': '<existing PEM trust file>',
                                                  'platform': 'ios'}, 'why': 'every host must chain to the pinned roots before the first start'},
        {'tool': 'sdk_app_get', 'args': {'expected_environment': environment, 'app_name': '<AST app name>'},
         'why': 'prefer an existing suitable AST app (also sdk_app_versions); create one with sdk_app_ensure only if none fits'},
        {'tool': 'sdk_app_versions', 'args': {'expected_environment': environment, 'app_name': '<AST app name>'}, 'why': 'pick the version'},
        {'tool': 'sdk_config_write', 'args': {'expected_environment': environment, 'certificate_paths': ['<trust PEM>'],
                                              'output_path': '<app bundle folder>/sdk_config.jwt'}, 'why': 'the signed SDK configuration'},
        {'tool': 'sdk_native_preflight', 'args': {'expected_environment': environment, 'platform': 'ios', 'path': 'kstrustedwebview',
                                                   'activation_client': 'KobilMobileEnrollment', 'login_client': 'KobilMobileLogin',
                                                   'use_token_based_login': True, 'ast_server_backend': 'maverick',
                                                   'login_header': 'X-KOBIL-ASTUSERID'}, 'why': 'proceed only on configuration_checked'},
        {'tool': 'sdk_deployment_preflight', 'args': {'mc_config_path': '<mc_config.json in the app>', 'expected_mtls': False},
         'why': 'the real mc_config must pass before code'},
    ]
    return {'platform': 'ios', 'needs_input': needs, 'decisions': decisions, 'steps': steps, 'gates': GATES, 'rules': RULES,
            'prompt': _prompt(decisions, needs)}


def _prompt(d, needs):
    asks = ' '.join(n['ask'] for n in needs) or 'Nothing is missing; do not ask the owner anything before the gates need them.'
    hosts = ', '.join(d['tls_hosts']) or '<tls_check_hosts>'
    return (
        'autopilot. Do not wait for approval between steps; stop only on a blocker or when you need the owner. '
        'Build a complete KOBIL SDK iOS app in this project (%s, team %s). Use only the kobil-sdk skill and the KOBILSDK MCP for KOBIL knowledge. '
        'Environment %s (tenant %s), TLS hosts: %s. '
        'Order: sdk_runtime_info, sdk_backend_status; check each .xcframework in %s with sdk_artifact_info; embed them with '
        'sdk_ios_project_integrate(project_path, target_name, frameworks_dir), build once and prove the app starts before SDK code; '
        'create the PEM trust file and run sdk_tls_chain_check (platform ios) for every host; reuse a suitable AST app (sdk_app_get, '
        'sdk_app_versions); sdk_config_write; sdk_native_preflight and sdk_deployment_preflight must pass before code. '
        'Decisions: trusted WebView enrollment with %s and SignedJWT token-based login with %s (kobil-mobile theme), biometric; '
        'jwtSignKeySecurityPolicy %s on the simulator, set before activation; mTLS false; certificate pinning on. '
        'Test users are named %s-*. '
        'Look and feel: call sdk_theme_get and build every screen from its roles with the native controls; the owner\'s own design always wins. '
        'Gates, each with SDK-log and server evidence: 1 start (pinned TLS), 2 activation, 3 login, 4 cold start and SignedJWT offline login, '
        '5 TMS accept and reject with readback (sdk_tms_trigger, sdk_tms_status, sdk_tms_result), 6 encrypted log export. '
        'Rules: %s '
        'Keep ACTIVITY.md (one line per step), ISSUES.md (every place the MCP knowledge or skill was missing or wrong) and TEST_REPORT.md '
        '(PASS or FAIL per gate with evidence paths) in the project. '
        'If sdk_runtime_info or sdk_backend_status returns feedback_prompt, ask the owner one short question about problems. '
        'Open questions for the owner: %s'
    ) % (d['target_name'] or 'new app', d['team_id'] or 'from the project', d['environment'], d['tenant'] or '-', hosts,
         d['frameworks_dir'] or 'the SDK delivery', d['activation_client'], d['login_client'], d['jwt_sign_key_policy_simulator'],
         d['test_user_prefix'], ' '.join(RULES), asks)
