#!/usr/bin/env python3
"""Sort every routable raw-Bash op in the transcript corpus into three buckets.

Unit = one transcript file (a session or a subagent). For each tool family:
  never_considered : skill never loaded AND tool never called in this unit
  before_engaged   : op ran before the first skill load / tool call
  after_engaged    : op ran after engagement  -> split covered / uncovered
  unavailable      : the skill is absent from that file's skill listing

Every bucket is also split by session (ses:) and subagent (sub:).
Op classification is regex over Bash text; heredoc bodies can match falsely.

Usage:  python3 scripts/bypass_buckets.py      # whole ~/.claude/projects corpus
See also: scripts/bypass_probe.py, scripts/score_spike.py
"""
import json, re, sys, glob, os, collections

ROOT = os.path.expanduser('~/.claude/projects')
CACHE = os.path.expanduser('~/.cache/claude-cli-nodejs')

# op classifiers on each Bash segment (split on && ; | newlines)
SEG = re.compile(r'\s*(?:&&|\|\||;|\n)\s*')
def classify(seg, piped):
    s = seg.strip().lstrip('(').strip()
    s = re.sub(r'^(cd \S+\s*)', '', s)
    w = s.split()
    if not w: return None
    c = w[0]
    if c == 'git':
        sub = next((x for x in w[1:] if not x.startswith('-') and x not in ('-C',)), '')
        if '-C' in w: sub = w[w.index('-C') + 2] if len(w) > w.index('-C') + 2 else ''
        return ('jetsam', 'git ' + sub)
    if c == 'gh':
        return ('jetsam', 'gh ' + ' '.join(w[1:3]))
    if c in ('cat', 'head', 'tail', 'less') and not piped and len(w) > 1:
        return ('duckeye', c)
    if c == 'sed' and '-n' in w:
        return ('duckeye', 'sed -n')
    if c in ('grep', 'rg') and not piped and any(x in w for x in ('-r', '-R', '-rn', '-rl', '-rli', '-rni')) or c == 'rg' and not piped:
        return ('squackit', c + ' -r')
    if c == 'find' and not piped:
        return ('squackit', 'find')
    if re.match(r'(python3? -m )?pytest|make\b|cargo (test|build)|npm (test|run)', s):
        return ('blq', w[0] if w[0] != 'python' else 'pytest')
    return None

# what jetsam's verbs cover (everything else is a coverage gap)
JETSAM_COVERED = re.compile(r'^git (status|add|commit|push|pull|fetch|log|diff|checkout|switch|branch|tag|merge|rebase|stash)$'
                            r'|^gh (pr \w+|issue list|issue close|release create)$')
FAMILY_PREFIX = {'jetsam': 'plugin_jetsam', 'squackit': 'plugin_squackit', 'blq': 'plugin_blq', 'duckeye': None}

def load_connected():
    """sessionId -> set of plugin servers that connected."""
    conn = collections.defaultdict(set)
    for f in glob.glob(f'{CACHE}/*/mcp-logs-plugin-*/*.jsonl'):
        srv = f.split('mcp-logs-plugin-')[1].split('/')[0].split('-')[0]
        sid = None; ok = False
        with open(f, errors='replace') as fh:
            for l in fh:
                if '"sessionId"' in l and sid is None:
                    m = re.search(r'"sessionId":"([^"]+)"', l); sid = m and m.group(1)
                if 'uccessfully connected' in l: ok = True
        if sid and ok: conn[sid].add(srv)
    return conn

def units():
    for f in glob.glob(f'{ROOT}/*/*.jsonl'): yield f, 'session'
    for f in glob.glob(f'{ROOT}/*/*/subagents/**/agent-*.jsonl', recursive=True): yield f, 'subagent'

def main():
    conn = load_connected()
    B = collections.Counter()               # (family, bucket) -> ops
    U = collections.defaultdict(set)        # (family, bucket) -> units
    gaps = collections.Counter(); kinds = collections.Counter()
    n_units = collections.Counter(); has_conn_data = 0
    for f, kind in units():
        n_units[kind] += 1
        sid = None; events = []             # ordered: ('engage', fam) | ('op', fam, op)
        offered = set()
        with open(f, errors='replace') as fh:
            for l in fh:
                if sid is None:
                    m = re.search(r'"sessionId":"([^"]+)"', l); sid = m and m.group(1)
                for fam in ('duckeye-workflow', 'squackit-workflow', 'jetsam-workflow', 'blq-workflow'):
                    if fam in l: offered.add(fam.split('-')[0])
                try: e = json.loads(l)
                except Exception: continue
                m = e.get('message') or {}
                if e.get('type') != 'assistant' or not isinstance(m.get('content'), list): continue
                for c in m['content']:
                    if c.get('type') != 'tool_use': continue
                    n, i = c['name'], c.get('input') or {}
                    if n == 'Skill':
                        sk = str(i.get('skill', ''))
                        for fam in FAMILY_PREFIX:
                            if fam in sk: events.append(('engage', fam))
                    elif n.startswith('mcp__'):
                        for fam, p in FAMILY_PREFIX.items():
                            if p and p in n: events.append(('engage', fam))
                    elif n == 'Bash':
                        cmd = str(i.get('command', ''))
                        if re.match(r'\s*(cd \S+ && )?(duckeye|dep)\b', cmd): events.append(('engage', 'duckeye'))
                        for line in cmd.split('\n'):
                            parts = line.split('|')
                            for k, part in enumerate(parts):
                                for seg in SEG.split(part):
                                    r = classify(seg, piped=k > 0)
                                    if r: events.append(('op',) + r)
        if sid in conn: has_conn_data += 1
        engaged = set()
        ever = {ev[1] for ev in events if ev[0] == 'engage'}
        for ev in events:
            if ev[0] == 'engage': engaged.add(ev[1]); continue
            _, fam, op = ev
            if fam not in ever and fam not in offered: b = 'unavailable'
            elif fam not in ever: b = 'never_considered'
            elif fam not in engaged: b = 'before_engaged'
            else:
                b = 'after_engaged'
                if fam == 'jetsam':
                    b += '/covered' if JETSAM_COVERED.match(op) else '/uncovered'
                    if not JETSAM_COVERED.match(op): gaps[op] += 1
            B[(fam, kind[:3] + ":" + b)] += 1; U[(fam, kind[:3] + ":" + b)].add(f); kinds[(fam, op)] += 1
    print(f'units: {dict(n_units)}   units with MCP connection log: {has_conn_data}')
    print(f'{"family":9} {"bucket":28} {"ops":>6} {"units":>6}')
    for (fam, b) in sorted(B): print(f'{fam:9} {b:28} {B[(fam,b)]:>6} {len(U[(fam,b)]):>6}')
    print('\njetsam coverage gaps after engagement (top 15):')
    for op, c in gaps.most_common(15): print(f'  {c:5} {op}')
    print('\ntop raw ops per family:')
    for fam in FAMILY_PREFIX:
        top = sorted(((c, op) for (f2, op), c in kinds.items() if f2 == fam), reverse=True)[:6]
        print(f'  {fam}: ' + ', '.join(f'{op}×{c}' for c, op in top))

if __name__ == '__main__': main()
