"""The look of the app as words, served by the MCP. An owner's own theme replaces the bundled default.

Order, first hit wins: a file named by KOBIL_SDK_THEME, the project's .kobil-sdk/theme.md, the owner's theme.md in the
state directory (~/.kobil-sdk), the bundled default. The text is plain Markdown without code; the tools never return
absolute paths and refuse text that looks like a credential.
"""
import os
import re
from pathlib import Path

MAX_CHARS = 24000
SCOPES = ('project', 'user')
SECRET_SHAPES = (
    re.compile(r'eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]*'),
    re.compile(r'(?i)\b(bearer|basic)\s+[\w.~+/=-]{12,}'),
    re.compile(r'(?i)\b(password|passwd|pwd|secret|token|apikey|api_key)\s*[=:]\s*\S{4,}'),
    re.compile(r'\b[A-Za-z0-9+/_-]{40,}={0,2}'),
)
HOW_TO_REPLACE = ('To use your own theme: sdk_theme_set(theme_markdown) writes it for this project (scope "project") or for '
                  'every project of this user (scope "user"); sdk_theme_reset removes it again. Keep the same headings and '
                  'tables so agents find the values by role. A theme file named by KOBIL_SDK_THEME beats both.')


def default_text():
    return (Path(__file__).parent / 'knowledge' / 'theme-default.md').read_text()


def _state_dir(env):
    return Path(env.get('KOBIL_SDK_HOME') or Path.home() / '.kobil-sdk')


def _project(env):
    project = env.get('KOBIL_SDK_PROJECT')
    if not project or not Path(project).is_absolute() or not Path(project).is_dir():
        raise ValueError('PROJECT_NOT_SELECTED: the project scope needs an existing project folder')
    return Path(project)


def _file(scope, env):
    if scope == 'project':
        return _project(env) / '.kobil-sdk' / 'theme.md'
    if scope == 'user':
        return _state_dir(env) / 'theme.md'
    raise ValueError('scope must be "project" or "user"')


def _read(path):
    try:
        text = Path(path).read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    return text if text.strip() and '\x00' not in text else None


def load(env=None):
    """The theme in force: {'source': 'env'|'project'|'user'|'default', 'text': ...}."""
    env = os.environ if env is None else env
    if env.get('KOBIL_SDK_THEME'):
        text = _read(env['KOBIL_SDK_THEME'])
        if text:
            return {'source': 'env', 'text': text}
    for scope in SCOPES:
        try:
            text = _read(_file(scope, env))
        except ValueError:
            text = None
        if text:
            return {'source': scope, 'text': text}
    return {'source': 'default', 'text': default_text()}


def sections(text):
    return re.findall(r'^##\s+(.+)$', text, re.M)


def _validate(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('The theme text is empty')
    if len(text) > MAX_CHARS:
        raise ValueError('The theme is longer than %d characters; keep it to what an agent needs' % MAX_CHARS)
    if '\x00' in text:
        raise ValueError('The theme must be plain text')
    for shape in SECRET_SHAPES:
        if shape.search(text):
            raise ValueError('The theme text contains something that looks like a credential; remove it')


def save(text, scope, env=None):
    env = os.environ if env is None else env
    _validate(text)
    path = _file(scope, env)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        handle.write(text if text.endswith('\n') else text + '\n')
    os.chmod(path, 0o600)
    return {'saved': True, 'scope': scope, 'characters': len(text)}


def reset(scope, env=None):
    env = os.environ if env is None else env
    path = _file(scope, env)
    try:
        path.unlink()
        return {'removed': True, 'scope': scope}
    except FileNotFoundError:
        return {'removed': False, 'scope': scope}
