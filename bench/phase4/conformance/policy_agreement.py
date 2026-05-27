"""B-workstream conformance: one policy, two enforcers.

A single umwelt policy (`world.yml` + `policy.umw`) compiles to one `policy.db`.
Three independent readers consume it:

  * **truth**    — umwelt's own `PolicyEngine.resolve` (the source of meaning).
  * **kibitzer** — `PolicyConsumer.from_db`, exactly as the kibitzer hook enforces
                   at tool-call time.
  * **lackpy**   — `policy.sources.umwelt.UmweltPolicySource`, as lackpy restricts
                   the tool set of a generated program.

Zero divergence is the safety gate (phase-4.md §3): if two enforcers read the same
compiled policy differently, the agent is sandboxed differently than it believes.

ARCHITECTURE NOTE (discovered building B): the three readers do **not** all operate
at the same granularity.
  * kibitzer enforces per (tool, path, active_mode): it threads `active_mode` through
    `context=` and gates paths via the mode's `writable`.
  * lackpy's `UmweltPolicySource` is **mode- and path-unaware** — `PolicyContext` has
    no mode field and the source takes no path; it computes an allowed/denied tool SET
    plus per-tool `ToolConstraints` from `resolve_all(type="tool")` with no mode.
So the common ground where all THREE must agree is the **unscoped tool verdict**
(allow/deny) and the **per-tool constraints** (max-level, allow/deny patterns). The
mode-scoped tool verdicts and the mode policy (writable/strategy/coaching) are a
**kibitzer↔truth** pair; lackpy structurally can't participate there yet — that gap is
recorded by `test_lackpy_is_mode_unaware` (a finding, not a silent pass).
"""
from __future__ import annotations

import itertools
import os
from pathlib import Path

_HERE = Path(__file__).parent
WORLD = _HERE / "world.yml"
STYLESHEET = _HERE / "policy.umw"
# Honor an externally-compiled db if given; otherwise tests build one from WORLD+STYLESHEET.
POLICY_DB_ENV = os.environ.get("PHASE4_POLICY_DB")

TOOLS = ["Read", "Grep", "Edit", "Write", "Bash"]
MODES = ["implement", "review", "explore"]


# ── policy.db production (the single source all three readers share) ─────────
def build_policy_db(dest) -> str:
    """Compile WORLD + STYLESHEET -> a saved policy.db. Returns the path."""
    from umwelt.policy import PolicyEngine

    eng = PolicyEngine.from_files(world=str(WORLD), stylesheet=str(STYLESHEET))
    eng.save(str(dest))
    return str(dest)


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


# ── normalization (so the three shapes compare apples-to-apples) ─────────────
def _allow_verdict(value) -> str:
    """allow/deny from a resolved `allow` property. Only an explicit 'false' denies
    (missing/true => allow) — matching lackpy's source semantics."""
    return "deny" if str(value).strip().lower() == "false" else "allow"


def _split(value) -> tuple[str, ...]:
    """umwelt stores list-valued props as comma-separated strings; normalize to a
    sorted tuple. Accepts already-split lists/tuples too."""
    if value is None or value == "":
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(sorted(str(x).strip() for x in value if str(x).strip()))
    return tuple(sorted(s.strip() for s in str(value).split(",") if s.strip()))


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _norm_constraints(max_level, allow_patterns, deny_patterns):
    return (_int_or_none(max_level), _split(allow_patterns), _split(deny_patterns))


# ── verdict getters: TRUTH (umwelt PolicyEngine) ─────────────────────────────
def _engine(db):
    from umwelt.policy import PolicyEngine

    return PolicyEngine.from_db(str(db))


def truth_tool_allow(db, tool, mode=None) -> str:
    ctx = {"mode": mode} if mode else {}
    return _allow_verdict(_engine(db).resolve(type="tool", id=tool, property="allow", context=ctx))


def truth_constraints(db, tool):
    props = _engine(db).resolve(type="tool", id=tool) or {}
    return _norm_constraints(props.get("max-level"), props.get("allow-patterns"), props.get("deny-patterns"))


def truth_mode_policy(db, mode):
    props = _engine(db).resolve(type="mode", id=mode) or {}
    return (_split(props.get("writable")), props.get("strategy", ""), _int_or_none(props.get("coaching-frequency")))


# ── verdict getters: KIBITZER (PolicyConsumer, as the hook enforces) ─────────
def _kib(db):
    from kibitzer.umwelt.consumer import PolicyConsumer

    return PolicyConsumer.from_db(str(db))


def kibitzer_tool_allow(db, tool, mode=None) -> str:
    return _allow_verdict(_kib(db).get_tool_policy(tool, active_mode=mode).get("allow"))


def kibitzer_constraints(db, tool):
    tp = _kib(db).get_tool_policy(tool)
    return _norm_constraints(tp.get("max-level"), tp.get("allow-patterns"), tp.get("deny-patterns"))


def kibitzer_mode_policy(db, mode):
    mp = _kib(db).get_mode_policy(mode)
    if mp is None:
        return (None, None, None)
    return (_split(mp.writable), mp.strategy, mp.coaching_frequency)


# ── verdict getters: LACKPY (UmweltPolicySource, as it restricts a kit) ──────
def _lackpy_source(db):
    from lackpy.policy.sources.umwelt import UmweltPolicySource

    return UmweltPolicySource(_engine(db))


def _lackpy_result(db):
    """Run lackpy's source over a kit that already contains every tool, so its
    intersection-with-kit step never masks a verdict. Returns the PolicyResult."""
    from lackpy.policy.types import PolicyResult

    src = _lackpy_source(db)
    current = PolicyResult(allowed_tools=frozenset(TOOLS))
    return src.resolve(current, {})


def lackpy_tool_allow(db, tool) -> str:
    res = _lackpy_result(db)
    return "deny" if tool in res.denied_tools or tool not in res.allowed_tools else "allow"


def lackpy_constraints(db, tool):
    res = _lackpy_result(db)
    tc = res.tool_constraints.get(tool)
    if tc is None:
        return (None, (), ())
    return (tc.max_level, _split(tc.allow_patterns), _split(tc.deny_patterns))


# ── tests ────────────────────────────────────────────────────────────────────
def _policy_db(tmp_path):
    """The compiled policy under test: env override if set, else build from sources."""
    if POLICY_DB_ENV and Path(POLICY_DB_ENV).exists():
        return POLICY_DB_ENV
    return build_policy_db(tmp_path / "policy.db")


def test_tool_allow_three_way(tmp_path):
    """THE gate: truth == kibitzer == lackpy on every unscoped tool allow verdict."""
    db = _policy_db(tmp_path)
    divergences = []
    for tool in TOOLS:
        verdicts = {
            "truth": truth_tool_allow(db, tool),
            "kibitzer": kibitzer_tool_allow(db, tool),
            "lackpy": lackpy_tool_allow(db, tool),
        }
        if len(set(verdicts.values())) != 1:
            divergences.append((tool, verdicts))
    assert not divergences, f"{len(divergences)} tool-allow divergence(s) (gate=0): {divergences}"


def test_constraints_three_way(tmp_path):
    """truth == kibitzer == lackpy on (max-level, allow-patterns, deny-patterns)."""
    db = _policy_db(tmp_path)
    divergences = []
    for tool in TOOLS:
        verdicts = {
            "truth": truth_constraints(db, tool),
            "kibitzer": kibitzer_constraints(db, tool),
            "lackpy": lackpy_constraints(db, tool),
        }
        if len(set(verdicts.values())) != 1:
            divergences.append((tool, verdicts))
    assert not divergences, f"{len(divergences)} constraint divergence(s) (gate=0): {divergences}"


def test_mode_scoped_tool_allow_kibitzer_vs_truth(tmp_path):
    """The two mode-aware readers agree on every (mode, tool) allow verdict."""
    db = _policy_db(tmp_path)
    divergences = []
    for mode, tool in itertools.product(MODES, TOOLS):
        t = truth_tool_allow(db, tool, mode=mode)
        k = kibitzer_tool_allow(db, tool, mode=mode)
        if t != k:
            divergences.append((mode, tool, {"truth": t, "kibitzer": k}))
    assert not divergences, f"{len(divergences)} mode-scoped divergence(s) (gate=0): {divergences}"


def test_mode_policy_kibitzer_vs_truth(tmp_path):
    """kibitzer's ModePolicy (writable/strategy/coaching) matches truth for each mode."""
    db = _policy_db(tmp_path)
    divergences = []
    for mode in MODES:
        t = truth_mode_policy(db, mode)
        k = kibitzer_mode_policy(db, mode)
        if t != k:
            divergences.append((mode, {"truth": t, "kibitzer": k}))
    assert not divergences, f"{len(divergences)} mode-policy divergence(s) (gate=0): {divergences}"


def test_lackpy_is_mode_unaware(tmp_path):
    """RECORDED FINDING (not a pass-by-accident): lackpy's UmweltPolicySource cannot
    take an active mode — PolicyContext has no `mode` field and the source calls
    resolve_all(type='tool') with no context. So mode-scoped policy (review/explore
    locking tools down) is invisible to lackpy. This test documents the gap so a future
    lackpy enhancement (thread mode through PolicyContext) has a target; until then the
    three-way gate is correctly scoped to the unscoped verdict + constraints."""
    from lackpy.policy.types import PolicyContext

    assert "mode" not in PolicyContext.__annotations__, (
        "lackpy PolicyContext now has a mode field — extend the three-way conformance to "
        "cover mode-scoped verdicts for lackpy too (this finding is resolved)."
    )


if __name__ == "__main__":
    demo = gen_cases(["src/auth/"], ["Edit", "Bash"])
    print(f"gen_cases(['src/auth/'], ['Edit','Bash']) -> {len(demo)} cases; sample:")
    for c in demo[:8]:
        print("  ", c)
