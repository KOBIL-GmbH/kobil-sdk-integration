#!/usr/bin/env python3
"""Fail when person, internal-source or ticket references reach shipped history.

Scans every blob reachable from the given refs (default HEAD), commit messages
and author/committer/tagger identities. Used by CI and as a pre-push hook.

Names of people are not stored in this repository: set FORBIDDEN_NAMES to a
regular expression (CI: repository/organization variable) to include them.
Matched person tokens are never printed.

usage: leak_scan.py [--tip] [repo] [ref ...]
"""
import os
import re
import subprocess
import sys
from collections import defaultdict

ALLOWED_IDENTITY = ('KOBIL SDK Contributors', 'contributors@example.invalid', 'GitHub', 'noreply@github.com')
EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
EMAIL_OK = re.compile(r'(example\.(?:com|org|invalid)|\.example\b|\.test\b|\.invalid\b|noreply)')
# Native, server or Flutter/Dart source files; public SDK headers (.h) are API, not source.
SRC = re.compile(r'[A-Za-z0-9_./-]+\.(?:cc|cpp|cxx|hpp|java|mm|dart)(?::\d+(?:-\d+)?)?\b')
# Swift/Kotlin files may only be cited from the GettingStarted samples.
SRC_MOBILE = re.compile(r'[A-Za-z0-9_./-]+/[A-Za-z0-9_.-]+\.(?:swift|kt)\b')
SRC_ALLOWED = re.compile(r'(gettingstarted|integratedui|integratedunit|positiveflow)', re.I)
TICKET = re.compile(r'\b(?:AK|DS|CBE|IDP|SDSH|KHC|WLA)-\d{2,5}\b')
NAMES = re.compile(os.environ['FORBIDDEN_NAMES'], re.I) if os.environ.get('FORBIDDEN_NAMES') else None


def git(repo, *args, data=None):
    return subprocess.run(['git', '-C', repo, *args], capture_output=True, input=data, check=True).stdout


def scan_text(label, text, hits, redact_names=True):
    for m in SRC.finditer(text):
        hits['source reference'].add((label, m.group(0)))
    for m in SRC_MOBILE.finditer(text):
        if not SRC_ALLOWED.search(m.group(0)):
            hits['source reference'].add((label, m.group(0)))
    for m in TICKET.finditer(text):
        hits['ticket key'].add((label, m.group(0)))
    for m in EMAIL.finditer(text):
        if not EMAIL_OK.search(m.group(0)):
            hits['e-mail address'].add((label, m.group(0)))
    if NAMES and NAMES.search(text):
        hits['person reference'].add((label, '<redacted>' if redact_names else NAMES.search(text).group(0)))


def main(argv):
    tip = '--tip' in argv
    argv = [a for a in argv if a != '--tip']
    repo = argv[0] if argv else '.'
    refs = argv[1:] or ['HEAD']
    hits = defaultdict(set)
    if tip:
        listing = git(repo, 'ls-tree', '-r', '-z', refs[0]).split(b'\0')
        entries = {}
        for e in listing:
            if e:
                meta, path = e.split(b'\t', 1)
                entries[meta.split()[2].decode()] = path.decode()
    else:
        entries = {}
        for line in git(repo, 'rev-list', '--objects', *refs).decode().splitlines():
            parts = line.split(' ', 1)
            if len(parts) == 2:
                entries[parts[0]] = parts[1]
    check = git(repo, 'cat-file', '--batch-check', data=('\n'.join(entries) + '\n').encode()).decode().splitlines()
    blob_ids = [c.split()[0] for c in check if ' blob ' in c]
    blob = subprocess.run(['git', '-C', repo, 'cat-file', '--batch'], capture_output=True,
                          input=('\n'.join(blob_ids) + '\n').encode(), check=True).stdout
    i = 0
    while i < len(blob):
        nl = blob.index(b'\n', i)
        sha, _, size = blob[i:nl].decode().split()
        size = int(size)
        body = blob[nl + 1:nl + 1 + size]
        i = nl + 1 + size + 1
        if b'\0' in body[:2000]:
            continue
        scan_text(entries.get(sha, '?'), body.decode('utf-8', 'replace'), hits)
    if not tip:
        fmt = '%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e'
        for rec in git(repo, 'log', '--format=' + fmt, *refs).decode().split('\x1e'):
            f = rec.strip('\n').split('\x1f')
            if len(f) < 6:
                continue
            sha, an, ae, cn, ce, msg = f
            label = 'commit ' + sha[:8]
            for who in (an, ae, cn, ce):
                if who and not any(a in who for a in ALLOWED_IDENTITY):
                    hits['author identity'].add((label, '<redacted>'))
            scan_text(label + ' message', msg, hits)
        for ref in git(repo, 'for-each-ref', '--format=%(refname:short)%1f%(taggername)%1f%(taggeremail)%1f%(contents)', 'refs/tags').decode().split('\n'):
            f = ref.split('\x1f')
            if len(f) == 4:
                for who in f[1:3]:
                    who = who.strip()
                    if who and not any(a in who for a in ALLOWED_IDENTITY):
                        hits['author identity'].add(('tag ' + f[0], '<redacted>'))
                scan_text('tag ' + f[0] + ' message', f[3], hits)
    total = sum(len(v) for v in hits.values())
    for kind, items in sorted(hits.items()):
        print(f'{kind}: {len(items)}')
        for label, token in sorted(items)[:15]:
            print(f'   {label}: {token}')
    print('clean' if total == 0 else f'{total} finding(s)')
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
