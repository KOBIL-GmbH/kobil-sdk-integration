#!/usr/bin/env python3
"""Performance benchmark of the real MCP server over stdio: what takes how long.

Offline tools only (no backend, no network): server start, tool listing, runtime info, service catalog, knowledge
topics, one knowledge page and the iOS knowledge bundle. Every tool is called --runs times after one cold call.
Prints min / p50 / p95 / max per tool (client wall time) and the result size, writes a JSON report and can compare
the p95 values with budgets (exit code 1 when a budget is exceeded).

The server reports to Sentry with the environment 'perf' when a DSN is configured; use --no-sentry to switch that off.
"""
import argparse
import asyncio
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_BUDGETS = HERE / 'perf_budgets.json'
SERVER = 'from kobil_sdk_integration.server import main; main()'


def percentile(values, fraction):
    """Nearest-rank percentile of a non-empty list."""
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def summarize(samples):
    """samples: {name: [seconds, ...]} -> {name: {runs, min_ms, p50_ms, p95_ms, max_ms}}"""
    out = {}
    for name, values in samples.items():
        ms = [v * 1000 for v in values]
        out[name] = {'runs': len(ms), 'min_ms': round(min(ms), 1), 'p50_ms': round(percentile(ms, 0.5), 1),
                     'p95_ms': round(percentile(ms, 0.95), 1), 'max_ms': round(max(ms), 1)}
    return out


def check_budgets(summary, budgets):
    """Return a list of 'name: p95 X ms > budget Y ms' strings for every exceeded budget."""
    problems = []
    tools = budgets.get('tools', {})
    for name, row in summary.items():
        limit = tools.get(name, budgets.get('default_ms'))
        if limit is not None and row['p95_ms'] > limit:
            problems.append('%s: p95 %.1f ms > budget %s ms' % (name, row['p95_ms'], limit))
    return problems


def render(summary, sizes):
    lines = ['%-28s %5s %8s %8s %8s %8s %9s' % ('step', 'runs', 'min ms', 'p50 ms', 'p95 ms', 'max ms', 'bytes')]
    for name, row in summary.items():
        lines.append('%-28s %5d %8.1f %8.1f %8.1f %8.1f %9s' % (name, row['runs'], row['min_ms'], row['p50_ms'],
                                                               row['p95_ms'], row['max_ms'], sizes.get(name, '')))
    return '\n'.join(lines)


async def measure(runs):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    samples, sizes = {}, {}
    params = StdioServerParameters(command=sys.executable, args=['-c', SERVER], env=dict(os.environ))
    began = time.perf_counter()
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            samples['server_start'] = [time.perf_counter() - began]

            async def timed(name, call):
                began = time.perf_counter()
                result = await call()
                samples.setdefault(name, []).append(time.perf_counter() - began)
                sizes[name] = len(json.dumps(result.model_dump(mode='json'), default=str)) if hasattr(result, 'model_dump') else ''
                return result

            await timed('list_tools (cold)', session.list_tools)
            plan = [('sdk_runtime_info', {}), ('sdk_service_catalog', {}), ('sdk_knowledge_topics', {}),
                    ('sdk_knowledge_get', {'topic': 'lifecycle', 'platform': 'ios'}),
                    ('sdk_knowledge_bundle', {'platform': 'ios'})]
            for _ in range(runs):
                await timed('list_tools', session.list_tools)
            for name, args in plan:
                await timed(name + ' (cold)', lambda n=name, a=args: session.call_tool(n, a))
                for _ in range(runs):
                    await timed(name, lambda n=name, a=args: session.call_tool(n, a))
    return samples, sizes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--budgets', default=str(DEFAULT_BUDGETS), help='JSON with default_ms and tools{name: ms}; empty to skip')
    parser.add_argument('--out', help='write the JSON report here')
    parser.add_argument('--no-sentry', action='store_true')
    args = parser.parse_args(argv)
    os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'perf')
    if args.no_sentry:
        os.environ['KOBIL_SDK_SENTRY_DISABLE'] = '1'
    if args.no_sentry:
        # keep the usage log of this run out of the real state directory
        with tempfile.TemporaryDirectory() as home:
            os.environ['KOBIL_SDK_HOME'] = home
            samples, sizes = asyncio.run(measure(args.runs))
    else:
        samples, sizes = asyncio.run(measure(args.runs))
    summary = summarize(samples)
    print(render(summary, sizes))
    report = {'created': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'runs': args.runs, 'python': sys.version.split()[0],
              'platform': sys.platform, 'summary': summary, 'result_bytes': sizes}
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1))
    problems = []
    if args.budgets:
        problems = check_budgets({k: v for k, v in summary.items() if '(cold)' not in k}, json.loads(Path(args.budgets).read_text()))
    for line in problems:
        print('BUDGET EXCEEDED', line)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
