# 03 · Relations as content — DuckDB, dataframes, and Arrow as mimetypes

> Companion: [02-goo-the-verb-layer](./02-goo-the-verb-layer.md) defines `Accept:`
> negotiation; this doc says what is being negotiated when the answer is *tabular*.
> The whole retritis substrate is relational (DuckDB = facts), so "what is a result?"
> has a specific answer: **a relation, addressable and content-negotiable.**

## 1. References, not data — but the substrate is a relation

goo's addressing thesis is "**references, not data**: a subject is normally a *locator*;
inline content is the exception." retritis pushes on this from the data side: nearly
every fact a retritis tool produces is a **DuckDB relation** — AST nodes, error rows,
commits, search hits, session traces. So the natural goo question is: *what is a query
result, as content?*

The answer that keeps the system coherent: **a `goo://` reference can resolve to a
relation, not just a scalar or a blob.** `goo://build/run=42/errors` is a locator for a
*set of rows*. You don't inline the rows into the sentence; you pass the reference, and
the consumer fetches exactly the slice it needs. References-not-data, applied to tables.

## 2. One relation, four notations

A relation shows up in four guises across the suite, and they are the *same object*:

| guise | where it lives | example |
|---|---|---|
| **in-memory relation** | a DuckDB connection | `con.sql("SELECT … FROM errors")` |
| **lazy definition** | a SQL string / a view | `goo://data/?sql=SELECT…` (resolved on demand) |
| **reference** | a `goo://` URI | `goo://build/run=42/errors` |
| **materialized frame / wire** | Arrow IPC, a dataframe, Parquet, CSV | `Accept: application/vnd.apache.arrow` |

The design rule: keep it a **reference or a lazy definition** for as long as possible;
materialize to a frame only at the edge, and only in the format the consumer asked for.
This is the relational version of "references, not data" — and it's why the substrate
being DuckDB (lazy relations, pushdown-capable) rather than a pile of JSON matters.

## 3. The `data` taxon: a selector is a WHERE clause

From umwelt's linker note, the `data` taxon's matcher is DuckDB/blq, and the pivot
`table → row` hands off to the query engine. So a row selector, a goo address, and a
SQL predicate are three notations for one filter:

```
goo://data/build-log?severity=error&columns=file,line       # goo address
data|table#build-log row[severity="error"]                  # umwelt selector
SELECT file, line FROM build_log WHERE severity='error'     # SQL
```

`?refine` keys become `WHERE` predicates; the requested columns become the projection.
This is the cleanest instance of the [01](./01-the-shared-graph.md) claim that
*selectors are addresses*: here the selector compiles straight to SQL, and the matched
"entity set" is literally a result set.

## 4. Content negotiation: render for the audience, at the wire

Once a reference resolves to a relation, `Accept:` chooses the representation — and the
*same* relation serves the agent, the human, and the launcher:

```
GET goo://build/run=42/errors  Accept: application/vnd.apache.arrow   → Arrow IPC (zero-copy, agent/pipeline)
GET goo://build/run=42/errors  Accept: application/json               → records [{file,line,severity,…}]
GET goo://build/run=42/errors  Accept: text/csv                       → CSV (spreadsheet / shell)
GET goo://build/run=42/errors  Accept: text/plain                     → a rendered table (human)
GET goo://build/run=42/errors  Accept: application/vnd.apache.parquet → Parquet (durable handoff)
```

A suggested mimetype vocabulary (reuse standards first; only mint a vendor type for the
goo-specific framing):

| mimetype | meaning |
|---|---|
| `application/vnd.apache.arrow` | Arrow IPC stream — the zero-copy lingua franca |
| `application/vnd.apache.parquet` | columnar file, durable |
| `text/csv`, `application/json`, `text/plain` | the usual renderings |
| `application/vnd.cosmic-goo.relation+ref` | **the body is a `goo://` pointer to a relation, not the rows** |
| `application/vnd.cosmic-goo.relation+sql` | the body is a SQL string — a *lazy* relation definition |

The `+ref` type is the load-bearing one: instead of shipping 10MB of rows inline, a
handler returns `goo://data/run-42-errors` and lets the next hop `GET` it with the
columns and predicate *it* wants. Tabular references-not-data.

## 5. Pushdown: token-thrift becomes a transport property

Because it's HTTP over relations, predicate and projection **pushdown** come for free:

```
GET goo://data/build-log?severity=error&columns=file,line&limit=20
```

The resolver pushes `WHERE severity='error'`, the `file,line` projection, and the
`LIMIT` *into DuckDB*; only the 20×2 slice crosses the wire, as Arrow. retritis's
headline result — "73–99% fewer tokens than grep, ranked and compact" — stops being a
tool-by-tool property and becomes a property of the *transport*: the consumer asks for
exactly the slice it needs, the substrate computes it, the wire carries the minimum.
`HEAD` (from [02](./02-goo-the-verb-layer.md)) is the count-only extreme of the same
idea.

## 6. Dataframes as the interchange contract

Every fact-producing tool in the suite can emit a relation; **Arrow is how they hand
relations to each other without serializing through text.** This makes "dataframe" a
*contract*, not a library:

- **squackit / fledgling** — code search and macros return rows (file, span, kind, …).
- **blq** — build/test events are rows (file, line, severity, fingerprint, …).
- **jetsam / duck_tails** — commits, diffs, blame are rows.
- **lackpy** — a sandboxed program's *output* is a relation (or an Arrow batch); see
  [04](./04-the-suite-as-matchers.md). Its input context can be a relation too.
- **agent-riggs** — session traces are rows; the goo.sock access log parsed by
  duck_hunt is rows.

So a lackpy-generated program can consume a squackit relation, filter it, join it to a
blq relation, and return an Arrow frame — and every boundary is `Accept:
application/vnd.apache.arrow`, zero-copy, no JSON tax. The "two substrates" idea
(DuckDB = facts) is, at the wire, "everything speaks Arrow-shaped relations."

## 7. Laziness, streaming, and cursors

A relation reference need not be materialized to be passed around:

- `application/vnd.cosmic-goo.relation+sql` carries a *lazy* definition; the consumer
  decides when (and how filtered) to materialize.
- Large results stream as **chunked Arrow record batches** — the launcher renders the
  first screen while the tail is still computing; an agent can stop after the first
  batch (the `;pick=first` / `LIMIT` instinct).
- A reference can be a **cursor**: `goo://data/run-42-errors;cursor=…` for paginated
  fetch, mapping to DuckDB's streaming result. (Deferred; noted so the URI grammar
  leaves room.)

## 8. Why this is "generic," not goo-specific

Nothing here needs goo to be useful — it's the shape of *any* substrate-mediated
integration:

- An **MCP tool** can already return Arrow-backed content; the role map in
  [02](./02-goo-the-verb-layer.md) just declares its output mimetype.
- A **DuckDB query** is a portable lazy relation regardless of who calls it.
- A **dataframe** (pandas / polars / Arrow) is a materialized relation; the mimetype is
  the contract between producer and consumer.

goo is the addressing/verb layer that makes relations *passable as references with
content negotiation*; but the relation-as-content discipline pays off the moment two
tools exchange tabular data, with or without goo. Treat this doc as the data-plane
convention for the whole suite, of which goo is the most expressive consumer.

## Honest status

| Piece | State |
|---|---|
| DuckDB relations + Arrow as the substrate medium | built (fledgling/blq emit rows; DuckDB↔Arrow is native) |
| `data` taxon ≡ `goo://data/` ≡ SQL WHERE | design; the umwelt `data` matcher is sketched, goo `data` domain is design |
| `+ref` / `+sql` mimetypes + content negotiation + pushdown transport | speculative (this dir) |
| streaming cursors over `goo://data/` | deferred (URI room reserved) |

→ Next: [04-the-suite-as-matchers.md](./04-the-suite-as-matchers.md) — which tool
plays which role, and how the loop closes.
