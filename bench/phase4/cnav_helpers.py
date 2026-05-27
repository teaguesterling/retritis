"""Code-nav / FTS latency probe for C-workstream scenarios. Run with cwd=<fixture>.

OFF (no FLEDGLING_PERSIST): cold in-memory connect + full rebuild_fts (+ optional
query) — the unaided ~4 s cost. ON (FLEDGLING_PERSIST set, workstream C): build the
file-backed cache on first miss (staleness-aware, ~no-op when fresh), then open it
read-only and query with no rebuild — the cache hit. checks.py captures the subprocess
walltime as latency_ms."""
import os
import sys

import fledgling

mode = sys.argv[1] if len(sys.argv) > 1 else "search"
persist = os.environ.get("FLEDGLING_PERSIST")

if persist:
    # ON: reader fast-path. Build-on-demand only when the cache is absent (first run);
    # otherwise go straight to a read-only attach + query. Staleness is the BUILDER's
    # job (out-of-band on content/HEAD change) — a per-read git+DB freshness probe would
    # defeat the point of a cheap cache hit, so readers don't pay it.
    if not os.path.exists(persist):
        fledgling.build_cache(persist, root=".")
    c = fledgling.connect(persist=persist, read_only=True, root=".")
else:
    # OFF: cold in-memory connect + full rebuild.
    c = fledgling.connect(root=".")
    c.rebuild_fts()

if mode == "search":
    r = c.con.execute("SELECT * FROM search_content('connect') LIMIT 3").fetchall()
    assert r, "no FTS hits for 'connect'"
    print("search_content hits", len(r))
elif mode == "build":
    n = c.con.execute("SELECT count(*) FROM fts.content").fetchone()[0]
    assert n > 0, "FTS index empty after rebuild"
    print("fts rows", n)
else:
    raise SystemExit(f"unknown mode {mode}")
