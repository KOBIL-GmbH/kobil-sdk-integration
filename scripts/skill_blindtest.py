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
may appear. It is a release gate for the guidance text, not a unit test.
"""
from __future__ import annotations

import argparse
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
    print(f'\n{len(scenarios) - failures}/{len(scenarios)} scenarios passed')
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--print', action='store_true', help='print the reader prompt')
    g.add_argument('--judge', type=Path, metavar='FILE', help='judge answers from FILE')
    g.add_argument('--ollama', metavar='MODEL', help='ask a local Ollama model and judge')
    ap.add_argument('--save', type=Path, help='with --ollama: save raw answers as JSON')
    args = ap.parse_args(argv)
    scenarios = load_scenarios()
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
