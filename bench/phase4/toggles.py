"""How each integration is realized OFF (baseline) vs ON.

The A/B is only meaningful if these toggles are clean — see the table in
vision/phase-4-calibration.md section B. Most ON paths reference integrations
that don't exist yet (Phase 4 builds them); those are TODO and currently raise
NotImplementedError so a misconfigured ON run fails loudly instead of silently
measuring the OFF behavior.
"""
from __future__ import annotations

from pathlib import Path


def env_for(integrations: dict[str, bool], fixture: Path) -> dict[str, str]:
    """Return the environment overlay that realizes the requested toggle set.

    OFF is always the current shipped behavior (in-memory fledgling, config-only
    kibitzer policy, no ratchet consumer). ON wires the Phase 4 deliverable.
    """
    env: dict[str, str] = {}

    # C - persistent fact substrate
    if integrations.get("C"):
        # ON: file-backed fledgling cache (workstream C). The cache must outlive the
        # per-run throwaway worktree, so it lives under results/_ccache keyed by a
        # run-index-stripped stem (every run of a scenario shares one cache; content
        # is identical across runs at the same git ref, so the staleness key matches).
        cache_dir = fixture.parent.parent / "_ccache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        stem = fixture.name.rsplit(".", 1)[0]  # "S06....proxy.C.3" -> "S06....proxy.C"
        env["FLEDGLING_PERSIST"] = str(cache_dir / f"{stem}.duckdb")
        # The persist feature lives in *current* fledgling (the tool), while the fixture
        # is an older fledgling checkout (the corpus to index). _isolated_env prepends the
        # fixture to PYTHONPATH, which would shadow the tool with the corpus's pre-persist
        # code. Clear it so `import fledgling` resolves to the installed/current version;
        # the corpus is still indexed via cwd=fixture (root=".").
        env["PYTHONPATH"] = ""
    # OFF: nothing -> fledgling.connect(persist=None), in-memory rebuild.

    # B - one policy, two enforcers
    if integrations.get("B"):
        # ON: compiled umwelt policy present -> kibitzer PolicyConsumer.from_db + lackpy source.
        # env["KIBITZER_POLICY_DB"] = str(fixture / ".umwelt/policy.db")
        raise NotImplementedError("toggle B ON: compiled policy.db wiring not built yet (workstream B)")
    # OFF: kibitzer config.toml only (PolicyConsumer.from_db -> None).

    # A - learn loop
    if integrations.get("A"):
        # ON: kibitzer reads agent-riggs' PROMOTED ratchets from a frozen store and surfaces
        # the recorded pattern as coaching. The consumer + its producer-key contract are BUILT
        # and tested in kibitzer (src/kibitzer/ratchet/consumer.py; tests/test_ratchet_consumer.py
        # — RatchetConsumer.from_db/from_env, coaching_for_failure, and a producer-driven
        # candidate_key conformance). What remains for the *measurable* repeat-failure A/B
        # (S12-S15) is the full-agent runner (run_agent="full", still stubbed) to drive a real
        # observe->surface->resolve cycle + a seeded-then-frozen store. Until then a meaningful
        # A-ON measurement can't be produced, so fail loudly rather than measure OFF behavior.
        #   env-to-set once the runner lands: RIGGS_RATCHET_DB=<frozen store>, RIGGS_FROZEN=1,
        #   PYTHONPATH=~/Projects/kibitzer/src (dev kibitzer with RatchetConsumer).
        raise NotImplementedError(
            "toggle A ON: consumer+contract built & tested in kibitzer; the repeat-failure A/B "
            "is deferred to the full-agent runner (run_agent='full')"
        )
    # OFF: empty/absent ratchet store.

    return env
