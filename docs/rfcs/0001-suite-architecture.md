# RFC 0001 — Suite architecture: composite identity, generators, and runtimes

**Status:** Draft. The *composition* and *addressing* sections are deliberately deferred
pending a review of `cosmic-goo/doc/design` (protocol/addressing/composition) and a
re-read of umwelt's language semantics. Everything else reflects decisions aligned in
discussion (2026-05-27).

## Motivation

The suite's tools are powerful but *abstract* — fledgling, squackit, kibitzer, lackpy,
umwelt, agent-riggs all operate on "the agent's work" in some way, and several have grown
to do more than one thing. Abstract tools with fuzzy boundaries are hard to reason about,
hard to compose, and (as this session proved with the public-contract and CI-rot work)
hard to keep from drifting. This RFC sharpens two of them — **lackpy** and **kibitzer** —
and corrects the runtime/generation roles of **umwelt** and **agent-riggs**.

## Principles

1. **Composite identity.** Every tool must have *one* clear identity *and* compose cleanly
   with the others. When a tool answers "what does it do?" with a list, split it — but only
   on a **load-bearing seam**. Each package boundary is a versioned contract to maintain;
   we hit that cost directly this session (the public-contract wave; lackpy/kibitzer CI rot
   that had stalled publishing for many versions). Split where the seam carries weight;
   resist splitting where it is merely tidy.

2. **Generators vs. runtimes.** A recurring pattern across the suite: a **generator**
   produces an artifact *offline* (often via an LLM or by learning), and a **runtime**
   consumes it *online*. They are different tools with different trust models and failure
   modes, and they should not be fused.
   - `lackpy-gen` (intent → program) **is a generator**; the lackpy runtime consumes the program.
   - `agent-riggs` (sessions → rules) **is a generator**; umwelt consumes the rules.
   A generator is never on the hot path; a runtime never learns. This symmetry is the
   organizing idea of the rest of the RFC.

## lackpy — a safe interpreter for subagents, with generation broken out

**Identity.** lackpy is, at its core, a **safe Python interpreter for subagents
("lackeys")** — Python with the dangerous pieces removed so a delegated worker can execute
generated code without risk. The *language + execution model* is the irreducible identity.
Generation (intent → program) was bolted on; it is valuable but it is a *frontend*, not the
core.

**Decisions.**
- **Break generation out** into a generator frontend (working name `lackpy-gen`:
  `infer/` + `prompts/`). Caveat acknowledged: generation **couples tightly to the
  execution model** (it must target the language, capabilities, and limits the runtime will
  enforce), so this is a *real-architectural-planning* seam, not a clean cut. The RFC
  commits to the *direction*; the precise boundary is an open design task (below).
- **Unify configuration.** Today `kit/` (capabilities), the `interpreters/` registry
  (which language), and `policy/` (what's allowed) are separate components. Generalize them
  into a **single runtime config** that configures the runtime *and the language it runs*:

  ```
  lackpy config = {
    interpreter,    # which language/interpreter (was: implicit registry choice)
    capabilities,   # which tools/callables  (was: "kit")
    policy,         # what's allowed         (resolved via umwelt — see below)
    sandbox,        # nsjail limits
  }
  ```

  A "kit" stops being a top-level noun — it is the `capabilities` field. This unification
  is conceptually straightforward and should land first; it makes the runtime parameterized
  (same program, different config) and clarifies the lang↔runtime↔frontend layering.
- **Split the interpreters.** `interpreters/{literate, ast_select, plucker, pss}` become
  pluggable interpreters behind the registry; **literate lackpy is useful on its own** (a
  literate-document → program compiler) and gets its own package. Note (to explore): these
  interpreters may align more naturally with **MCP prompt templates / fabric patterns** —
  *a pattern plus execution* — than with bespoke lackpy internals. `ast_select`/`plucker`
  are pluckit-flavored and may belong nearer pluckit.

**Proposed layering** (names provisional; see open questions):
```
  lang  (restricted language + validator + interpreter protocol + safe-Python interpreter)
    ▲
  runtime  (the config above; execute a program; sandbox)   ← this is lackpy's core identity
    ▲
  frontends:  lackpy-gen (intent→program) · literate (cells→program) · hand-authored .lackey
```

## kibitzer — one supervisor, two faculties, on named tie-in points

**Identity.** kibitzer is **the agent's supervisor at the tool-call boundary**.

**Decisions.**
- **One package, two faculties over an event substrate.** The substrate (`hooks/`,
  `interceptors/`, `controller/`, `session.py`, `state.py`, `store.py`) maintains state and
  dispatches **named tie-in events** — `session_start`, `pre_tool`, `post_tool`,
  `on_failure`, `on_mode_change` — *not* two monolithic hook functions. Faculties subscribe
  to the events they need.
  - **enforce** (`guards/`): **hard** authority — may block. Subscribes to `pre_tool`.
  - **coach** (`coach/`): **soft** authority — may only advise. Subscribes to `post_tool` /
    `on_failure`.
  Every kibitzer output is typed as enforce-or-coach, so the agent always knows whether it
  received a *constraint* or a *hint* — removing the ambiguity that made kibitzer's purpose
  feel scattered.
- **Fold the librarian into coach.** `context7.py` + `docs.py` (doc retrieval, incl. the
  live external fetch) become a *capability of the coach* (e.g., fired on `on_failure`), not
  a top-level subsystem.
- **Both faculties consume umwelt at runtime** (see next). kibitzer does **not** read
  agent-riggs at runtime.

**Mental-model one-liner.** *At named moments in the agent's loop, kibitzer either
**enforces** a constraint or **coaches** — both driven by umwelt.*

## umwelt — the single runtime rule system (event-in-context → rules)

**Reframe.** umwelt is **not** merely a static policy cascade. It is an **event-contextual
rule system**: given an event occurring in a context, it returns the applicable rules —
both **constraints** (for enforce) and **actions/suggestions** (for coach). It is the
*single runtime rule source* for the suite:
- kibitzer **enforce** asks umwelt for constraints at `pre_tool`.
- kibitzer **coach** asks umwelt for suggestions at `post_tool`/`on_failure`.
- lackpy's runtime resolves its `policy` (capability restriction) through umwelt.

> **Deferred — composition & addressing.** *How* events/contexts are addressed and how
> rules compose (specificity, scoping, layering) is exactly what the cosmic-goo
> protocol/addressing/composition review + the umwelt language re-read must inform. This
> section will be completed after that review. The open question: does umwelt's current
> `.umw` cascade already express "event in context → rules," or does it need a vocabulary
> extension for events/actions beyond tool/mode policy?

## agent-riggs — the umwelt rule *generator* (offline, not runtime)

**Reframe.** agent-riggs is **the generator of umwelt rules**, not a runtime consumer. It
observes sessions (turns, failures, trust/EWMA), learns recurring patterns, and **emits
umwelt rules** (promotion = a learned pattern graduating into umwelt). It is *never*
consulted on the hot path.

```
   agent-riggs  ──(learn: turns/failures/trust)──►  umwelt rules  ──►  umwelt (runtime)
   (generator, offline)                                                 │
                                                              kibitzer enforce / coach
                                                              lackpy policy
```

This is the generator/runtime symmetry from the Principles, applied: `riggs → umwelt`
mirrors `lackpy-gen → program`. It also resolves the earlier "RatchetConsumer in kibitzer"
design — kibitzer should read **umwelt** (which riggs has populated), not riggs directly.
(The RatchetConsumer built this session becomes an *implementation detail of riggs's
generation path*, or is superseded by emitting umwelt rules.)

## Open questions (need real design, not just naming)

1. **lackpy gen↔runtime boundary.** Generation couples to the execution model; where
   exactly does the package line go, and what shared contract (config + language profile)
   do both sides depend on? What is published as `lackpy` proper — the runtime, or the
   generator?
2. **Interpreters as MCP templates / fabric patterns.** Is "a pattern + execution" the
   right framing, and does it move literate/ast_select/plucker/pss toward template/fabric
   conventions (and pluckit) rather than lackpy internals?
3. **umwelt event/action vocabulary.** Does the cascade need first-class *events* and
   *actions* (coach suggestions, not just allow/deny), and how are they addressed/scoped?
   → cosmic-goo review.
4. **riggs → umwelt emission format.** What does a generated umwelt rule look like, and how
   is promotion expressed as a rule rather than a `ratchet_decisions` row?
5. **Contract maintenance.** Each new boundary (lackpy-lang, -literate, -gen; umwelt's
   rule schema) is a versioned contract. Budget for it; do not over-fragment.

## Next steps

1. Review `cosmic-goo/doc/design` — protocol, addressing, composition — for the
   composition/addressing model.
2. Re-read umwelt's language + resolve semantics against the "event-in-context → rules"
   framing.
3. Complete the deferred umwelt composition/addressing section and revisit the lackpy
   boundary questions; only then touch code.

---

# Addendum A — Composition & addressing (informed by cosmic-goo + an umwelt re-read)

This completes the sections deferred above. Two reviews fed it: `cosmic-goo/doc/design`
(protocol/addressing/composition) and a re-read of umwelt's AST + resolve engine.

## Finding 1 — umwelt is *already* the event-in-context → rules engine

The re-read settled the biggest open question. umwelt is **not** a tool/mode policy gadget;
it is a **generalized cross-taxon contextual cascade**:

- **Taxa** (`ast.py`): every selector is typed to a *taxon* resolved from a plugin registry.
  Entity types (tool, mode, capability, state, **event**, path, …) are just registered
  taxa — open-ended.
- **The `context` combinator**: `mode#review tool { … }` is a *cross-taxon* scope (the
  `CombinatorMode = structural | context | root` distinction). Cross-taxon scoping is the
  native mechanism, not a mode special-case.
- **Arbitrary active context** (`policy/queries.py`): resolve takes a
  `ContextQualifier = (taxon, type_name, entity_id)` **list** — `_setup_active_context`
  iterates *any* taxa. `mode=` is sugar for a single qualifier. So
  `resolve(type="tool", id="Bash", context=[("event","event","on_failure"),
  ("mode","mode","review")])` already works.
- **Predicate layer**: pseudo-classes (`:has`, `:glob`, `:not`) + attribute ops
  (`[path*="src/"]`, `^=`, `$=`) are exactly Plan-9-plumber's `data matches` and goo's
  `valid_when` jq-predicate — in CSS form. Specificity is the cascade's weighting.

**Consequence:** umwelt as the (opt-in) rule system needs **~zero engine change** —
only (a) *vocabulary*: register the `event`/`state`/etc. taxa and define **property
families** (enforce reads `allow`/`max-level`; coach reads `coach`/`suggest`/`doc`), and
(b) *plumbing*: kibitzer's tie-in points pass the **full active context** (event + mode +
tool + paths) into `resolve`, and each faculty reads its own property family off the same
resolved entity. An event becomes a taxon; an action becomes a property. That's it.

```
   event#on_failure tool.dangerous          { coach: "check the sandbox section"; }
   mode#review      tool                     { allow: false; }
   mode#implement   capability[path*="src/"] { allow: true; max-level: 8; }
        ▲ taxon        ▲ taxon + predicate        ▲ property family (enforce | coach)
```

## Finding 2 — the composition model to borrow from cosmic-goo

cosmic-goo independently converged on the patterns the suite needs; adopt the *concepts*
(not the `goo://` wire):

1. **Capabilities, not kinds.** A tool is a bundle of capabilities that compose, not a
   monolith. kibitzer's **enforce** and **coach** are two *capabilities* reading the same
   umwelt resolution (constraint properties vs action properties) — the goo `{read, write,
   process}` idea applied to rules. This is the precise form of "composite identity."
2. **"A verb is abstract; instruments implement it."** goo refuses `summarize-fabric` vs
   `summarize-duckdb`; one verb, the channel implements it via `Using:`. **lackpy's
   interpreters are exactly this** — *run* is the verb; the interpreter (literate, restricted-
   python, ast-select) is the **instrument**, selected by the runtime **config**. "Config
   configures the runtime *and its language*" = "the `Using:` slot picks the instrument."
3. **Channels ≈ fabric patterns ≈ MCP tool schemas.** goo's `OPTIONS` slot-schema *is* an
   MCP `inputSchema` (`accepts→emits` + params), and a goo channel is a fabric-style
   pattern+execution. This is the concrete backing for "interpreters align with MCP
   templates / fabric patterns": a lackpy interpreter is a typed `accepts → emits` channel
   whose schema is its MCP tool surface. literate = `accepts: literate-doc, emits: program`.
4. **Negotiate on capability, not identity.** goo's `From:`-is-`User-Agent` rule:
   never branch on *who* the caller is; negotiate on what it *accepts/provides*. For the
   suite: kibitzer should gate on the *capabilities/context* of a call (taxa + predicates),
   not on a tool's name; lackpy should select an interpreter by `accepts/emits`, not by a
   hardcoded switch.
5. **References, not data** (+ buffers materialize data→reference). The suite already passes
   references (paths, `policy.db`, symbols, ratchet keys); name it as a principle and keep
   data-producing stages (gen output, query results) addressable.

## Finding 3 — agent-riggs as a rule generator, concretely

With umwelt as a cascade, riggs's output is **`.umw` rules / `RuleBlock`s** (or rows the SQL
compiler turns into cascade candidates), *contributed like a plugin's rules* — plumber's
`[[dispatch]]` table, learned. **Promotion = a generated rule graduating into the active
cascade.** This replaces "kibitzer reads riggs' `ratchet_decisions` at runtime": kibitzer
reads **umwelt**; riggs *populates* umwelt offline. (The RatchetConsumer built this session
becomes part of riggs's generation/registration path, not a kibitzer runtime dependency.)

## Net architecture (revised)

```
  GENERATORS (offline)                 RUNTIME RULE SYSTEM            RUNTIMES (online)
  ───────────────────                  ──────────────────            ─────────────────
  agent-riggs  ── emits .umw rules ──►  umwelt  ──── resolve ───────► kibitzer: enforce (constraint props)
  (learns from sessions)               (cross-taxon contextual                 coach   (action props + docs)
                                        cascade; taxa+predicates)     lackpy:   policy on the run-config
  lackpy-gen   ── emits program ─────►  (program)  ── run ──────────► lackpy runtime (interpreter = instrument,
  (intent→program)                                                    config = capabilities+language+sandbox)
```

Two generator→runtime pairs (`riggs→umwelt`, `lackpy-gen→program`), one shared rule engine
(umwelt) that every runtime consults, and composition by **capability + instrument +
context**, not by enumerating combined tools. That is the suite's composite identity.

## Resolved / still open

- **Resolved:** umwelt is the runtime rule engine (no new engine); events=taxa,
  actions=properties; riggs emits rules; interpreters=instruments=channels≈MCP-schemas;
  enforce/coach=capabilities.
- **Still needs design:** the lackpy gen↔runtime package line (the coupling); the concrete
  taxa/property vocabulary (`event`, `state`, `coach`/`suggest` names) and whether to adopt a
  goo-style *address* for events/rules; the riggs→umwelt emission format + how promotion
  writes into a live cascade; contract/versioning for each new boundary.

---

# Addendum B — umwelt is opt-in; goo defines the world; shape vs context

Two corrections/clarifications from discussion (supersede any "single runtime rule system"
phrasing above).

## The distinction that organizes everything: shape-driven vs context-driven

> **goo is shape-driven — "can *this* fit into *that*?"**
> **umwelt is context-driven — "what constraints are on *that* when it's over *here*?"**

goo answers **applicability/fit**: does this entity's *shape* (its type/MIME, an
instrument's `accepts→emits`, a destination's `{write}`) match the slot it's going into? It
is structural and mostly static — type-match + `valid_when`, no notion of "where in the
session am I."

umwelt answers **contextual constraint**: given that a thing exists and fits, what rules
apply to it *in this context* (mode, event, session, location) — *with override semantics*
(cascade + specificity)? It is dynamic and layered — the part goo's flat predicates do
poorly.

Applicability vs policy. Fit vs constraint. Keeping these on different tools keeps both
identities sharp — and is the rule that prevents the redundant-matching trap below.

## umwelt is 100 % opt-in, via mutual plugins (it does not pre-enumerate)

umwelt is powerful but complicated, so **nothing depends on it by default.** A consumer
that wants it performs a **mutual registration**:

- the consumer supplies the **world** — `register_matcher` (per-taxon: what entities exist
  + how to resolve them; `MatcherProtocol`), `register_entity`, optional `register_sugar`
  (consumer-defined at-rules), and a pluggable compiler for its enforcement target;
- umwelt supplies **resolution** — `resolve(entity, property, active-context)` over the
  cascade.

umwelt **does not pre-enumerate the world** — it asks the registered matchers, and
**degrades gracefully** when none are registered (raw rule scan / synthetic entities, as in
offline/test use). Every consumer therefore keeps a **no-umwelt path** (kibitzer's
`PolicyConsumer.from_db → None → config fallback` is the reference). The complexity stays
behind the opt-in boundary; the "what's in the world" knowledge lives with the consumer
that actually has it.

Restate the earlier claim accordingly: umwelt is **the rule system *when opted in*, and
zero footprint when absent** — not a mandatory single dependency.

## goo and umwelt: cousins; goo defines the world more than it consumes

goo and umwelt are architectural **cousins** — both plugin-fed resolvers over a typed
entity space (goo: domains/MIME/`valid_when`; umwelt: taxa/predicates/cascade). That
overlap is a **trap**: goo already does applicability matching, so leaning on umwelt for it
would mean *two* matching engines and muddied identities. The shape-vs-context split is the
discipline that avoids it.

**Division of labor.**
- **goo owns** addressing, **applicability** (shape/fit), dispatch, composition. No umwelt
  needed for the common case.
- **umwelt owns** **contextual policy with override semantics** (cascade/specificity,
  mode/event-scoped). The cases goo's flat `valid_when` handles poorly.

**The relationship (weighted toward "defines").**
1. **goo *defines* the umwelt world — the primary, natural tie.** goo's domains/entities/
   MIME-types are exactly the rich, live, addressable entity space umwelt wants but won't
   pre-enumerate. goo registering a matcher that resolves its addresses into umwelt entities
   (and its types as taxa/classes) *is* the `register_matcher`/`register_entity` seam. goo is
   plausibly the best world-provider umwelt could have.
2. **goo *uses* umwelt — real but minority.** Only when goo needs **cascading contextual
   policy** ("deny `REBOOT` in a locked-down session"; "destructive *in review mode*") does
   it consult umwelt. For flat needs ("this verb is destructive → confirm"), goo's own verb
   metadata suffices; umwelt would be overkill.

These are **two halves of one opt-in act**: goo opting into umwelt *means* it registers its
world (half 1) and can then query rules over it (half 2).

**Dependency direction (clean):** **goo → umwelt** (goo registers/queries); **umwelt never
reaches into goo.** umwelt stays standalone and goo-agnostic; if goo never opts in, umwelt
never hears of it. Same shape as kibitzer→umwelt and lackpy→umwelt — they are all mutual-
plugin consumers, differing only in how much world they contribute vs how much policy they
query.

**Recommendation:** treat goo as a **world-definer first** (its entity/type registry is
premium umwelt material) and an umwelt *consumer* only where it needs context-scoped,
overriding policy. goo = shape/fit/dispatch; umwelt = contextual constraint. Don't duplicate
matching across them.

---

# Addendum C — Aspiration: a flat verb vocabulary (unqualified tool names)

**Wish:** call `find_definitions …`, not `squackit.find_definitions` (let alone
`mcp__plugin_squackit_squackit__find_definitions`). The verb should be flat; *which tool
implements it* should be resolution, not qualification.

This is goo's principle applied to the suite's surface: **"a verb is an abstract operation;
instruments implement it"** and **addresses group by kind, not provider** — the provider is
*resolved*, never named. `find_definitions` is one verb; fledgling and squackit are
instruments that provide it, selected the way goo selects a `Using:` channel.

- **Obstacle.** MCP namespaces tools *by server*, and the suite has genuine collisions (the
  same verb in fledgling *and* squackit). A flat vocabulary therefore needs a thin
  **dispatch facade** that owns one verb namespace and resolves the implementing tool by
  **applicability** — collisions broken by capability/specificity (umwelt's and goo's
  existing resolution), not by a server prefix.
- **Mechanism (free, from cosmic-goo).** goo's `OPTIONS` slot-schema *is* an MCP
  `inputSchema` — so a flat-verb ↔ MCP proxy is mechanical: the facade publishes unqualified
  verbs, each backed by a resolved instrument's schema, and routes the call.
- **Shape vs context applies.** Resolving *which instrument* answers a verb is **shape-driven**
  (does this tool's `accepts` fit the subject?); gating *whether it's allowed here* is
  **context-driven** (umwelt). The facade does the former; umwelt the latter.

Open: where the facade lives (a suite-level MCP gateway? squackit-as-front-door?), and the
collision-resolution policy (prefer the higher-level tool — squackit over fledgling — by
default, overridable).
