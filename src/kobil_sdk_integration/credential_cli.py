"""Local setup only: never exposes a print/get-secret command."""
import argparse
import getpass
import json
import os
from pathlib import Path
import sys
import warnings
from .backend import authentication, configuration, BackendError, AST
from .credentials import CredentialError, resolve, store, delete, validate_reference


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    status = sub.add_parser('status'); status.add_argument('--probe', action='store_true')
    set_cmd = sub.add_parser('set'); set_cmd.add_argument('--replace', action='store_true')
    # Private pipe bridge for a local editor password dialog, not a CLI password arg.
    set_cmd.add_argument('--stdin', action='store_true', help='Read value from a private editor pipe')
    remove = sub.add_parser('delete'); remove.add_argument('--confirm', action='store_true', required=True)
    test = sub.add_parser('test-backend'); test.add_argument('--environment', required=True); test.add_argument('--app', required=True)
    migrate = sub.add_parser('prepare-keyring'); migrate.add_argument('--service', required=True); migrate.add_argument('--account', required=True); migrate.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        cfg = configuration(path=args.config)
        auth = authentication(cfg); ref = auth['credential']
        if args.command == 'status':
            if args.probe: resolve(ref)
            print(json.dumps({'configured': True, 'provider': ref['provider'],
                              'credential_checked': args.probe, 'backend_checked': False}))
        elif args.command == 'set':
            if args.stdin:
                value = sys.stdin.read(65537)
            else:
                if not sys.stdin.isatty(): raise CredentialError('CONFIG_INVALID')
                with warnings.catch_warnings():
                    warnings.simplefilter('error', getpass.GetPassWarning)
                    value = getpass.getpass('Backend credential (hidden): ')
            store(ref, value, replace=args.replace)
            print('Credential stored. Restart MCP after rotation; profile is unchanged.')
        elif args.command == 'delete':
            delete(ref); print('Selected credential deleted; profile is unchanged.')
        elif args.command == 'test-backend':
            configuration(args.environment, path=args.config)
            backend = AST(cfg)
            try: result = backend.get_app(args.app)
            finally: backend.close()
            print(json.dumps({'backend_read_succeeded': True, 'app_exists': result['exists']}))
        elif args.command == 'prepare-keyring':
            ref = validate_reference({'provider': 'keyring', 'service': args.service, 'account': args.account})
            new = {k:v for k,v in cfg.items() if k not in {'oauth','token_env','auth','schema_version'}}
            new.update(schema_version=2, auth={**auth, 'credential':ref})
            args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as handle: json.dump(new, handle, indent=2); handle.write('\n')
            print('New reference-only profile prepared. Existing profile and credentials unchanged. Enroll and verify before switching.')
    except (CredentialError, BackendError) as error:
        print(str(error), file=sys.stderr); return 1
    except Exception:
        print('Local setup failed; check configuration, permissions and selected operation.', file=sys.stderr); return 1
    return 0


if __name__ == '__main__': sys.exit(main())
