"""IDE entry point. The project is the folder the host opened, so a new app needs no new plug-in setup.

An IDE host that starts the server from a project (Xcode starts its agent in the project folder) is followed
when that folder holds an Xcode project or workspace: a binding fixed at import time (KOBIL_SDK_PROJECT) is
then stale for every later app. Without such a folder the explicit binding is used. Never taken from the
working directory: the home directory, the filesystem root and any folder without an Xcode project, because a GUI
host can start the server anywhere.
"""
import os
from pathlib import Path

MARKERS = ('.xcodeproj', '.xcworkspace')


def _is_project_folder(folder):
    try:
        return any(entry.suffix in MARKERS for entry in folder.iterdir())
    except OSError:
        return False


def resolve_project(env, cwd):
    """Return (project folder, source) with source 'cwd' or 'env'; raise PROJECT_NOT_SELECTED otherwise."""
    folder = Path(cwd).resolve()
    bound = env.get('KOBIL_SDK_PROJECT')
    if bound and Path(bound).is_absolute() and Path(bound).is_dir() and Path(bound).resolve() == folder:
        return folder, 'env'
    if folder not in (Path.home().resolve(), Path(folder.anchor)) and _is_project_folder(folder):
        return folder, 'cwd'
    if bound and Path(bound).is_absolute() and Path(bound).is_dir():
        return Path(bound).resolve(), 'env'
    raise ValueError('PROJECT_NOT_SELECTED: start the agent in the folder of the Xcode project, or regenerate the '
                     'IDE setup for an existing absolute project path')


def main():
    project, source = resolve_project(os.environ, Path.cwd())
    os.environ['KOBIL_SDK_PROJECT'] = str(project)
    os.environ['KOBIL_SDK_PROJECT_SOURCE'] = source
    from .server import main as run
    run()


if __name__ == '__main__':
    main()
