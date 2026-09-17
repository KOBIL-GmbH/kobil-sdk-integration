"""Expose the pinned integration and its public documentation to Claude clients."""
import os
from pathlib import Path
import subprocess
import sys


def read_guide(release, document='skills/kobil-sdk/SKILL.md'):
    root = Path(release).resolve()
    target = (root / document).resolve()
    allowed = [root / 'skills/kobil-sdk', root / 'docs']
    if not any(target.is_relative_to(folder) for folder in allowed) or target.suffix != '.md':
        raise ValueError('Choose a Markdown document under skills/kobil-sdk or docs.')
    if not target.is_file() or target.stat().st_size > 256 * 1024:
        raise ValueError('Guide is unavailable or exceeds the size limit.')
    return target.read_text(encoding='utf-8')


def main():
    import json
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    os.environ.pop('KOBIL_SDK_CONNECTION', None)
    if cfg.get('connection'):
        os.environ['KOBIL_SDK_CONNECTION'] = cfg['connection']
    if cfg.get('keychain'):
        service, account, name = cfg['keychain']
        try:
            result = subprocess.run(['/usr/bin/security', 'find-generic-password', '-s', service,
                                     '-a', account, '-w'], capture_output=True, text=True,
                                    check=True, timeout=120)
            secret = result.stdout.removesuffix('\n')
            if not secret:
                raise ValueError()
            os.environ[name] = secret
        except (OSError, subprocess.SubprocessError, ValueError):
            print('KOBIL SDK: Keychain credential unavailable; check the configured item.', file=sys.stderr)
            sys.exit(1)
    from kobil_sdk_integration.server import mcp

    @mcp.tool()
    def sdk_guide(document: str = 'skills/kobil-sdk/SKILL.md') -> str:
        """Read the pinned KOBIL integration skill or a public reference.

        Start with the default skill before integrating an SDK. Resolve its relative
        links to release-root paths, e.g. skills/kobil-sdk/references/tms.md or
        docs/backend.md, then call this tool again. No customer files are exposed.
        """
        return read_guide(cfg['release'], document)

    mcp.run()


if __name__ == '__main__':
    main()
