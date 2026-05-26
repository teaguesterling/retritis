# 04 · The suite as matchers — who plays which role

> Where each retritis tool plugs into the shared graph
> ([01](./01-the-shared-graph.md)), the verb layer ([02](./02-goo-the-verb-layer.md)),
> and the relational data plane ([03](./03-relations-as-content.md)). Then: how the
> observe→understand→act→learn loop finally closes when all three are present.

The shape repeats for every tool: **it owns a world model, registers it as a umwelt
taxon (= a goo domain) with a matcher, optionally declares pivot edges into other
worlds, and exposes verbs.** A tool is some combination of four roles:

- **Matcher / resolver** — turns a selector into a ranked entity set (`goo://…` GET).
- **Verb source** — declares extension methods (`MOVE`, `SHIP`, `SOLVE`).
- **Channel** (`Using:`) — performs work on behalf of a verb.
- **Substrate** — emits/holds the relations everyone else joins against.

---

## umwelt — the grammar itself (not a matcher)

umwelt is the **linker**: the common selector + cascade surface, a leaf dependency that
imports nothing and that everyone registers into. It is not a domain; it is the engine
that makes domains addressable and hoppable. Its `register_taxon / register_entity /
register_property / register_matcher` API is *also* the goo domain-registration API
(§2 of [01](./01-the-shared-graph.md)), and its deferred `register_relationship` is the
domain-hop primitive ([01](./01-the-shared-graph.md#5-the-hop-primitive-the-keystone-currently-deferred)).
Its `capability` taxon is where goo's verb-safety lives as policy
([02 §6](./02-goo-the-verb-layer.md#6-safety-one-policy-two-enforcement-points)).

## squackit / pluckit / sitting_duck — the `source` taxon, `goo://code/`

- **Matcher:** CSS-over-AST. `GET goo://code/;q=validate_token` → ranked code entities
  `{id: goo://code/file=src/auth/token.py#validate_token, label:"def validate_token",
  weight:0.91}`. The Kupfer-style weighting goo wants is squackit's BM25+AST ranking.
- **Pivots:** `file → node` (within `world→source`, built); `node → commit`
  (`source→git`, via the relationship keystone).
- **Verbs:** `GOO` (default) opens at the line; `VIEW`, `CALLERS` (→ call_graph),
  `INVESTIGATE`, `REVIEW`; mutation verbs via **pluckit** — `MOVE goo://code/…#old To:
  new` is a rename, `EDIT … With: selector=…` is a chain.
- **Content:** results are relations ([03](./03-relations-as-content.md)); `Accept:`
  picks structured nodes vs grep-style text vs an HTML preview.

## fledgling — substrate macros + the schema-identity proof

fledgling's `PRAGMA mcp_publish_tool(name, desc, sql, inputSchema, required, format)`
is the existing demonstration that **a DuckDB macro signature is an MCP `inputSchema`
is a goo OPTIONS slot schema** ([02 §2](./02-goo-the-verb-layer.md#2-the-three-way-schema-identity)).
Every macro it publishes is a candidate goo verb/resolver via one adapter + a role map.
It is the substrate layer: unified SQL views over code/git/docs/conversations that the
other matchers and lackpy programs join against.

## blq — the `data` taxon, `goo://build/` and `goo://activity/`

- **Observe:** runs builds/tests and captures failures as fingerprinted rows. `GET
  goo://build/run=42/errors` is a relation ([03](./03-relations-as-content.md)); the
  `data` matcher is DuckDB, so the address compiles to SQL.
- **`goo://activity/` — the sneaky-important one.** goo requests are *literally HTTP*
  over `/run/user/$UID/goo.sock`, so there is an access log. duck_hunt/blq ingest it
  into DuckDB and your own system activity becomes a fact substrate: `GET
  goo://activity/;q="files I emailed last week"` is a SQL query. This is what gives the
  learn loop a uniform action stream (see below).
- **Pivot:** `event → node` (`data→source`) is the **one-edge experiment** in
  [01](./01-the-shared-graph.md#the-one-edge-experiment).

## jetsam — the `git` taxon, `goo://repo/`

- **Matcher:** commits, branches, diffs as entities/rows.
- **Verbs:** `SHIP goo://repo/. To: goo://branch/main`, `SAVE`, `SYNC` — the `To:` case
  carries the destination ref naturally.
- **Pivots:** `node → commit → contact` (changed-by / authored-by) — the edges that let
  "who last touched the function behind this failing test" be a single
  [01](./01-the-shared-graph.md) pivot chain.

## lackpy — a `Using:` channel, and goo becomes its output language

This is the most generative role. lackpy turns NL intent into a sandboxed program.
Give it **goo as its action vocabulary** and it emits a *goo-request-program* — a
sequence of strict, individually policy-checkable verbs — for the whole system, not
just code:

```
SOLVE goo://text/"rebase onto main, run the auth tests, ping me if they pass"
  Using: goo://channel/lackpy
  → emits:  SHIP goo://repo/. To: goo://branch/main
            TEST goo://code/dir=tests/auth/
            NOTIFY goo://contact/me  With: when=pass
```

- lackpy **`OPTIONS`-discovers** the available verbs to compose against — inference at
  the LLM tier, using the same OPTIONS oracle that drives tab-completion.
- Each emitted step is **policy-checked by umwelt** and **sandboxed by nsjail**.
- Its program's *output* is a relation ([03](./03-relations-as-content.md)); its input
  context can be a relation (a squackit set joined to a blq set).
- It runs locally on longbottom's GPU (qwen3:14b-iq4xs) — inference stays on-prem,
  which is the whole reason longbottom is a full host.

goo is to lackpy what bash is to a shell agent: the substrate it composes in — except
addressable, typed, and policy-gated per step.

## kibitzer — the `state` taxon, in-agent policy enforcement

kibitzer is the *in-agent* twin of the goo dispatch middleware: it intercepts tool
calls (PreToolUse) and enforces umwelt policy without an LLM in the loop (rules, not a
model). Same `.umw` policy, enforced at the semantic altitude inside the agent;
goo-middleware enforces the same policy at the system altitude. (The drift hazard in
[02 §6](./02-goo-the-verb-layer.md#6-safety-one-policy-two-enforcement-points) is why
they must share umwelt's evaluator, not reimplement it.)

## agent-riggs — the `state` taxon, and the close of the loop

agent-riggs is cross-session memory, trust scoring, and pattern promotion. Its open
problem (per the suite's own status: the "learn" loop is unwired) gets a substrate for
free from goo: **a uniform, addressable, timestamped action stream** — the goo.sock log
(`goo://activity/`), parsed into DuckDB. It scores traces, and promotes a recurring fix
into a kibitzer suggestion or a lackpy template. The loop's weakest link gets the exact
medium it needs.

## nsjail-python — the sandbox backend

Not a domain; the OS-altitude enforcement layer that *realizes* umwelt `world`-taxon
constraints (mounts, resources, network) for lackpy-generated programs. The compiler
target umwelt emits to; the bound on reality beneath the policy.

---

## The loop, closed — in goo + umwelt + relations terms

```
OBSERVE     blq runs the build → goo://build/run=N/errors  (a relation)
UNDERSTAND  pivot event → node → commit:                 squackit + jetsam, ranked sets
DECIDE      kibitzer / goo-middleware check the same .umw policy (umwelt)
ACT         pluckit MOVE / jetsam SHIP — or lackpy SOLVE emits a policy-checked goo-program
LEARN       every step is an HTTP request on goo.sock → goo://activity/ → agent-riggs
            scores the trace, promotes the pattern back into kibitzer/lackpy
```

Each station is a matcher or a verb over the shared graph; each handoff is a relation;
each action is one addressable, logged, policy-gated sentence. The thing retritis marks
"open" (a *closed* observe→learn loop) is exactly the thing goo's uniform action stream
supplies — which is why this integration is a completion, not a bolt-on.

## Honest status (suite-wide)

| Role | Built today | Needs |
|---|---|---|
| matchers emit ranked relations | yes (squackit/blq/jetsam/fledgling) | a `{id,label,weight}` envelope convention |
| umwelt taxa register the matchers | partial (taxa specced; matchers exist) | wire the registrations |
| cross-tool pivots (`event→node`, `node→commit→contact`) | no | `register_relationship` (umwelt v1.1) |
| lackpy → goo-program output | no | goo request layer (#31) + a verb vocabulary |
| `goo://activity/` learn loop | no | goo.sock daemon (#31) + duck_hunt ingest |
| one policy, two enforcers | partial (kibitzer in-agent) | goo-middleware sharing umwelt's PolicyEngine |

The build gates are real and deliberate. The point of this directory is that the
*architecture* is one architecture — so each gated piece, when built, lands in a slot
that's already shaped for it.
