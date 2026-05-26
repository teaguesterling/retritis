"""Code-nav / FTS latency probe for C-workstream scenarios. Run with cwd=<fixture>.
Measures the cold connect + rebuild_fts (+ optional query) cost — exactly what the
persistent substrate (workstream C) should turn into a cache hit. Prints a short line;
checks.py captures the subprocess walltime as latency_ms."""
import sys
import fledgling

mode = sys.argv[1] if len(sys.argv) > 1 else "search"
c = fledgling.connect(root=".")
c.rebuild_fts()
if mode == "search":
    r = c._con.execute("SELECT * FROM search_content('connect') LIMIT 3").fetchall()
    assert r, "no FTS hits for 'connect'"
    print("search_content hits", len(r))
elif mode == "build":
    n = c._con.execute("SELECT count(*) FROM fts.content").fetchone()[0]
    assert n > 0, "FTS index empty after rebuild"
    print("fts rows", n)
else:
    raise SystemExit(f"unknown mode {mode}")
