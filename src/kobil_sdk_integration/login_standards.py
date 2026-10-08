"""KOBIL's two official native login standards, and a read-only check of a realm against them.

Native apps (KSSIDP, not a web view) activate and log in through one of two standards,
each defined by KOBIL's official IDP flow exports on Confluence:

- kssidp (current): "KSSIDP Enrollment - Multi form flow" and "KSSIDP Mobile App Multi
  Flow Login". Enrollment takes user ID, activation code, temporary password and a new
  password over three pages.
- bddk (deprecated in IDP 5.1/5.2, removal planned for 6.0): "BDDK Enrollment" and
  "BDDK Login". Enrollment takes user ID, activation code and a new password on one page.

Both were verified on a device (iOS, a KOBIL development environment, 2026-09-27). The check never
creates or changes a flow: a realm without the official flows needs the export imported
by its IDP administrator, not a look-alike.
"""
from .activation import _call, admin_token
from .backend import segment

STANDARDS = {
    'kssidp': {
        'status': 'current',
        'source': "KOBIL IDP Confluence: 'KSS-IDP Activation/Enrollment Flow' and 'KSS-IDP Login Flow' "
                  "(DRAFT pages, Sep 2026); flow exports 'KSSIDP Enrollment - Multi form flow' and "
                  "'KSSIDP Mobile App Multi Flow Login'. Copies: skill references/flows/.",
        'activation_client': 'KSSIDPWebBasedEnrollment',
        'login_client': 'KSSIDPWebBasedLogin',
        'activation_flow': 'KSSIDP Enrollment - Multi form flow',
        'login_flow': 'KSSIDP Mobile App Multi Flow Login',
        'activation_steps': [
            'ast-headers-to-session', 'kssidp-activation-code-verifier', 'ast-login-authenticator',
            'kobil-risk-and-policy-evaluator', 'kssidp-configure-or-verify-password',
            'ast-login-authenticator', 'kobil-user-group-authenticator',
            'kssidp-delete-activation-code', 'kobil-claims-authenticator'],
        'login_steps': [
            'ast-headers-to-session', 'ast-login-authenticator', 'kobil-risk-and-policy-evaluator',
            'kobil-username-password-form', 'kssidp-configure-or-verify-password'],
        'login_theme': 'kobil-lite',
        'activation_pages': [
            'user ID + activation code (fields username, activation-code)',
            'temporary password (field password)',
            'new password (fields password, confirmPassword)'],
        'activation_credentials': ['user ID', 'activation code', 'temporary password', 'new password'],
        'login_credentials': ['user ID (also sent as header X-KOBIL-ASTUSERID)', 'password'],
        'administrator_issues': ['membership of group ks-users',
                                 'temporary password: sdk_activation_password_set(temporary=True)',
                                 'activation code: sdk_activation_code_set()'],
        'app_notes': 'KssIdp renders only the first page and drops later pages silently; the app posts '
                     'all three pages natively (skill: references/ios/login-standards/KssidpFormFlow.swift).',
    },
    'bddk': {
        'status': 'deprecated',
        'deprecation': "KOBIL IDP 'Deprecation Planning': BDDK authenticators deprecated in 5.1/5.2, "
                       'removal planned for 6.0, replaced by the KSSIDP authenticators. Use only for '
                       'deployments that already run BDDK.',
        'source': "KOBIL IDP Confluence 'IDP Configuration', attachment BDDK_Partial_Import.json.",
        'activation_client': 'BDDKEnrollment',
        'login_client': 'BDDKLogin',
        'activation_flow': 'BDDK Enrollment',
        'login_flow': 'BDDK Login',
        'activation_steps': [
            'ast-headers-to-session', 'bddk-user-password-reg', 'ast-login-authenticator',
            'ast-login-authenticator', 'kobil-user-group-authenticator'],
        'login_steps': ['ast-headers-to-session', 'kobil-username-password-form', 'ast-login-authenticator'],
        'login_theme': None,
        'activation_pages': ['user ID + activation code + new password (one page)'],
        'activation_credentials': ['user ID', 'activation code', 'new password'],
        'login_credentials': ['user ID (also sent as header X-KOBIL-ASTUSERID)', 'password'],
        'administrator_issues': ['membership of group ks-users', 'activation code: sdk_activation_code_set()'],
        'app_notes': 'One page, so KssIdp runs it without native page posting.',
    },
}

# Step settings a working flow needs, keyed by (standard, role, top-level step index). The
# AST link/login step must read the client data the first step stored in the session:
# without it a fresh device's link fails with 513_4041 (it reads the all-zero client ID).
# The KSSIDP exports set it; the BDDK export omits it on the link step, so a BDDK realm
# imported as-is fails on first activation until it is set.
REQUIRED_STEP_CONFIG = {
    ('kssidp', 'activation', 2): {'Action': 'activate'},
    ('kssidp', 'activation', 4): {'ForceResetTemporaryPwdConfig': 'With Password Verification'},
    ('kssidp', 'activation', 5): {'Action': 'link', 'read_ast_data_from_session': 'true'},
    ('kssidp', 'login', 1): {'Action': 'login', 'read_ast_data_from_session': 'true'},
    ('bddk', 'activation', 2): {'Action': 'activate'},
    ('bddk', 'activation', 3): {'Action': 'link', 'read_ast_data_from_session': 'true'},
    ('bddk', 'login', 2): {'Action': 'login'},
}

APP_SETTINGS = {'useTokenBasedLogin': True, 'astServerBackend': 'maverick',
                'login_header': 'X-KOBIL-ASTUSERID'}


def _steps(api, standard, role, alias, errors):
    """Compare the bound flow's top-level steps and key settings with the standard."""
    expected = STANDARDS[standard][role + '_steps']
    executions = api('GET', '/authentication/flows/%s/executions' % segment(alias))
    if not isinstance(executions, list):
        errors.append("%s: the steps of flow '%s' could not be read." % (role, alias))
        return None
    top = [e for e in executions if isinstance(e, dict) and e.get('level', 0) == 0]
    actual = [e.get('providerId') for e in top]
    if actual != expected:
        errors.append("%s: flow '%s' steps %s differ from the official %s flow %s."
                      % (role, alias, actual, standard, expected))
        return actual
    for index, execution in enumerate(top):
        if execution.get('requirement') != 'REQUIRED':
            errors.append('%s: step %d (%s) must be REQUIRED.' % (role, index + 1, actual[index]))
        wanted = REQUIRED_STEP_CONFIG.get((standard, role, index))
        if not wanted:
            continue
        config_id = execution.get('authenticationConfig')
        stored = api('GET', '/authentication/config/%s' % segment(config_id)) if config_id else None
        config = (stored or {}).get('config', {}) if isinstance(stored, dict) else {}
        for key, value in wanted.items():
            if str(config.get(key, '')).lower() != value.lower():
                hint = (' Without it a fresh device fails with 513_4041.'
                        if key == 'read_ast_data_from_session' else '')
                errors.append('%s: step %d (%s) needs %s=%s.%s' % (role, index + 1, actual[index], key, value, hint))
    return actual


def check(api, login_standard='kssidp', activation_client=None, login_client=None):
    """Check a realm's native clients and flows against an official login standard. Reads only.

    api(method, path, params=None) calls the realm's admin API with paths relative to
    /auth/admin/realms/<realm>. Client names default to the standard's own; other names
    are accepted (a realm may rename them), but their flows must still be the official ones.
    """
    standard = STANDARDS.get(login_standard)
    if standard is None:
        raise ValueError('login_standard must be kssidp (current) or bddk (deprecated)')
    errors, notes, bindings = [], [], []
    if standard['status'] == 'deprecated':
        notes.append(standard['deprecation'])
    for role, client_id in (('activation', activation_client or standard['activation_client']),
                            ('login', login_client or standard['login_client'])):
        clients = api('GET', '/clients', {'clientId': client_id, 'max': 2})
        clients = [c for c in clients if isinstance(c, dict) and c.get('clientId') == client_id] \
            if isinstance(clients, list) else []
        if len(clients) != 1:
            other = next((n for n, s in STANDARDS.items() if client_id == s[role + '_client']
                          and n != login_standard), None)
            errors.append('%s: client %s is missing.%s' % (
                role, client_id, " It belongs to the %s standard; pass login_standard='%s'." % (other, other)
                if other else ' Ask the IDP administrator to import the official export (see source).'))
            continue
        client = clients[0]
        if client.get('enabled') is not True or client.get('standardFlowEnabled') is not True:
            errors.append('%s: client %s must be enabled with standard flow enabled.' % (role, client_id))
        theme = (client.get('attributes') or {}).get('login_theme')
        binding = {'role': role, 'client_id': client_id, 'login_theme': theme}
        bindings.append(binding)
        flow_id = (client.get('authenticationFlowBindingOverrides') or {}).get('browser')
        flow = api('GET', '/authentication/flows/%s' % segment(flow_id)) if flow_id else None
        alias = flow.get('alias') if isinstance(flow, dict) else None
        binding['flow_alias'] = alias
        if alias != standard[role + '_flow']:
            errors.append("%s: client %s is bound to flow %r, not the official %s flow '%s'. Do not "
                          'build a look-alike; import the official export.'
                          % (role, client_id, alias, login_standard, standard[role + '_flow']))
            continue
        if standard['login_theme'] and theme != standard['login_theme']:
            errors.append('%s: client %s uses theme %r; only %s ships the KSSIDP templates (others '
                          'answer HTTP 500 TemplateNotFoundException).' % (role, client_id, theme,
                                                                           standard['login_theme']))
        binding['steps'] = _steps(api, login_standard, role, alias, errors)
    return {
        'status': 'blocked' if errors else 'configuration_checked',
        'login_standard': login_standard, 'errors': errors, 'notes': notes, 'bindings': bindings,
        'standard': {k: standard[k] for k in ('status', 'source', 'activation_client', 'login_client',
                                              'activation_pages', 'activation_credentials',
                                              'login_credentials', 'administrator_issues', 'app_notes')},
        'app_settings': APP_SETTINGS,
        'runtime_verified': False,
        'limits': 'Checks clients, flow bindings, theme, the official step order and the step settings a '
                  'first activation depends on; not every authenticator setting, PIN policy or live app '
                  'behavior. configuration_checked is not a device test.',
    }


def check_realm(backend, login_standard='kssidp', activation_client=None, login_client=None):
    token = admin_token(backend)
    base = '/auth/admin/realms/%s' % segment(backend.cfg['tenant'])

    def api(method, path, params=None):
        return _call(backend, token, method, base + path, params=params, allow_not_found=True)

    return check(api, login_standard, activation_client, login_client)
