#!/usr/bin/env python3
"""Score subagent transcripts: suite tool use vs routable raw Bash, per label.

Used to test dispatch-prompt variants and the "Name the tool for every step"
rule (2026-10-18). Built-in Read/Grep/Glob are counted separately from Bash.

Usage:  python3 scripts/score_spike.py LABEL=path/to/agent.jsonl [LABEL=...]
"""
import json, sys, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from bypass_buckets import classify, SEG

for label_path in sys.argv[1:]:
    label, path = label_path.split('=', 1)
    tools = collections.Counter(); raw = collections.Counter(); skills = []
    for l in open(path, errors='replace'):
        try: e = json.loads(l)
        except Exception: continue
        m = e.get('message') or {}
        if e.get('type') != 'assistant' or not isinstance(m.get('content'), list): continue
        for c in m['content']:
            if c.get('type') != 'tool_use': continue
            n, i = c['name'], c.get('input') or {}
            if n == 'Skill': skills.append(i.get('skill'))
            if n.startswith('mcp__plugin_'): tools[n.split('__')[1].replace('plugin_', '').split('_')[0]] += 1
            elif n == 'Bash':
                cmd = str(i.get('command', ''))
                if cmd.lstrip().startswith(('duckeye', 'dep ')): tools['duckeye'] += 1
                for line in cmd.split('\n'):
                    for k, part in enumerate(line.split('|')):
                        for seg in SEG.split(part):
                            r = classify(seg, piped=k > 0)
                            if r: raw[r[0]] += 1
            else: tools['builtin:' + n] += 1
    suite = sum(v for k, v in tools.items() if not k.startswith('builtin:'))
    print(f'{label}: suite calls={suite} raw routable={sum(raw.values())} skills={skills}')
    print(f'    tools={dict(tools)}  raw={dict(raw)}')
