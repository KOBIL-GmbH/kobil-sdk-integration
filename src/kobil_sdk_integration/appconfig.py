"""Generate the app-side configuration file the SDK reads at startup.

The signed sdk_config.jwt is only half of an app's configuration: the SDK also needs
mc_config.json naming the IDP, the login client and the trusted certificate. Writing
it by hand is where integrations silently go wrong, so it is generated from the same
connection the backend tools already use.
"""
import json
import re

KEY_POLICIES = ('ALLOW_VIRTUAL_SMART_CARD', 'ENFORCE_HARDWARE', 'ENFORCE_STRONG_HARDWARE')


def write_mc_config(content, output_path):
    """Save generated mc_config.json content to a NEW file; never overwrites."""
    import json as _json
    import os as _os
    from pathlib import Path as _Path
    path = _Path(output_path).expanduser()
    if not path.parent.is_dir():
        raise ValueError('Output directory must exist')
    if path.exists():
        raise ValueError('Output file already exists; choose a new file name')
    fd = _os.open(str(path), _os.O_WRONLY | _os.O_CREAT | _os.O_EXCL, 0o600)
    text = content if isinstance(content, str) else _json.dumps(content, indent=2) + '\n'
    with _os.fdopen(fd, 'w') as stream:
        stream.write(text)
    return str(path)


def mc_config(cfg, idp_url, client_id, certificate_file,
              key_policy='ALLOW_VIRTUAL_SMART_CARD', redirect_uri='https://kobil/OpenIdRedirectUri'):
    """Return the mc_config.json content for a Shift Lite app. Writes nothing."""
    if not isinstance(idp_url, str) or not idp_url.startswith('https://') or len(idp_url) > 500:
        raise ValueError('Provide the HTTPS base URL of the IDP')
    if not isinstance(client_id, str) or not re.fullmatch(r'[A-Za-z0-9_.\-]{1,120}', client_id):
        raise ValueError('Provide the IDP login client id')
    if not isinstance(certificate_file, str) or not re.fullmatch(r'[A-Za-z0-9_.\-/]{1,120}', certificate_file):
        raise ValueError('Provide the trusted certificate file name as bundled with the app')
    if key_policy not in KEY_POLICIES:
        raise ValueError('Choose a documented key protection policy')
    if not isinstance(redirect_uri, str) or not re.fullmatch(r'[A-Za-z0-9_.:/\-]{1,200}', redirect_uri):
        raise ValueError('Provide the redirect URI registered on the login client')
    content = {
        'useScp': False,
        'useTokenBasedLogin': True,
        'useSmartScreen': False,
        'astServerBackend': 'maverick',
        'iam': {
            'clientId': client_id,
            'serverUrl': idp_url.rstrip('/'),
            'redirectUri': redirect_uri,
            'trustedSslServerCerts': [certificate_file],
        },
        'maverick': {'jwtSignKeySecurityPolicy': key_policy},
    }
    return {
        'file_name': 'mc_config.json',
        'content': json.dumps(content, indent=2) + '\n',
        'environment': cfg['environment'],
        'tenant': cfg['tenant'],
        'bundle_with': ['mc_config.json', 'sdk_config.jwt', certificate_file],
        'note': 'Add all three to the app bundle. The certificate is looked up by this exact '
                'file name. The app version and identifier must match the registered version.',
    }
