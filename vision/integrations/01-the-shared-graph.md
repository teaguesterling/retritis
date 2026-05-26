# 01 · The shared graph — umwelt as the noun engine

> Companion: [02-goo-the-verb-layer](./02-goo-the-verb-layer.md) (the verb that acts on
> what this doc resolves). Sources: umwelt `docs/vision/entity-model.md` and
> `docs/vision/notes/world-as-root-and-linker-role.md`; goo
> `doc/design/addressing-and-protocol.md`.

## 1. umwelt is already a leaf-dependency entity engine

umwelt's core knows nothing about files, tools, or code. It knows **selectors, rule
blocks, declarations, cascade, and a matcher protocol**. Everything concrete is a
*consumer-registered taxon*: a collection of entity types with typed attributes,
declared structural relationships, and a matcher implementation. From its own
entity-model doc:

> "Core umwelt defines no entities. Consumers register taxa… The view's grammar is
> the same; the taxa are the vocabulary."

And from the linker note, the role is stated outright:

> "umwelt is not a sandbox tool. It's the **common selector + cascade surface**
> connecting every tool in the ecosystem… umwelt imports nothing from any of them.
> They all import umwelt's registry API. **Leaf dependency.**"

That is exactly what an addressing engine needs: a vocabulary-agnostic core, a
pluggable resolver per domain, and one grammar across all of them.

## 2. A goo domain *is* a umwelt taxon

goo's addressing doc defines a **domain** as "a named resolver = *name · type(s) it
yields · capabilities*," registered as `[[domains]]` with `emits` and an optional
`list_cmd`. umwelt defines a **taxon** as a registered collection of entity types
with a matcher. These are the same construct under two names — and umwelt's linker
table already assigns the matchers to retritis tools:

| umwelt taxon | matcher (world model) | goo domain | resolves |
|---|---|---|---|
| `world` | umwelt.sandbox (fs/mounts/env/net) | `goo://file/` | files, dirs, mounts |
| `source` | sitting_duck / pluckit / squackit | `goo://code/` | AST nodes, symbols |
| `data` | DuckDB / blq | `goo://data/`, `goo://build/` | tables, rows |
| `capability` | lackpy / fledgling / squackit | `goo://verb/`, `goo://app/` | tools, kits, effects |
| `git` | jetsam | `goo://repo/` | commits, branches, diffs |
| `state` | kibitzer / agent-riggs | `goo://job/` | hooks, jobs, budgets, traces |
| `actor` | the Ma layer | `goo://contact/`, `goo://agent/` | principals, delegates |

So: **write a matcher once and it serves both faces** — umwelt evaluates it to attach
policy; goo evaluates it to resolve a subject. The `register_matcher(taxon, …)` call
*is* the goo domain resolver registration.

## 3. A goo address is a umwelt selector

goo's URI is `goo://<domain>/<path>[;matrix][?refine]`. Each part has a umwelt
selector equivalent:

| goo URI part | umwelt selector | example |
|---|---|---|
| `<domain>` (authority) | taxon namespace (`ns\|type`) | `goo://code/` → `source\|…` |
| `<path>` exact id | `type#id` (id = `name` attr) | `goo://app/firefox` → `app#firefox` |
| `?refine` filters | attribute selectors `[attr=val]` | `?title=*Cosmic*` → `[title*="Cosmic"]` |
| `;matrix` (`;q=`, `;n=`, sort) | matcher query + ranking knobs | `;q=firefox` → fuzzy match + weight |
| value-first / search-fallback | `#id` exact vs `[attr]`/search | the addressing doc's resolution order |
| `infer` (default domain) | bare-type default-taxon resolution | `file { … }` resolves across taxa |

umwelt's CSS subset — `type`, `#id`, `[attr^= $= *=]`, descendant, `:not`, `:glob()`,
`:has()` — is the address grammar goo's `?refine` has been reaching toward. The two
designs converged on CSS-shaped addressing independently; this just notices it.

## 4. Three combinator meanings — and the one that is *domain hopping*

umwelt's descendant combinator means different things depending on the registry, and
the distinction is the whole story:

1. **Within-taxon descent** — `file[path^="src/"] node[kind="function"]` walks the
   declared `file → node` parent link. *Structural.* Built in v1.
2. **Context qualifier** — `tool[name="Bash"] file[path^="src/"]` reads "when Bash is
   acting, src files…". The left selector *gates* the rule; it doesn't contain the
   right. *Conditional.* Built in v1. (goo's analogue: the `Using:` case — the
   acting instrument conditions the verb.)
3. **Cross-taxon pivot** — descending from one world model into another, where the
   *entity type changes domains*. From the linker note:
   > "When a selector descends from one domain into another, that's a **pivot**. The
   > entity type changes from one tool's world model to another's… pivots are
   > structural (containment/descent within or between taxa); context qualifiers are
   > conditional (gating)."

   `file[path="login.py"] node.function#authenticate` pivots from the filesystem
   matcher to the AST matcher (sitting_duck). `table#results row[severity="error"]`
   pivots from blq's store into DuckDB's query engine.

**The pivot is goo's "domain hop."** Walking `file → node`, `event → node`,
`node → commit → contact` *is* the cross-domain traversal you want a launcher or an
agent to do mid-request.

## 5. The hop primitive (the keystone, currently deferred)

Within-taxon pivots (`file → node`) ship. **Cross-taxon** pivots between *peer* worlds
(`code → git`, `file → contact`, `window → workspace`) need two things umwelt has
scoped but not built (entity-model §13, v1.1+):

- **`register_relationship(from, to, name)`** + per-matcher navigation — declares a
  typed edge and how to walk it (e.g. `source/node —last-changed-by→ git/commit` is a
  blame query; `git/commit —authored-by→ actor/contact` is a log lookup).
- **`DOMSchema(pivot_from=("world","file"))`** — a plugin declares where its DOM
  *snaps onto* the global hierarchy. "Shadow DOM for policy surfaces." This makes the
  pivot graph explicit and discoverable — which is exactly the goo domain-hop graph.

Surfaced in the selector grammar as structural pseudo-classes:
`node:last-changed-by(commit)`, `commit:authored-by(contact)`,
`workspace:contains(window)`. umwelt files these under v1.1 as
"`hook:triggered-by(...)`, `job:owned-by(...)`, `file:produced-by(...)`."

**goo already has the syntactic room.** Its addressing doc says matrix params "bind to
a path *segment*, which gives each segment of a future hierarchy its own params." So a
multi-segment goo path *is* a pivot chain:

```
goo://world/file=report.md / changed-by / commit / authored-by / contact
   ≈  world|file#report.md :changed-by commit :authored-by contact
```

One declared-edge API on umwelt's side; one path-as-chain reading on goo's side; the
same traversal. Build the API once, both light up.

## 6. The seam: shared matcher, different collapse

umwelt and goo share the bottom of the stack and diverge at the top. Getting this
boundary right is the design:

```
            ┌──────────── shared ────────────┐
            │   matcher + pivot engine        │   selector → entity SET; hop across edges
            └───────────────┬─────────────────┘
              umwelt ◀───────┤───────▶ goo
       CASCADE                         RANK
   collapse to ONE winner          keep a ranked SET ({id,label,weight}),
   (CSS specificity + order)        disambiguate ambiguity as `300 Multiple Choices`
   → attach DECLARATIONS (policy)   → apply a VERB to the chosen member(s)
```

Both evaluate a selector to a matched set over the typed graph. Then:

- **umwelt cascades** — picks the single governing rule by specificity, because policy
  needs *one* answer ("is this file editable: yes/no").
- **goo ranks** — keeps the set with Kupfer-style weights, because a launcher/agent
  needs *choices* (the resolved firefox windows, ranked).

Do **not** try to make umwelt's cascade do goo's ranking. They are two collapse
strategies on the same matched set. The shared layer is the matcher + the pivots; the
divergence is "collapse to a policy verdict" vs "rank and act."

This is the precise content of the slogan: **an address is a policy rule with an empty
declaration block.** `file[path^="src/auth/"] { editable: false }` and
`EDIT goo://code/file=src/auth/login.py` evaluate the *same* selector; one hangs a
constraint on the match, the other hangs a verb.

## 7. The real tension: static vs live

umwelt is deliberately **static, decidable, snapshot-time**. Its entity-model is
emphatic: "runtime state never enters the selector layer"; runtime matching lives in
*declaration-level patterns* (`allow-pattern: "git *"`), not selectors; `dry-run`
evaluates against a supplied *world snapshot*. This keeps selectors portable across
compilers (nsjail, bwrap, kibitzer-hooks) and analysis decidable.

goo is the opposite temperament: **live, per-request**. "Which firefox window *right
now*," pid-qualified ids, weights that reflect current usage. Resolution happens at
keystroke time against a freshly-sampled world.

The matcher *protocol* is shared; the *cadence* is not. Using umwelt as goo's engine
means: feed the matcher a live world snapshot per request, accept that goo resolution
is "umwelt selector eval against a just-sampled world," and keep umwelt's
runtime-out-of-selectors discipline (so the same selector still compiles to a static
policy when umwelt wants it to). The grammar is shared; whether you evaluate it once
(policy) or every keystroke (addressing) is the consumer's choice.

## 8. Why the grammar is free but the edges are work

The selector syntax costs nothing — every code-trained reader already knows CSS. What
costs is each **pivot edge's navigation**:

- `node :last-changed-by commit` — a git-blame query (jetsam/duck_tails).
- `commit :authored-by contact` — a git-log lookup.
- `window :on workspace` — a wlroots/COSMIC query.
- `event :at node` — a join from a blq error row to a squackit symbol.

`register_relationship` gives you the *grammar* for free; you still implement the
walk per edge in the owning matcher. That's the honest scope: the syntax generalizes
instantly, the edges accrue one at a time.

## The one-edge experiment

Don't build the linker. Build **one pivot edge end-to-end** between two matchers that
already exist in retritis:

> `register_relationship(from="data/event", to="source/node", name="at")`, implement
> its navigation (a blq error row → file+line → squackit `node`), and resolve a single
> `GET goo://code/?at=goo://build/error:3` through the matcher layer to a ranked
> `{id,label,weight}` set.

If that one hop reads naturally as a selector and round-trips with weights, the
pivot-graph is real — build `register_relationship` for keeps. If wiring a single
edge through the static engine fights the live cadence (§7), you've found the seam for
the price of an afternoon, before either build gate.

→ Next: [02-goo-the-verb-layer.md](./02-goo-the-verb-layer.md) — what acts on the
entities this doc resolves.
