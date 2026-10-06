# Knowledge interrogation before building apps

Test a fresh reader's integration decisions before a mobile build. The question
bank has 46 scenarios: simulator/device policy, configuration prerequisites,
IDP endpoint/client selection, activation recovery, WebView headers and trust,
SignedJWT evidence, TMS, SDK errors, delivery scope, lifecycle and log export.

## Run a blind interview

Use a clean reader session with the candidate MCP/skill, no prior conversation,
internal source checkout or answer key. Record the package version/commit and
whether the working tree is modified. Do not give the reader the scenario JSON:
it contains evaluator-only expectations.

Export a reader-only packet:

```sh
python scripts/skill_blindtest.py --packet retrieval > questions.json
```

`retrieval` asks the reader to discover the installed read-only knowledge tools
and record their arguments, returned resources and supporting sections.
`--packet comprehension` instead tests reading supplied shipped documentation.
Neither mode authorizes backend mutations or device operations. The packet
command creates questions; it does not execute an agent.

Save answers as a JSON object mapping scenario IDs to answer text, or Markdown
with `## scenario-id` headings. Answers should contain:

- Decision and, where appropriate, a configuration fragment.
- Supporting shipped knowledge section and retrieved tool/resource evidence.
- Prerequisites and the next diagnostic action.
- Unknowns and the boundary between documentation and measured runtime proof.

A complete configuration requires delivery-qualified schema and deployment
inputs. A partial fragment with explicit missing inputs is preferable to a
fabricated complete file. Check produced configuration against that delivery's
schema; these interview harness tests do not certify generated app assets.

## Evaluate independently

```sh
python scripts/skill_blindtest.py --judge answers.json
```

This is only a lexical smoke check. Keywords can be present in a wrong or
contradictory answer. A pass is not semantic acceptance. Review each answer
against `review_criteria`, correct release-qualified behavior and recorded tool
retrieval. Do not force a correct answer to use one exact phrase.

Save a separate evaluator JSON keyed by scenario ID. Each entry requires
`answer_sha256` (SHA-256 of the exact UTF-8 answer text),
`scenario_sha256` (canonical sorted compact JSON of the complete evaluator scenario),
`candidate_sha256` (from the reader packet; the validator rehashes the source/guidance), `verdict` (`pass` or
`fail`), `reviewer`, `rationale`, and `source_evidence`. Do not give this file to
the reader. Changed answers, scenario/rubric or candidate content invalidate earlier reviews.

```sh
python scripts/skill_blindtest.py --review reviews.json --answers answers.json
```

The review validator checks completeness and answer binding; it cannot determine
whether the reviewer is independent or the rationale is correct. Require real
review, not automatically populated pass records. Retain failed answers and
rationales. Rephrase cases and change one input at a time for a further blind
round. Missing knowledge is a finding, not permission to invent an answer.

## Deterministic regressions

`tests/test_knowledge_interrogation.py` verifies reader/evaluator separation,
review integrity and discovery/retrieval through registered MCP knowledge
handlers, including unsupported platform/version boundaries. It is not a live
model interview or a transport/end-to-end MCP-client test. The protocol suite
separately checks stdio registration.

The IDP catalog tests inject timeout and backend exceptions after a dispatched
write and reject retry or swallowed failure for minimally reachable mutations.
They do not cover every optional argument or real backend authorization policy.
Log-marker regressions reject mismatched request IDs, unrelated endpoints,
out-of-order responses and intervening SDK operations. Log chronology is not a
universal causal proof: ambiguous/multiplexed formats need stronger evidence.
