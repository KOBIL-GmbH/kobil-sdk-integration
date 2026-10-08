"""Serve the integration method to clients that cannot load a skill file.

A skill is only read by agents whose client supports skills. Every other MCP client
sees the tools and no method at all, which is how an agent ends up guessing an IDP
client id or a platform value. These helpers return the same text as tool output.
"""
from pathlib import Path

MAX_BYTES = 60000
CODE_SUFFIXES = ('.swift', '.kt', '.java', '.h', '.m', '.json')


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
    # Platform guides live in subfolders; serve them under the platform name.
    for path in sorted((skill / 'references').glob('*/README.md')):
        found.setdefault(path.parent.name, path)
    refs = skill / 'references'
    # The bundled official KOBIL documentation, one section per page; "official" is its index.
    for path in sorted((refs / 'official').glob('*.md')):
        if path.name != 'README.md':
            found['official/' + path.stem] = path
    # Reference source files, served under their path (e.g. "ios/email-code/MasterControllerSession.swift").
    for path in sorted(refs.rglob('*')):
        if path.is_file() and path.suffix in CODE_SUFFIXES:
            found.setdefault(path.relative_to(refs).as_posix(), path)
    return found


def read(section=None, offset=0):
    """Return one section, or the section index plus the workflow when none is named.

    Never returns every section at once: a full dump exceeds the result cap of
    several MCP clients, which truncate silently and leave a partial method.
    A section larger than the cap is returned in parts cut at line ends; the
    result then carries next_offset, to be passed back until it is absent.
    """
    found = catalog()
    # The section list comes with the index call only; repeating ~60 names with every page is noise.
    with_index = section is None and offset == 0
    if section is None:
        section = 'workflow'
    elif not isinstance(section, str) or section not in found:
        raise ValueError('Unknown documentation section')
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError('offset must be a non-negative integer')
    text = found[section].read_text(encoding='utf-8')
    if offset > len(text):
        raise ValueError('offset is past the end of the section')
    part, end, used = [], offset, 0
    for line in text[offset:].splitlines(keepends=True):
        size = len(line.encode('utf-8'))
        if used + size > MAX_BYTES and part:
            break
        part.append(line)
        used += size
        end += len(line)
    result = {'returned': {section: ''.join(part)}}
    if with_index:
        # The official pages are listed in the "official" section, not here: 87 names would crowd the reply.
        result['sections_available'] = sorted(name for name in found if not name.startswith('official/'))
        result['note'] = ('Read "workflow" first, then the section for the task in hand. '
                          'Reference source files are listed by path; copy them verbatim. '
                          'The official KOBIL documentation is the "official" section (index) and '
                          '"official/<page>" sections; search it with sdk_official_docs_search. '
                          'Only this call lists the sections.')
    else:
        result['note'] = 'Call sdk_docs() without a section for the list of sections.'
    if end < len(text):
        result['next_offset'] = end
        result['note'] += ' This section continues: call again with offset=next_offset.'
    return result


SCOPES = ('all', 'official', 'guides')


def _page_hits(name, path, words, kind):
    """Lines holding every word, and the page's first line with the first word if the page holds them all."""
    lines = path.read_text(encoding='utf-8').splitlines()
    source = lines[0].split('<', 1)[-1].split('>', 1)[0] if kind == 'official' and lines else None
    lower = [line.lower() for line in lines]
    hit = lambda number: {'section': name, 'kind': kind, 'line': number, 'text': lines[number - 1][:300],
                          'source': source}
    line_hits = [hit(n) for n, line in enumerate(lower, 1) if all(w in line for w in words)]
    page_hit = None
    if all(any(w in line for line in lower) for w in words):
        page_hit = hit(next(i for i, line in enumerate(lower, 1) if words[0] in line))
    return line_hits, page_hit


def search(query, limit=20, scope='all'):
    """Find lines that contain every word of the query, in the official documentation and the guides.

    Case-insensitive. When no single line holds all words, pages that hold them all are
    returned with the first line matching the first word, so a question phrased differently
    from the page still finds it. Official pages and the plugin's guides are ranked
    separately, each up to `limit`: a guide records what was verified on a device (for
    example that the iOS SDK cannot send chat messages), which the official pages leave out.
    """
    if not isinstance(query, str) or not query.split():
        raise ValueError('query must contain at least one word')
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100')
    if scope not in SCOPES:
        raise ValueError('scope is one of: ' + ', '.join(SCOPES))
    words = [w.lower() for w in query.split()]
    kinds = {'official', 'guide'} if scope == 'all' else {'official' if scope == 'official' else 'guide'}
    results = {}
    for kind in ('guide', 'official'):
        if kind not in kinds:
            continue
        if kind == 'official':
            pages = {n: p for n, p in catalog().items() if n.startswith('official/')}
        else:
            pages = {n: p for n, p in catalog().items() if not n.startswith('official/') and p.suffix == '.md'}
        lines_hit, pages_hit = [], []
        for name, path in sorted(pages.items()):
            line_hits, page_hit = _page_hits(name, path, words, kind)
            lines_hit += line_hits
            if page_hit:
                pages_hit.append(page_hit)
        hits = lines_hit or pages_hit
        # Headings name what a page is about, and the overview answers "can the SDK do X";
        # both come first, so a limit of a few results still carries the answer.
        results[kind] = sorted(hits, key=lambda h: (not h['text'].lstrip().startswith('#'),
                                                    h['section'] != 'overview'))
    hits = results.get('guide', [])[:limit] + results.get('official', [])[:limit]
    return {'query': query, 'scope': scope, 'matches': sum(len(v) for v in results.values()),
            'results': hits,
            'note': 'Read a result with sdk_docs(section=...). kind "official" is KOBIL\'s documentation '
                    '(cite its source URL); kind "guide" is this plugin\'s guide, which records what was '
                    'verified on a device. Where either differs from the shipped SDK, sdk_api_lookup '
                    'checks the delivered headers and binary.'}
