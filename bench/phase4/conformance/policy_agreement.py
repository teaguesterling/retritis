"""B-workstream conformance test (skeleton).

One `.umw`, two enforcers: kibitzer and lackpy must agree with the umwelt
`PolicyEngine` ground truth on **every** (tool, path) verdict. **Zero divergence is
the safety gate** (phase-4.md §3) — a disagreement means the agent believes it's
sandboxed differently than enforcement allows.

STATUS: skeleton. `gen_cases` + the assertion harness are real and runnable today
(`python policy_agreement.py`). The three verdict-getters need a **compiled
`policy.db`** — workstream B wires `umwelt compile <.umw> -> policy.db` and points
kibitzer's `PolicyConsumer.from_db` and lackpy's `policy/sources/umwelt` at it. Until
that exists the pytest test **skips (pending)**, so it never falsely passes.
"""
from __future__ import annotations

import itertools
import os
from pathlib import Path

POLICY_DB = Path(os.environ.get("PHASE4_POLICY_DB", ".umwelt/policy.db"))


# ── corpus generation (real, runnable) ──────────────────────────────────────
def gen_cases(writable_prefixes, tools, *, fuzz_paths=None):
    """Boundary-rich (tool, path) cases from a policy's writable prefixes + tool set.

    For each prefix `p`: just-inside, deeper, the dir itself, its parent, a look-alike
    sibling, plus clearly-outside paths — crossed with every tool, plus a fuzz tail.
    Exhaustiveness here is what makes "zero divergence" meaningful (phase-4.md §3 T2):
    don't hand-pick easy cases.
    """
    paths: list[str] = []
    for p in writable_prefixes:
        p = p.rstrip("/")
        parent = str(Path(p).parent) if "/" in p else "."
        paths += [f"{p}/inside.py", f"{p}/sub/deep.py", p, parent, f"{p}_sibling/x.py"]
    paths += ["totally/unrelated/x.py", "README.md", "/etc/passwd"]
    paths += fuzz_paths or []
    return [(t, pth) for t, pth in itertools.product(sorted(set(tools)), sorted(set(paths)))]


def _path_writable(writable: list[str], path: str) -> bool:
    return writable == ["*"] or any(path.startswith(w.rstrip("/")) for w in writable)


def _truthy_allow(v) -> bool:
    return v not in (False, "false", "False", 0)


# ── verdict getters (need a compiled policy.db — workstream B) ───────────────
def verdict_truth(tool: str, path: str, mode: str) -> str:
    """Ground truth, straight from umwelt's PolicyEngine."""
    from umwelt.policy import PolicyEngine

    eng = PolicyEngine.from_db(POLICY_DB)
    mp = eng.resolve(type="mode", id=mode, context={"mode": mode}) or {}
    tp = eng.resolve(type="tool", id=tool, context={"mode": mode}) or {}
    ok = _path_writable(mp.get("writable", ["*"]), path) and _truthy_allow(tp.get("allow", True))
    return "allow" if ok else "deny"


def verdict_kibitzer(tool: str, path: str, mode: str) -> str:
    """As kibitzer enforces it — via the same PolicyConsumer it uses at hook time."""
    from kibitzer.umwelt.consumer import PolicyConsumer

    pc = PolicyConsumer.from_db(POLICY_DB)
    mp = pc.get_mode_policy(mode, active_mode=mode)
    tp = pc.get_tool_policy(tool, active_mode=mode)
    ok = _path_writable(mp.writable if mp else ["*"], path) and _truthy_allow(tp.get("allow", True))
    return "allow" if ok else "deny"


def verdict_lackpy(tool: str, path: str, mode: str) -> str:
    """As lackpy validates generated programs against the SAME policy.db.

    TODO(workstream B): wire `lackpy.policy.sources.umwelt` against POLICY_DB and map its
    result to allow/deny. Read that module's API when starting B; it must resolve through
    the same umwelt PolicyEngine (no reimplemented evaluator — that's the drift hazard).
    """
    raise NotImplementedError("lackpy umwelt-source verdict — wire in workstream B")


# ── the test (skips until B compiles a policy.db) ────────────────────────────
def test_policy_agreement():
    import pytest

    if not POLICY_DB.exists():
        pytest.skip(f"PENDING workstream B: no compiled policy at {POLICY_DB}")

    # B derives these from the .umw via umwelt; the skeleton hardcodes the sample policy.
    cases = gen_cases(writable_prefixes=["src/", "tests/"], tools=["Edit", "Bash", "Read"])
    mode = "implement"
    divergences = []
    for tool, path in cases:
        verdicts = {
            "truth": verdict_truth(tool, path, mode),
            "kibitzer": verdict_kibitzer(tool, path, mode),
            "lackpy": verdict_lackpy(tool, path, mode),
        }
        if len(set(verdicts.values())) != 1:
            divergences.append((tool, path, verdicts))
    assert not divergences, f"{len(divergences)} policy divergence(s) (gate=0): {divergences[:5]}"


if __name__ == "__main__":
    demo = gen_cases(["src/auth/"], ["Edit", "Bash"])
    print(f"gen_cases(['src/auth/'], ['Edit','Bash']) -> {len(demo)} cases; sample:")
    for c in demo[:8]:
        print("  ", c)
