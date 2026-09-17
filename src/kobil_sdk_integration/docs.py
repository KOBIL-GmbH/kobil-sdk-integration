"""Serve the integration method to clients that cannot load a skill file.

A skill is only read by agents whose client supports skills. Every other MCP client
sees the tools and no method at all, which is how an agent ends up guessing an IDP
client id or a platform value. These helpers return the same text as tool output.
"""
from pathlib import Path

MAX_BYTES = 60000


def _skill_dir():
    for root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]):
        candidate = root / 'skills' / 'kobil-sdk'
        if (candidate / 'SKILL.md').is_file():
            return candidate
    raise RuntimeError('Integration documentation is not bundled with this installation')


def catalog():
    """Section name -> file, without reading any of them."""
    skill = _skill_dir()
    found = {'workflow': skill / 'SKILL.md'}
    for path in sorted((skill / 'references').glob('*.md')):
        found[path.stem] = path
    return found


def read(section=None):
    """Return one section, or the index plus the workflow when none is named.

    Never returns every section at once: a full dump exceeds the result cap of
    several MCP clients, which truncate silently and leave a partial method.
    """
    found = catalog()
    if section is not None:
        if not isinstance(section, str) or section not in found:
            raise ValueError('Unknown documentation section')
        names = [section]
    else:
        names = ['workflow']
    out, total = {}, 0
    for name in names:
        text = found[name].read_text(encoding='utf-8')
        if total + len(text.encode('utf-8')) > MAX_BYTES:
            raise RuntimeError('Documentation section exceeds the result size limit')
        total += len(text.encode('utf-8'))
        out[name] = text
    return {'sections_available': sorted(found), 'returned': out,
            'note': 'Read "workflow" first, then the section for the task in hand.'}
