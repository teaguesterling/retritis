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
