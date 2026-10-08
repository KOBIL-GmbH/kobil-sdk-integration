"""First-start recipient setup and copyable credential request; never sends mail."""
import os
from pathlib import Path
from .age_store import absolute, atomic_write, project_identity


def configured_connection():
    """Return the selected connection path when it exists; onboarding is then unnecessary."""
    selected = os.environ.get('KOBIL_SDK_CONNECTION')
    if selected and Path(selected).expanduser().is_file():
        return str(Path(selected).expanduser())
    return None


def prepare(project_path):
    project = absolute(project_path).resolve(strict=True)
    existing = configured_connection()
    if existing:
        return {'status': 'connection_already_configured', 'connection': existing,
                'email_sent': False, 'existing_connections_preserved': True,
                'next_step': 'A backend connection is already selected for this project. Call sdk_backend_status and continue with the standard journey; no credential request or identity is needed.'}
    info = project_identity(str(project))
    local = project / '.kobil-sdk'
    incoming = local / 'incoming'
    incoming.mkdir(mode=0o700, exist_ok=True)
    if incoming.is_symlink():
        raise ValueError('Incoming delivery directory must not be a symlink')
    public = info['recipient']
    subject = 'KOBIL SDK access request — ' + project.name
    body = f'''Hello,

Please provide the approved test-server access and SDK SFTP access for my KOBIL SDK project.

Encrypt the credential delivery for this age public recipient:

{public}

I can also attach recipient.txt containing this public key.

Please include:
- IDP and AST environment settings and the credentials required for SDK integration.
- SDK SFTP server, port, username, authorized release directory and credentials.
- The verified SSH host-key fingerprint or public host key for the SFTP server.

For IDP/AST, please use sdk_age_server_bundle_export with the recipient above.
For SFTP credentials, sdk_age_transfer_export can create a separate encrypted
credential delivery. Please provide the matching SFTP connection settings as well.
Return the encrypted .age file(s); please do not send plaintext passwords or private keys.

Thank you.
'''
    content = 'Subject: ' + subject + '\n\n' + body
    target = local / 'credential-request.txt'
    atomic_write(target, content.encode(), replace=True)
    return {'status': 'credential_delivery_requested', 'recipient': public,
            'recipient_file': info['recipient_file'], 'request_file': str(target),
            'email_subject': subject, 'email_body': body,
            'incoming_directory': str(incoming), 'email_sent': False,
            'existing_connections_preserved': True,
            'next_step': 'Show the email text and public recipient to the user for copying. Wait for recipient-encrypted server/SFTP delivery. Never ask for a private delivery key or plaintext password in chat.'}


def startup():
    project = os.environ.get('KOBIL_SDK_PROJECT')
    if not project:
        connection = os.environ.get('KOBIL_SDK_CONNECTION')
        if connection:
            parent = Path(connection).expanduser().parent
            if parent.name == '.kobil-sdk':
                project = str(parent.parent)
    # Do not guess the host working directory: some clients start in / or HOME.
    # A selected connection means the installation is onboarded: write no request file.
    if project and not configured_connection():
        local = Path(project).expanduser()/'.kobil-sdk'
        if not (local/'credential-request.txt').exists():
            prepare(project)


def register(mcp):
    @mcp.tool()
    def sdk_onboarding_prepare(project_path: str) -> dict:
        """Create/reuse a project age identity and prepare a copy-paste access-request email.

        Return the PUBLIC recipient and public recipient.txt path. Request IDP/AST
        and SFTP credentials encrypted for that recipient. Never send email, return
        private keys, alter existing connections, or contact backends. Save received
        files in the project incoming directory, then import with existing age tools.
        """
        return prepare(project_path)
