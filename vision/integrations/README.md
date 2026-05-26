# Integrations — the shared graph, the verb, and the body

> **Status: vision, ahead of build.** This directory documents a *convergence*,
> not a shipped integration. Several pieces are deliberately build-gated on both
> sides (goo's request layer → consumer/daemon #31/#38; umwelt's cross-taxon
> `register_relationship` → v1.1). The claim here is that the retritis suite and
> [cosmic-goo](https://github.com/teaguesterling/cosmic-goo) are the same typed
> entity graph seen from two ends, and that naming the seam now makes both cheaper
> to build later. Read it as a map, hold it to the honest-status tables in each doc.

## The one-sentence thesis

retritis turns **facts and policy** into queryable substrates so a *machine* composes
by **join**. goo turns **actions and entities** into an addressable protocol so a
*human* composes by **sentence**. They are the same graph. Concretely:

> **umwelt is the DOM of the system. goo is the verb you speak to it. A *pivot* is
> how you walk from one world into the next mid-sentence. A *relation* is what comes
> back. The retritis tools are the matchers that make any of it real.**

Two slogans carry the weight, each developed in its own doc:

- **An address is a policy rule with an empty declaration block.** umwelt selects a
  noun-phrase to attach *declarations* (policy); goo selects the same noun-phrase to
  attach a *verb* (action). Same selector, same graph — different thing hung off the
  match. → [01-the-shared-graph.md](./01-the-shared-graph.md)
- **A DuckDB macro signature, an MCP `inputSchema`, and a goo `OPTIONS` slot schema
  are the same object.** fledgling already publishes macros as MCP tools; the bridge
  to goo is therefore an adapter you write *once*, not glue per tool. →
  [02-goo-the-verb-layer.md](./02-goo-the-verb-layer.md)

## The layered picture

```
   the SENTENCE        VERB subject  Using: … To: … With: …          ← 02  goo (the verb)
   ───────────────────────────────────────────────────────────
   the NOUN-PHRASE     taxa = domains · pivots = hops · selectors    ← 01  umwelt (the engine)
   ───────────────────────────────────────────────────────────
   the MATCHERS        squackit · blq · jetsam · lackpy · pluckit …  ← 04  the suite (instantiation)
   ───────────────────────────────────────────────────────────
   the BODY            DuckDB relation / Arrow / dataframe / CSV     ← 03  relations as content
   ───────────────────────────────────────────────────────────
   the SUBSTRATES      DuckDB = facts        SQLite = policy
```

Bottom-up: two shared stores (facts in DuckDB, policy in SQLite); the suite tools are
matchers over them; umwelt is the common selector+cascade grammar that addresses
their entities and hops between them; goo is the verb+case sentence spoken against
that grammar; and what flows back over the wire is a **relation** — content-negotiated
into Arrow, a dataframe, CSV, or a rendered table depending on who's asking.

## Reading order

| # | doc | the question it answers |
|---|---|---|
| 01 | [the-shared-graph](./01-the-shared-graph.md) | What is a goo domain, really? (a umwelt taxon.) How do you hop between them? (a pivot.) |
| 02 | [goo-the-verb-layer](./02-goo-the-verb-layer.md) | How does a verb travel, and why is bridging goo↔MCP↔DuckDB mechanical? |
| 03 | [relations-as-content](./03-relations-as-content.md) | If the substrate is tabular, what is a result? (a relation as a mimetype.) |
| 04 | [the-suite-as-matchers](./04-the-suite-as-matchers.md) | Where does each tool plug in, and how does the loop finally close? |

## Honest status

| Piece | State | Where |
|---|---|---|
| DuckDB/SQLite substrates, suite matchers | **built** | the suite ships; fledgling `mcp_publish_tool` is live |
| umwelt selector + cascade + within-taxon descent (`file→node`) | **built (v1)** | umwelt entity-model |
| umwelt cross-taxon **pivots** (`register_relationship`, `DOMSchema(pivot_from=…)`) | **scoped, v1.1** | the keystone for domain-hopping |
| goo `goo://` URI addressing | **shipped** | goo addressing doc |
| goo request/wire layer (verbs, cases, status) | **design, build-gated** | goo-protocol.md (#31/#38) |
| goo↔MCP↔DuckDB bridge; relations-as-content negotiation | **speculative (this dir)** | here |

## The bet, and the cheapest way to disconfirm it

The load-bearing claim is that one **pivot primitive** — a typed edge between two
matchers' world models, traversed by the shared selector grammar — is simultaneously
umwelt's deferred `register_relationship` *and* goo's domain-hopping. Build it once,
both unlock. If that's true, this whole directory is an architecture. If wiring a
single cross-tool edge through the (static, decidable) selector engine fights goo's
(live, per-request) cadence, the seam is real and you've found it cheap. The smallest
experiment that tests it is spelled out at the end of
[01-the-shared-graph.md](./01-the-shared-graph.md#the-one-edge-experiment) — one edge,
`build-error → code`, between two matchers that already exist.
