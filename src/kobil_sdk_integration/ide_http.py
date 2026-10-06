"""Project-local Streamable HTTP adapter using the MCP library transport."""
import argparse
import hmac
import os
from pathlib import Path
import stat


class LocalAuthorization:
    """Reject unauthorized HTTP calls before MCP session allocation."""
    def __init__(self, app, token):
        self.app = app
        self.expected = ('Bearer ' + token).encode('ascii')

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            headers = [v for k, v in scope['headers'] if k.lower() == b'authorization']
            if len(headers) != 1 or not hmac.compare_digest(headers[0], self.expected):
                await send({'type': 'http.response.start', 'status': 401,
                            'headers': [(b'content-type', b'text/plain')]})
                await send({'type': 'http.response.body', 'body': b'Local MCP authorization required'})
                return
        await self.app(scope, receive, send)


def read_token(path):
    """Read an owner-only regular file; never return its value in diagnostics."""
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, 'r', encoding='ascii') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise ValueError()
            if hasattr(os, 'getuid') and info.st_uid != os.getuid():
                raise ValueError()
            token = stream.read(257).strip()
            if not 32 <= len(token) <= 256 or not all(c.isalnum() or c in '-_' for c in token):
                raise ValueError()
            return token
    except (OSError, ValueError, UnicodeError):
        raise ValueError('HTTP_TOKEN_UNAVAILABLE: use a private owner-only token file') from None


def build_app(mcp, token, port):
    from mcp.server.transport_security import TransportSecuritySettings
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[f'127.0.0.1:{port}'], allowed_origins=[])
    return LocalAuthorization(mcp.streamable_http_app(), token)


def main():
    parser = argparse.ArgumentParser(description='Run one local MCP HTTP process for one project; stop with Ctrl-C')
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--connection', type=Path)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Choose a port between 1024 and 65535')
    project = args.project.expanduser().resolve(strict=True)
    if not project.is_dir():
        parser.error('Project must be an existing directory')
    token = read_token(args.token_file.expanduser())
    os.environ['KOBIL_SDK_PROJECT'] = str(project)
    # Explicit project invocation must never inherit another project's selector.
    os.environ.pop('KOBIL_SDK_CONNECTION', None)
    if args.connection:
        os.environ['KOBIL_SDK_CONNECTION'] = str(args.connection.expanduser().resolve(strict=True))
    from .server import mcp
    from . import onboarding
    import uvicorn
    onboarding.startup()
    uvicorn.run(build_app(mcp, token, args.port), host='127.0.0.1', port=args.port,
                access_log=False, log_level='warning')


if __name__ == '__main__':
    main()
