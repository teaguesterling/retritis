# 02 · goo as the verb layer

> Companion: [01-the-shared-graph](./01-the-shared-graph.md) resolves the *noun*; this
> doc is the *verb* that acts on it. Sources: goo `doc/design/goo-protocol.md` and
> `doc/design/addressing-and-protocol.md`.

## 1. The sentence

A goo invocation is one HTTP/1.1 request, with the slots as grammatical cases:

```
VERB    <subject>                 the Theme/Patient — what is acted on (a goo:// URI)
Using:  <agent / instrument>      the channel that performs it
To:     <recipient / goal>        where it lands (resolves, or falls through as a literal)
With:   key=value …               opaque manner/config
body                              inline Theme, only when there's no addressable referent
```

```
SUMMARIZE goo://file/~/article.md  HTTP/1.1
Using: goo://channel/fabric?model=iq4xs
To:    goo://chat/new
With:  depth=brief
```

The subject is resolved by the noun engine of [01](./01-the-shared-graph.md) (a umwelt
selector / matcher); `Using:`/`To:` are *also* resolved that way (with goo's
try/require/literal gradient). So goo's request layer is: **a verb, plus three umwelt
selector evaluations, plus an opaque bag.** The retritis tools supply the matchers
that make those selectors mean something.

## 2. The three-way schema identity

This is the structural fact that makes the whole bridge mechanical rather than
hand-wired. goo's protocol doc states it for half of it:

> "this slot schema **is** an MCP tool's `inputSchema`… so a goo↔MCP proxy is
> mechanical."

retritis supplies the other half. fledgling already runs, in SQL:

```sql
PRAGMA mcp_publish_tool(
  'FindCode',
  'Search code with CSS selectors…',
  'SELECT * FROM find_code_grep(_resolve($file_pattern), $selector, …)',
  '{"file_pattern": {"type":"string",…}, "selector": {"type":"string",…}}',  -- inputSchema
  '["file_pattern","selector"]', 'text');
```

So there is a **three-way identity**:

```
DuckDB macro signature   ≡   MCP tool inputSchema   ≡   goo OPTIONS slot schema
   (find_code_grep)            (FindCode)                 (OPTIONS goo://code/…)
```

A thing authored *once* as a fledgling macro is already an MCP tool with a JSON
schema; goo's `OPTIONS` returns a JSON schema that maps to MCP. Therefore a DuckDB
macro can be surfaced as a goo verb **by adapter, not by hand** — and `OPTIONS`
becomes the completion oracle for tab-completing a partial goo sentence.

### The lossy part (read this before believing the word "mechanical")

The identity holds for the *shape*, not the *roles*. MCP `inputSchema` has no notion
of:

- which param is the **subject** vs `To:` vs `Using:` vs `With:` (grammatical case);
- the **resolution gradient** (`try | require | literal`) goo attaches per slot;
- **cardinality** (`1` / `pick=first` / `all`) and the `300`-on-ambiguity behavior.

DuckDB macros have positional/named params with *no* case at all. So the adapter needs
a small, hand-declared **role map per tool** — "`find_code_grep.selector` is the
subject; `file_pattern` is a `With:` filter; there is no `To:`." That role map is the
actual engineering. goo's protocol doc waves it off ("the handler's OPTIONS schema
assigns meaning"); name it honestly so nobody budgets zero for it.

## 3. The bridge is bidirectional, and retritis is the consumer that earns goo's gate

goo's request layer is build-gated: *"revisit when a real consumer exists — not
before."* retritis is that consumer, and the bridge runs both ways:

- **MCP → goo** (retritis tools become *desktop verbs/resolvers*): `GET
  goo://code/;q=validate_token` proxies to `squackit.find` → `300` ranked
  `{id,label,weight}`. The launcher now does semantic code navigation, build-log
  triage, git workflows — the tools escape Claude Code.
- **goo → MCP** (desktop verbs become *agent tools*): every goo verb auto-mounts as an
  MCP tool, OPTIONS→`inputSchema`, `destructive`/`confirm`→annotations. Claude Code
  can `OPEN`, `MOVE`, `EMAIL`, `REBOOT` — actuate the real desktop under policy.

Because of the identity in §2, both directions are one adapter parameterized by the
role map, not N hand-written shims.

## 4. The grammatical cases, mapped onto retritis operations

The cases aren't decoration — they carry the indirect objects retritis tools already
take:

```
MOVE  goo://code/file=src/auth.py#oldName   To: newName            # pluckit rename (To: = target name, literal)
SHIP  goo://repo/.                          To: goo://branch/main   # jetsam ship (To: = destination ref)
EMAIL goo://code/file=token.py#validate     To: goo://contact/alice # squackit renders fn; email channel sends
SEARCH goo://sel/                           Using: goo://channel/fabric   # "search selection with…" (instrument)
SOLVE goo://text/"rebase & run auth tests"  Using: goo://channel/lackpy   # NL intent → a goo-program (see 04)
```

"Email this function to alice" is one sentence because the subject (a code entity) and
the recipient (a contact) are both first-class resolvable nouns, and the verb is a
channel. The grammar is what lets cross-domain composition read as language.

## 5. Two HTTP affordances that *are* the retritis thesis

goo being literal HTTP hands retritis two of its core principles for free:

- **`Accept:` negotiation = "structured for machines, rendered for humans."** The same
  resolver serves three audiences off one address:
  ```
  GET goo://code/…#fn   Accept: application/json     → structured nodes (agent)
  GET goo://code/…#fn   Accept: text/plain           → grep-style file:line (human)
  GET goo://code/…#fn   Accept: text/html            → rendered preview (launcher)
  ```
  This is retritis's "structured beats textual, but render for the audience," realized
  at the transport layer. (For tabular results this becomes Arrow/CSV/dataframe — see
  [03-relations-as-content](./03-relations-as-content.md).)
- **`HEAD` = the cheap pre-flight probe.** `HEAD goo://code/;q=foo` answers "exists? /
  what type? / how many callers?" in headers, no body. Token-thrift becomes a verb:
  an agent checks before it pays for the full result.

## 6. Safety: one policy, two enforcement points

goo declares safety in verb TOML (`confirm = always|multiple|never`, `destructive =
true`), surfaced in OPTIONS and mapped to MCP annotations. umwelt's `capability` taxon
declares the same kind of thing as policy (`tool { max-level: 2 }`, `require: sandbox`,
effect signatures). These are the *same constraint at two scopes*:

- **kibitzer** enforces umwelt policy *in-agent* (PreToolUse interception).
- a **goo dispatch middleware** enforces the *same* `.umw` policy *system-wide* (before
  any verb runs): allow / `428 Precondition Required` (confirm) / `403`.

One `.umw` file, two enforcement surfaces — finally crossing the agent/desktop
boundary. **Caveat (security, not ergonomics):** if the same policy is enforced by two
different mechanisms and they drift, the agent believes it is sandboxed differently
than the desktop enforces. Shared policy demands a *shared evaluator* (umwelt's
PolicyEngine), not two reimplementations.

## 7. "goo as MCP transport" — the tempting overreach

The `tools/call` half of MCP genuinely is isomorphic to a goo request, and goo adds
addressing, grammatical composition, `curl`-ability, and desktop reach that MCP lacks.
It is tempting to say "make retritis servers speak goo natively; MCP is a thin
adapter." Resist stating it that broadly: MCP also has resources, prompts, sampling,
notifications, and progress that goo does not model. The honest claim is **goo is a
superset of MCP *tool-calls*** — not of MCP. Bridge the tool-call surface; leave the
rest to MCP.

## Honest status

| Piece | State |
|---|---|
| `goo://` URI addressing | shipped (Rust + bash resolve it) |
| goo request/wire layer (verbs, cases, status codes, OPTIONS) | design, build-gated (#31/#38) |
| fledgling `mcp_publish_tool` (the schema-identity proof) | built |
| goo↔MCP bridge + per-tool role maps | speculative (this dir) |
| umwelt-as-goo-middleware (shared policy enforcement) | speculative; depends on umwelt PolicyEngine (built) + goo daemon (gated) |

→ Next: [03-relations-as-content.md](./03-relations-as-content.md) — what comes back
when the verb returns tabular data.
