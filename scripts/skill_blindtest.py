#!/usr/bin/env python3
"""Blind comprehension check of the shipped skill against measured scenarios.

Reads tests/scenarios/skill_blindtest.json. Two modes:

  --print      print the reader prompt (skill-only instructions + scenarios) so a
               human or any model can answer it; paste the answers into a file
               and judge them with --judge FILE.
  --judge FILE judge answers (one JSON object {scenario_id: answer_text} or a
               markdown file with '## <scenario_id>' headings) against the
               expected/forbidden elements; exit 1 on any miss.
  --ollama MODEL  ask a local Ollama model (http://localhost:11434) each scenario
               with the skill text as context and judge the answers. Nothing
               leaves the machine. Requires the `requests` package.

Judging is lexical and case-insensitive: every `expect_all` phrase must appear,
at least one phrase of every `expect_any` group must appear, no `forbid` phrase
may appear. It is a lexical smoke check only. A semantic review is required for acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'kobil-sdk'
KNOWLEDGE = ROOT / 'src' / 'kobil_sdk_integration' / 'knowledge'
SCENARIOS = ROOT / 'tests' / 'scenarios' / 'skill_blindtest.json'

READER_RULES = (
    "You are an integration engineer who has just installed the KOBIL SDK integration "
    "MCP and its skill. You know nothing about KOBIL beyond the skill text given to you. "
    "Do not call tools, do not access any backend. Answer each scenario strictly from the "
    "skill: decision/next action in 2-4 sentences, which MCP tool(s) you would call first, "
    "the skill section you based it on, and what the skill left open. If the skill does not "
    "say it, write 'skill does not say'. Do not invent."
)


def load_scenarios() -> list[dict]:
    return json.loads(SCENARIOS.read_text(encoding='utf-8'))['scenarios']


def skill_text() -> str:
    parts = [(SKILL / 'SKILL.md').read_text(encoding='utf-8')]
    for f in sorted((SKILL / 'references').glob('*.md')):
        parts.append(f'\n\n# references/{f.name}\n' + f.read_text(encoding='utf-8'))
    for f in sorted(KNOWLEDGE.glob('*.json')):
        parts.append(f'\n\n# knowledge/{f.name}\n' + f.read_text(encoding='utf-8'))
    return '\n'.join(parts)


def judge(answers: dict[str, str], scenarios: list[dict]) -> int:
    failures = 0
    for sc in scenarios:
        text = re.sub(r'\s+', ' ', answers.get(sc['id'], '')).lower()
        misses = []
        if not text:
            misses.append('no answer')
        for phrase in sc.get('expect_all', []):
            if phrase.lower() not in text:
                misses.append(f'missing: {phrase}')
        for group in sc.get('expect_any', []):
            if not any(p.lower() in text for p in group):
                misses.append(f'missing one of: {group}')
        for phrase in sc.get('forbid', []):
            if phrase.lower() in text:
                misses.append(f'forbidden: {phrase}')
        status = 'PASS' if not misses else 'FAIL'
        failures += bool(misses)
        print(f'{status}  {sc["id"]}')
        for m in misses:
            print(f'       - {m}')
    print(f'\n{len(scenarios) - failures}/{len(scenarios)} lexical checks passed; semantic review still required')
    return 1 if failures else 0


def parse_answers(path: Path) -> dict[str, str]:
    raw = path.read_text(encoding='utf-8')
    if path.suffix == '.json':
        return json.loads(raw)
    answers: dict[str, str] = {}
    current = None
    for line in raw.splitlines():
        m = re.match(r'^##\s+(\S+)', line)
        if m:
            current = m.group(1)
            answers[current] = ''
        elif current:
            answers[current] += line + '\n'
    return answers


def ask_ollama(model: str, scenarios: list[dict]) -> dict[str, str]:
    import requests  # local only

    context = skill_text()
    answers = {}
    for sc in scenarios:
        prompt = f"{READER_RULES}\n\n<skill>\n{context}\n</skill>\n\nSCENARIO: {sc['prompt']}"
        r = requests.post('http://localhost:11434/api/generate',
                          json={'model': model, 'prompt': prompt, 'stream': False}, timeout=600)
        r.raise_for_status()
        answers[sc['id']] = r.json().get('response', '')
        print(f'answered {sc["id"]}', file=sys.stderr)
    return answers


def scenario_digest(scenario: dict) -> str:
    return hashlib.sha256(json.dumps(scenario, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def candidate_digest() -> str:
    """Hash delivered behavior/guidance, including dirty changes, independently of Git HEAD."""
    digest = hashlib.sha256()
    paths = [ROOT / 'pyproject.toml']
    for folder in ('src', 'skills', 'docs', 'scripts'):
        paths.extend(p for p in (ROOT / folder).rglob('*')
                     if p.is_file() and p.suffix in ('.py', '.md', '.json', '.toml'))
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def review_answers(answers: dict[str, str], reviews: dict, scenarios: list[dict]) -> int:
    """Require independent, answer-bound review; never equate keywords to correctness."""
    failures = []
    if not isinstance(reviews, dict):
        print('FAIL: review must be a JSON object')
        return 1
    current_candidate = candidate_digest()
    for sc in scenarios:
        answer = answers.get(sc['id'], '')
        review = reviews.get(sc['id'], {})
        digest = hashlib.sha256(answer.encode()).hexdigest()
        if not isinstance(review, dict) or not answer or review.get('answer_sha256') != digest or review.get('scenario_sha256') != scenario_digest(sc) or review.get('candidate_sha256') != current_candidate:
            failures.append(sc['id'] + ': missing answer or stale answer/scenario/candidate review')
            continue
        if review.get('verdict') != 'pass' or not all(
                isinstance(review.get(k), str) and review[k].strip()
                for k in ('reviewer', 'rationale', 'source_evidence')):
            failures.append(sc['id'] + ': semantic pass with reviewer, rationale and source evidence required')
    for failure in failures:
        print('FAIL ' + failure)
    print(f'{len(scenarios) - len(failures)}/{len(scenarios)} semantic reviews accepted')
    return int(bool(failures))


def reader_packet(scenarios: list[dict], retrieval: bool = False) -> dict:
    """No evaluator-only fields in the material delivered to the reader."""
    rules = READER_RULES if not retrieval else (
        'Use only the installed KOBIL SDK skill and read-only bundled knowledge tools. '
        'No external source checkouts, previous session, backend writes or device actions. '
        'For each question record the decision/config fragment, exact resource or tool '
        'and arguments used, supporting section, missing prerequisites and uncertainty. '
        'Report package version and distinguish retrieved knowledge from runtime proof.'
    )
    return {'mode': 'retrieval' if retrieval else 'comprehension', 'rules': rules,
            'candidate_sha256': candidate_digest(),
            'scenarios': [{'id': s['id'], 'prompt': s['prompt']} for s in scenarios]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--packet', choices=['comprehension', 'retrieval'], help='print a reader-only JSON question packet')
    g.add_argument('--review', type=Path, help='validate independent semantic review JSON against --answers')
    ap.add_argument('--answers', type=Path, help='answers evaluated by --review')
    g.add_argument('--print', action='store_true', help='print the reader prompt')
    g.add_argument('--judge', type=Path, metavar='FILE', help='judge answers from FILE')
    g.add_argument('--ollama', metavar='MODEL', help='ask a local Ollama model and judge')
    ap.add_argument('--save', type=Path, help='with --ollama: save raw answers as JSON')
    args = ap.parse_args(argv)
    scenarios = load_scenarios()
    if args.packet:
        print(json.dumps(reader_packet(scenarios, args.packet == 'retrieval'), indent=2))
        return 0
    if args.review:
        if not args.answers:
            ap.error('--review requires --answers')
        return review_answers(parse_answers(args.answers), json.loads(args.review.read_text()), scenarios)
    if args.print:
        print(READER_RULES)
        print('\nRead only SKILL.md, references/*.md and knowledge/*.json of the installed skill.\n')
        for sc in scenarios:
            print(f'## {sc["id"]}\n{sc["prompt"]}\n')
        return 0
    if args.judge:
        return judge(parse_answers(args.judge), scenarios)
    answers = ask_ollama(args.ollama, scenarios)
    if args.save:
        args.save.write_text(json.dumps(answers, indent=2, ensure_ascii=False), encoding='utf-8')
    return judge(answers, scenarios)


if __name__ == '__main__':
    sys.exit(main())
