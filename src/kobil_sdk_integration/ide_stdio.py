"""IDE entry point: require explicit project binding, never infer GUI cwd."""
import os
from pathlib import Path


def main():
    project = os.environ.get('KOBIL_SDK_PROJECT')
    if not project or not Path(project).is_absolute() or not Path(project).is_dir():
        raise ValueError('PROJECT_NOT_SELECTED: regenerate IDE setup for an existing absolute project path')
    from .server import main as run
    run()


if __name__ == '__main__':
    main()
