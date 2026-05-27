# 4. pluckit — CSS-over-AST

If fledgling is SQL over the AST, **pluckit** is *CSS* over the AST: a selector language
for picking nodes out of parsed source the way a stylesheet picks elements out of a DOM.
It is the ergonomic middle layer — squackit's structural queries lean on it.

## The idea: selectors for code

You already know how to say "every `<a>` inside a `.nav`." pluckit lets you say the
analogous thing about code — "every function call inside a class method," "every import in
this module" — as a selector evaluated against the tree-sitter AST. The match set is then a
chain you can refine and extract from, rather than a regex you hope is precise.

```python
from pluckit import Plucker
plk = Plucker(root="/path/to/project")
plk.connection            # a fledgling.Connection when fledgling is installed; else raw duckdb
plk.pluckins              # the loaded pluckin instances (extensions)
```

## Pluckins and chains

- **pluckins** are pluckit's extension units — packaged selector/extraction capabilities
  (search, viewer, language adapters). `Plucker.pluckins` is the public list of loaded
  instances; a pluckin can publish tools that squackit surfaces.
- **chains** are the refine-and-extract pipeline over a match set. `Chain.MUTATION_OPS` is
  the public set of operations that *modify* (as opposed to read), which downstream code
  (squackit) consults to know whether an operation is read-only.

## The connection contract (a cautionary tale)

`Plucker.connection` is, *when fledgling is installed*, a `fledgling.Connection` — so it
carries `.con`/`.tools`/`.ensure_fts()`. **When fledgling is absent**, it is a bare DuckDB
connection with none of those. squackit once assumed the rich object unconditionally and
also reached into private internals; the fix (suite Phase 4, workstream "public contract")
was to document this proxy precisely, expose `pluckins` and `MUTATION_OPS` publicly, and
have squackit declare a real dependency on a compatible fledgling. The rule that fell out:

> **Why declare the dependency.** A proxy that is "rich when X is installed, thin
> otherwise" is a trap for consumers. pluckit documents the contract; squackit pins
> `ast-pluckit` and `fledgling-mcp` to compatible ranges so the rich object is guaranteed.
> Don't depend on the lucky case.

## When you touch pluckit directly

Mostly you won't — you'll call squackit, which uses pluckit under the hood. Reach for
pluckit directly when you are building a new structural query or a pluckin: it is the right
altitude for "select these nodes, refine, extract," below squackit's packaged tools but
above raw SQL.
