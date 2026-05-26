# S16 — code-nav under live hooks (C · affordable coaching)

**Archetype:** navigating code while kibitzer's PreToolUse hook fires. The point is whether
doc-context coaching (which needs an FTS lookup per hook) is affordable within the hook time
budget — only true once the persistent substrate (C) makes FTS a cache hit.

**Status:** PENDING — blocked on workstream **C** (per-hook doc-context coaching needs the
persistent index; with in-memory rebuild it's too slow to fire inside the hook budget).
**Feeds:** C (doc_context_coaching_fired rate; per-hook latency budget adherence).
